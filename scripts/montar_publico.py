"""Monta o site público em docs/ a partir da landing de origem (lida somente para leitura).

Uso:
  python -I scripts/montar_publico.py [--origem <pasta da landing>]
A origem também pode vir da variável ORIGEM. Padrão: pasta irmã LANDING-OSC-CAPTACAO-TRANSFEREGOV.
Antes, renderize os slides (scripts/renderizar_slides.ps1) em gerado/slides/<palestra|painel>/.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
from regras_publicacao import (  # noqa: E402
    LIMITE_ARQUIVO_BYTES, LIMITE_SITE_BYTES, arquivos_do_item, item_publicavel, recusados,
)

DESTINO = RAIZ / "docs"
ESTILO = RAIZ / "estilo"
SLIDES = RAIZ / "gerado" / "slides"

PAGINAS = ["index.html", "palestra-1-captacao.html", "palestra-2-desafios.html"]
PASTAS_INTEIRAS = ["css", "js", "assets/identidade", "fonts", "vendor/govbr-ds"]

AVISO_PUBLICO = (
    '<div class="aviso-publico"><div class="envelope"><p>'
    "Página de apoio a uma palestra; não é serviço oficial do gov.br."
    "</p></div></div>"
)
TEXTO_IA = (
    "Material de suporte da apresentação, produzido com uso de inteligência artificial "
    "(NotebookLM) a partir das fontes do caderno MROSC e revisado com errata."
)
SELO_IA = '<span class="selo-ia">Produzido com IA</span>'

APRESENTACOES = {
    "palestra": {
        "pagina": "palestra-1-captacao.html",
        "arquivo_slides": "slides-palestra.html",
        "rotulo": "da palestra",
        "titulo": "Captação de Recursos Federais via Transferegov.br para o Terceiro Setor",
        "voltar": "Voltar à palestra",
    },
    "painel": {
        "pagina": "palestra-2-desafios.html",
        "arquivo_slides": "slides-painel.html",
        "rotulo": "do painel",
        "titulo": "Transferegov.br e as OSCs: Desafios, Exigências e Estratégias para Acesso a Recursos",
        "voltar": "Voltar ao painel",
    },
}


class ErroMontagem(Exception):
    pass


def substituir(texto, padrao, novo, esperado, onde, flags=0):
    """re.subn que exige o número esperado de trocas: a página de origem mudou se falhar."""
    resultado, n = re.subn(padrao, novo, texto, flags=flags)
    if n != esperado:
        raise ErroMontagem(f"{onde}: esperava {esperado} ocorrência(s) de {padrao!r}, achei {n}")
    return resultado


def ajustes_comuns(texto, onde, prefixo=""):
    texto = substituir(texto, r'(<meta name="viewport"[^>]*>)',
                       r'\1\n<meta name="robots" content="noindex">', 1, onde)
    texto = substituir(texto, r'(<link rel="stylesheet" href="' + re.escape(prefixo) + r'css/estilo\.css">)',
                       r'\1\n<link rel="stylesheet" href="' + prefixo + 'css/publico.css">', 1, onde)
    if '<header class="cabecalho">' in texto:
        texto = substituir(texto, r'(<header class="cabecalho">)', AVISO_PUBLICO + r"\n\1", 1, onde)
    else:
        texto = substituir(texto, r"(<main )", AVISO_PUBLICO + r"\n\1", 1, onde)
    return texto


def marcar_ia(texto, onde):
    """Reescreve o aviso de IA e põe o selo em cada item do material didático."""
    ini = texto.find('id="material-didatico"')
    if ini < 0:
        return texto
    fim = texto.find("</section>", ini)
    trecho = texto[ini:fim]
    trecho = substituir(trecho, r"Material gerado com apoio de IA \(NotebookLM\) a partir das fontes do caderno MROSC\.",
                        TEXTO_IA, 1, onde)
    # Cada item do material tem um id "mat-…"; os <li> das erratas começam direto com texto.
    itens = len(re.findall(r'id="mat-', trecho))
    trecho = substituir(trecho, r'<li>(\s*<(?:p class="titulo-material"|a href="materiais/))',
                        r"<li>" + SELO_IA + r"\1", itens, onde)
    return texto[:ini] + trecho + texto[fim:]


def transformar_pagina(nome, texto):
    texto = ajustes_comuns(texto, nome)
    for chave, ap in APRESENTACOES.items():
        if nome == ap["pagina"]:
            texto = substituir(
                texto,
                r'<a class="br-button secondary" href="apresentacoes/[a-z-]+\.pptx" download>[^<]*</a>',
                f'<a class="br-button secondary" href="{ap["arquivo_slides"]}">Acompanhar os slides {ap["rotulo"]}</a>',
                1, nome)
    texto = re.sub(
        r'<span class="meta">Apresentação · <a href="[^"]+\.pptx" download>Baixar o PowerPoint</a></span>',
        '<span class="meta">Apresentação em PDF</span>', texto)
    texto = marcar_ia(texto, nome)
    if re.search(r"\sdownload[\s>=]", texto) or ".pptx" in texto:
        raise ErroMontagem(f"{nome}: sobrou link de download ou .pptx")
    return texto


def transformar_leitura(nome, texto):
    texto = ajustes_comuns(texto, nome, prefixo="../../")
    texto = texto.replace(
        "Material gerado com apoio de IA (NotebookLM) a partir das fontes do caderno MROSC.",
        TEXTO_IA)
    if "Produzido com IA" not in texto:
        texto = substituir(texto, r'(<p class="aviso-ia">)', r"\1" + SELO_IA + " ", 1, nome)
    return texto


def texto_do_slide(textos, total):
    """Tira o contador "n/total" e os campos não preenchidos da capa."""
    limpos = []
    for t in textos:
        t = t.strip()
        if re.fullmatch(rf"\d+/{total}", t) or re.fullmatch(r"(\[[^\]]+\]\s*)+", t):
            continue
        limpos.append(t)
    return limpos


# Endereço do próprio site público (a capa das apresentações aponta para ele).
SITE_PUBLICO = "https://marcelofernandesgarcia-dev.github.io/transferegov-contes-osc/"


def link_permitido(endereco):
    """Só https em domínio gov.br, como na landing de origem, ou o endereço do próprio site."""
    u = urlparse(endereco or "")
    host = (u.hostname or "").lower()
    if u.scheme != "https":
        return False
    if host == "gov.br" or host.endswith(".gov.br"):
        return True
    return endereco.startswith(SITE_PUBLICO)


def juntar_quebra(texto):
    """Texto de link quebrado em linhas no slide: sem espaços (endereço) junta direto; senão, com espaço."""
    partes = [p.strip() for p in texto.replace("\r", "\n").split("\n") if p.strip()]
    return ("" if all(" " not in p for p in partes) else " ").join(partes)


def linha_html(linha, links):
    """Linha do texto do slide; vira link externo se for o texto de um hyperlink do slide."""
    texto = linha.strip()
    endereco = links.get(texto)
    if not endereco:
        return html.escape(texto)
    return (f'<a href="{html.escape(endereco, quote=True)}" target="_blank" rel="noopener">{html.escape(texto)}'
            '<span class="sr-only"> (abre em nova aba)</span>'
            '<svg class="icone" aria-hidden="true"><use href="#i-externo"/></svg></a>')


def links_do_slide(s, onde):
    links = {}
    for l in s.get("links") or []:
        if not link_permitido(l.get("endereco")):
            raise ErroMontagem(f"{onde}, slide {s['numero']}: link fora de https/gov.br: {l.get('endereco')!r}")
        if l.get("texto"):
            links[juntar_quebra(l["texto"])] = l["endereco"]
    return links


def unir_textos_de_link(textos, links_brutos):
    """Junta numa linha só o texto de um link que o slide quebrou em várias linhas."""
    saida = []
    for t in textos:
        for l in links_brutos:
            bruto = (l.get("texto") or "").replace("\r", "\n").strip()
            if "\n" in bruto and bruto in t:
                t = t.replace(bruto, juntar_quebra(bruto))
        saida.append(t)
    return saida


def pagina_slides(chave, slides):
    ap = APRESENTACOES[chave]
    total = len(slides)
    itens = []
    for s in slides:
        textos = texto_do_slide(s["textos"], total)
        titulo = textos[0] if textos else f"Slide {s['numero']}"
        if s["numero"] == 1 and len(textos) > 1:
            titulo = f"{textos[0]}: {textos[1]}"
        links = links_do_slide(s, chave)
        textos = unir_textos_de_link(textos, s.get("links") or [])
        paragrafos = "\n".join(
            "<p>" + "<br>".join(linha_html(l, links) for l in t.split("\n") if l.strip()) + "</p>" for t in textos)
        usados = sum(paragrafos.count(f'href="{html.escape(e, quote=True)}"') > 0 for e in links.values())
        if usados != len(set(links.values())):
            raise ErroMontagem(f"{chave}, slide {s['numero']}: link do .pptx sem texto correspondente no slide")
        # Slide com links: o texto já vem aberto, para os links ficarem visíveis sob a imagem.
        aberto = " open" if links else ""
        n = s["numero"]
        carregar = "eager" if n == 1 else "lazy"
        itens.append(f"""      <li class="slide" id="slide-{n}">
        <figure>
          <img src="slides/{chave}/{s['imagem']}" width="{s['largura']}" height="{s['altura']}" loading="{carregar}" alt="Slide {n} de {total}: {html.escape(titulo, quote=True)}">
          <figcaption class="contador-slide">Slide {n} de {total}</figcaption>
        </figure>
        <details class="texto-slide"{aberto}>
          <summary>{"Texto e links" if links else "Texto"} do slide {n}</summary>
          {paragrafos}
        </details>
      </li>""")
    lista = "\n".join(itens)
    titulo_html = html.escape(ap["titulo"])
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Slides {ap['rotulo']}: {titulo_html}</title>
<link rel="icon" type="image/png" href="assets/identidade/transferegov-logo.png">
<link rel="stylesheet" href="vendor/govbr-ds/tokens-ds.min.css">
<link rel="stylesheet" href="vendor/govbr-ds/button.min.css">
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/estilo.css">
</head>
<body>
<svg class="sprite" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">
  <symbol id="i-externo" viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></symbol>
</svg>
<nav class="atalhos" aria-label="Atalhos de acessibilidade">
  <a href="#conteudo">Ir para o conteúdo</a>
</nav>
<header class="cabecalho">
  <div class="envelope">
    <p class="cabecalho-titulo"><a href="index.html">OSCs e parcerias federais</a></p>
    <img src="assets/identidade/transferegov-logo.png" alt="Transferegov.br" width="120" height="40">
  </div>
</header>
<main id="conteudo" class="envelope visualizador">
  <p><a href="{ap['pagina']}">{ap['voltar']}</a></p>
  <h1>Slides {ap['rotulo']}: {titulo_html}</h1>
  <p class="aviso">Slides disponíveis só para acompanhar a apresentação. O texto de cada slide está em "Texto do slide", logo abaixo da imagem. Use os botões ou as setas do teclado para avançar e voltar.</p>
  <section class="apresentacao" aria-label="Slides {ap['rotulo']}" data-total="{total}">
    <ol class="lista-slides">
{lista}
    </ol>
    <div class="controles-slides" hidden>
      <button type="button" class="br-button secondary" data-ir="-1">Slide anterior</button>
      <p class="posicao-slide" aria-live="polite" aria-atomic="true"></p>
      <button type="button" class="br-button primary" data-ir="1">Próximo slide</button>
    </div>
  </section>
</main>
<script src="js/slides.js"></script>
</body>
</html>
"""


def copiar(origem, rel, copiados):
    src = origem / rel
    if not src.is_file():
        raise ErroMontagem(f"arquivo não encontrado na origem: {rel}")
    dst = DESTINO / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copiados.append(rel)


def montar(origem):
    origem = Path(origem).resolve()
    if not (origem / "materiais" / "materiais.json").is_file():
        raise ErroMontagem(f"origem inválida (sem materiais/materiais.json): {origem}")
    # Apaga só os arquivos de docs/: pastas podem estar presas pelo OneDrive ou por um servidor local,
    # e pasta vazia não vai para o git.
    if DESTINO.exists():
        for f in DESTINO.rglob("*"):
            if f.is_file():
                f.unlink()
    DESTINO.mkdir(exist_ok=True)
    copiados = []

    for pasta in PASTAS_INTEIRAS:
        for f in sorted((origem / pasta).rglob("*")):
            if f.is_file():
                copiar(origem, f.relative_to(origem).as_posix(), copiados)
    for nome in ("publico.css",):
        shutil.copy2(ESTILO / nome, DESTINO / "css" / nome)
        copiados.append(f"css/{nome}")
    shutil.copy2(ESTILO / "slides.js", DESTINO / "js" / "slides.js")
    copiados.append("js/slides.js")

    catalogo = json.loads((origem / "materiais" / "materiais.json").read_text(encoding="utf-8"))
    for item in catalogo["itens"]:
        if item_publicavel(item):
            for a in arquivos_do_item(item):
                copiar(origem, f"materiais/{a}", copiados)

    paginas = {}
    for nome in PAGINAS:
        paginas[nome] = transformar_pagina(nome, (origem / nome).read_text(encoding="utf-8"))
    referenciadas = set()
    for texto in paginas.values():
        referenciadas |= set(re.findall(r'href="(materiais/leitura/[^"#]+\.html)"', texto))
    for rel in sorted(referenciadas):
        texto = transformar_leitura(rel, (origem / rel).read_text(encoding="utf-8"))
        (DESTINO / rel).parent.mkdir(parents=True, exist_ok=True)
        (DESTINO / rel).write_text(texto, encoding="utf-8", newline="\n")
        copiados.append(rel)
    for nome, texto in paginas.items():
        (DESTINO / nome).write_text(texto, encoding="utf-8", newline="\n")
        copiados.append(nome)

    for chave, ap in APRESENTACOES.items():
        pasta = SLIDES / chave
        dados = pasta / "slides.json"
        if not dados.is_file():
            raise ErroMontagem(f"slides não renderizados: rode scripts/renderizar_slides.ps1 para {chave}")
        slides = json.loads(dados.read_text(encoding="utf-8-sig"))
        (DESTINO / "slides" / chave).mkdir(parents=True, exist_ok=True)
        for s in slides:
            shutil.copy2(pasta / s["imagem"], DESTINO / "slides" / chave / s["imagem"])
            copiados.append(f"slides/{chave}/{s['imagem']}")
        (DESTINO / ap["arquivo_slides"]).write_text(
            ajustes_comuns(pagina_slides(chave, slides), ap["arquivo_slides"]), encoding="utf-8", newline="\n")
        copiados.append(ap["arquivo_slides"])

    (DESTINO / ".nojekyll").write_text("", encoding="utf-8")
    copiados.append(".nojekyll")

    # Barreira final: tudo o que está em docs/ (não só o que este script copiou).
    no_disco = [p.relative_to(DESTINO).as_posix() for p in DESTINO.rglob("*") if p.is_file()]
    ruins = recusados(no_disco)
    if ruins:
        raise ErroMontagem("arquivos recusados em docs/: " + "; ".join(f"{c} ({m})" for c, m in ruins))
    tamanhos = {p: (DESTINO / p).stat().st_size for p in no_disco}
    grandes = [p for p, t in tamanhos.items() if t > LIMITE_ARQUIVO_BYTES]
    if grandes or sum(tamanhos.values()) > LIMITE_SITE_BYTES:
        raise ErroMontagem(f"limite de tamanho excedido: {grandes or 'site inteiro'}")
    return no_disco, sum(tamanhos.values())


def main():
    padrao = os.environ.get("ORIGEM") or str(RAIZ.parent / "LANDING-OSC-CAPTACAO-TRANSFEREGOV")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--origem", default=padrao)
    args = ap.parse_args()
    try:
        arquivos, total = montar(args.origem)
    except ErroMontagem as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print(f"{len(arquivos)} arquivos em docs/ ({total / 1024 ** 2:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
