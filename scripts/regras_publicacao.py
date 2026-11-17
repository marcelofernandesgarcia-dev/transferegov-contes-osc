"""Regras puras do que pode e do que não pode ir para o site público (pasta docs/).

Parâmetros em constantes no topo; sem dependência além da biblioteca padrão.
Usado por montar_publico.py (barreira antes de terminar) e pelos testes.
"""
import re

# Limites do GitHub Pages no plano Free (docs do GitHub, conferidas em 17/11/2026):
# site até 1 GB. Arquivo acima de 100 MB é recusado pelo push do GitHub.
LIMITE_SITE_BYTES = 1024 ** 3
LIMITE_ARQUIVO_BYTES = 100 * 1024 ** 2

# Caminhos relativos a docs/, sempre com "/".
PERMITIDOS = [
    r"\.nojekyll",
    r"index\.html",
    r"palestra-1-captacao\.html",
    r"palestra-2-desafios\.html",
    r"slides-palestra\.html",
    r"slides-painel\.html",
    r"css/[a-z0-9-]+\.css",
    r"js/[a-z0-9-]+\.js",
    r"assets/identidade/[a-z0-9-]+\.png",
    r"fonts/[A-Za-z0-9-]+\.(woff2|txt)",
    r"vendor/govbr-ds/([a-z0-9-]+\.min\.css|LICENSE|VERSAO\.md)",
    r"slides/(palestra|painel)/slide-\d{2}\.png",
    r"materiais/leitura/p[12]-[a-z0-9-]+\.html",
    r"materiais/palestra-[12]-[a-z0-9-]+/(videos/[a-z0-9-]+\.mp4|audios/[a-z0-9-]+\.m4a"
    r"|infograficos/[a-z0-9-]+\.png|apresentacoes/[a-z0-9-]+\.pdf"
    r"|transcricoes/[a-z0-9-]+\.(txt|vtt)|textos/[a-z0-9-]+\.md)",
]

# Proibidos têm prioridade sobre a lista permitida (defesa em profundidade).
PROIBIDOS = [
    r"(^|/)apoio-do-apresentador(/|$)",
    r"(^|/)modelo-seges(/|$)",
    r"\.pptx$", r"\.potx$", r"\.docx$", r"\.xlsx$",
    r"(^|/)CLAUDE\.md$",
    r"(^|/)\.claude(/|$)",
    r"(^|/)PLANEJAMENTO-[^/]*$",
    r"^(scripts|testes|conteudo|fonte|versoes|design|fontes-oficiais|gerado)(/|$)",
    r"(^|/)\.env",
    r"(^|/)(materiais\.json|edicoes-video\.json|REVISAO-MATERIAIS\.md|LEIA-ME\.md|ROTEIRO[^/]*)$",
    r"\.(py|ps1|mjs|key|pem)$",
]

_PERMITIDOS = [re.compile(p + r"$") for p in PERMITIDOS]
_PROIBIDOS = [re.compile(p) for p in PROIBIDOS]


def classificar(caminho):
    """Devolve 'proibido', 'fora_da_lista' ou 'permitido' para um caminho relativo a docs/."""
    if caminho is None or not str(caminho).strip():
        raise ValueError("caminho vazio")
    c = str(caminho).replace("\\", "/").lstrip("/")
    if ".." in c.split("/"):
        return "proibido"
    if any(p.search(c) for p in _PROIBIDOS):
        return "proibido"
    if any(p.fullmatch(c) for p in _PERMITIDOS):
        return "permitido"
    return "fora_da_lista"


def recusados(caminhos):
    """Lista (caminho, motivo) de tudo que não pode ir ao site."""
    return [(c, m) for c in caminhos if (m := classificar(c)) != "permitido"]


def item_publicavel(item):
    """Item do catálogo materiais.json entra só se revisado e marcado para exibição."""
    return bool(item.get("revisado") is True and item.get("exibir") is True)


def arquivos_do_item(item):
    """Arquivos do item que entram no site (sem .pptx), relativos a materiais/."""
    lista = [a for a in (item.get("arquivos") or []) if not a.lower().endswith(".pptx")]
    lista += [a for a in (item.get("transcricao"), item.get("legenda")) if a]
    return lista
