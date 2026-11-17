"""Testes da versão pública: regras puras e conferência do que está em docs/.

Rodar: python -I -m unittest discover -s testes -p "test_*.py"
(rode antes scripts/montar_publico.py; sem docs/, os testes do site são pulados com aviso)
"""
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
from regras_publicacao import (  # noqa: E402
    LIMITE_ARQUIVO_BYTES, LIMITE_SITE_BYTES, arquivos_do_item, classificar, item_publicavel, recusados,
)

DOCS = RAIZ / "docs"


class TestRegras(unittest.TestCase):
    def test_recusa_material_proibido(self):
        for c in [
            "apresentacoes/palestra-captacao.pptx",
            "materiais/palestra-1-captacao/apresentacoes/guia-pratico-mrosc.pptx",
            "apresentacoes/apoio-do-apresentador/audios/palestra.mp3",
            "apoio-do-apresentador/x.pdf",
            "CLAUDE.md", ".claude/settings.json", "PLANEJAMENTO-FASE-1.md",
            "scripts/montar_paginas.py", "testes/a.py", "conteudo/parametros.json",
            "fonte/paginas.json", "versoes/index.html", "design/DESIGN.md",
            "fontes-oficiais/manual.pdf", "apresentacoes/modelo-seges/m.pptx",
            "materiais/materiais.json", "materiais/REVISAO-MATERIAIS.md", ".env",
        ]:
            with self.subTest(c=c):
                self.assertEqual(classificar(c), "proibido")

    def test_fora_da_lista_e_recusado(self):
        self.assertEqual(classificar("qualquer.html"), "fora_da_lista")
        self.assertEqual(classificar("materiais/palestra-1-captacao/videos/original.mov"), "fora_da_lista")

    def test_caminho_que_sobe_pasta_e_proibido(self):
        self.assertEqual(classificar("css/../../segredo.css"), "proibido")

    def test_caminho_vazio_gera_erro(self):
        with self.assertRaises(ValueError):
            classificar("")
        with self.assertRaises(ValueError):
            classificar(None)

    def test_permitidos_basicos(self):
        for c in ["index.html", "css/publico.css", "slides/painel/slide-01.png",
                  "materiais/palestra-2-desafios/videos/transferegov-e-oscs-editado.mp4",
                  "materiais/leitura/p1-texto-guia-transferegov-osc.html"]:
            with self.subTest(c=c):
                self.assertEqual(classificar(c), "permitido")

    def test_separador_windows(self):
        self.assertEqual(classificar("css\\estilo.css"), "permitido")
        self.assertEqual(recusados(["index.html", "x.pptx"]), [("x.pptx", "proibido")])

    def test_item_publicavel_exige_os_dois_campos(self):
        self.assertTrue(item_publicavel({"revisado": True, "exibir": True}))
        self.assertFalse(item_publicavel({"revisado": True, "exibir": False}))
        self.assertFalse(item_publicavel({"revisado": False, "exibir": True}))
        self.assertFalse(item_publicavel({"revisado": "true", "exibir": True}))
        self.assertFalse(item_publicavel({}))

    def test_arquivos_do_item_sem_pptx_e_com_transcricao(self):
        item = {"arquivos": ["a/x.pdf", "a/x.pptx"], "transcricao": "t/x.txt", "legenda": None}
        self.assertEqual(arquivos_do_item(item), ["a/x.pdf", "t/x.txt"])
        self.assertEqual(arquivos_do_item({"arquivos": None}), [])


class TestLinksDosSlides(unittest.TestCase):
    def test_so_https_gov_br(self):
        from montar_publico import link_permitido
        self.assertTrue(link_permitido("https://portal.transferegov.sistema.gov.br/portal/home"))
        self.assertTrue(link_permitido("https://www.gov.br/transferegov"))
        self.assertFalse(link_permitido("http://www.gov.br/x"))
        self.assertFalse(link_permitido("https://gov.br.exemplo.com/x"))
        self.assertFalse(link_permitido("javascript:alert(1)"))
        self.assertFalse(link_permitido(None))

    def test_link_fora_da_regra_para_a_montagem(self):
        from montar_publico import ErroMontagem, links_do_slide
        with self.assertRaises(ErroMontagem):
            links_do_slide({"numero": 1, "links": [{"texto": "x", "endereco": "https://exemplo.com"}]}, "teste")

    def test_linha_vira_link_com_nova_aba(self):
        from montar_publico import linha_html
        h = linha_html("Manual <MROSC>", {"Manual <MROSC>": "https://www.gov.br/a?b=1&c=2"})
        self.assertIn('href="https://www.gov.br/a?b=1&amp;c=2" target="_blank" rel="noopener"', h)
        self.assertIn("Manual &lt;MROSC&gt;", h)
        self.assertIn("(abre em nova aba)", h)
        self.assertEqual(linha_html("texto comum", {}), "texto comum")


class _Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.downloads, self.metas, self.imgs_sem_alt = [], [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ("href", "src"):
            if a.get(k):
                self.refs.append(a[k])
        if "download" in a:
            self.downloads.append(a.get("href"))
        if tag == "meta":
            self.metas.append(a)
        if tag == "img" and "alt" not in a:
            self.imgs_sem_alt += 1


@unittest.skipUnless(DOCS.is_dir(), "docs/ não montado: rode scripts/montar_publico.py")
class TestSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arquivos = [p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*") if p.is_file()]
        cls.paginas = [p for p in cls.arquivos if p.endswith(".html")]

    def test_nenhum_arquivo_recusado(self):
        self.assertEqual(recusados(self.arquivos), [])

    def test_nenhum_pptx_nem_material_de_estudo(self):
        for c in self.arquivos:
            self.assertNotRegex(c.lower(), r"\.pptx$|apoio-do-apresentador|claude")

    def test_tamanhos(self):
        tamanhos = [(DOCS / c).stat().st_size for c in self.arquivos]
        self.assertTrue(all(t <= LIMITE_ARQUIVO_BYTES for t in tamanhos))
        self.assertLessEqual(sum(tamanhos), LIMITE_SITE_BYTES)

    def test_paginas_esperadas(self):
        for p in ["index.html", "palestra-1-captacao.html", "palestra-2-desafios.html",
                  "slides-palestra.html", "slides-painel.html", ".nojekyll"]:
            self.assertIn(p, self.arquivos)

    def test_cada_pagina_tem_noindex_aviso_e_refs_validas(self):
        for pagina in self.paginas:
            with self.subTest(pagina=pagina):
                texto = (DOCS / pagina).read_text(encoding="utf-8")
                p = _Refs()
                p.feed(texto)
                self.assertIn({"name": "robots", "content": "noindex"}, p.metas)
                self.assertIn("Página de apoio a uma palestra; não é serviço oficial do gov.br.", texto)
                self.assertEqual(p.downloads, [], "link com atributo download")
                self.assertNotIn(".pptx", texto)
                self.assertEqual(p.imgs_sem_alt, 0)
                base = (DOCS / pagina).parent
                for ref in p.refs:
                    u = urlparse(ref)
                    if u.scheme or ref.startswith("#") or ref.startswith("data:"):
                        continue
                    destino = (base / unquote(u.path)).resolve()
                    self.assertTrue(destino.is_file(), f"{pagina}: {ref} não existe")
                    self.assertTrue(str(destino).startswith(str(DOCS.resolve())), f"{pagina}: {ref} sai de docs/")

    def test_links_externos_so_https(self):
        for pagina in self.paginas:
            texto = (DOCS / pagina).read_text(encoding="utf-8")
            self.assertEqual(re.findall(r'(?:href|src)="http:', texto), [], pagina)

    def test_selo_de_ia_em_todo_item_do_material_didatico(self):
        for pagina in ["palestra-1-captacao.html", "palestra-2-desafios.html"]:
            texto = (DOCS / pagina).read_text(encoding="utf-8")
            ini = texto.index('id="material-didatico"')
            trecho = texto[ini:texto.index("</section>", ini)]
            itens = len(re.findall(r'id="mat-', trecho))
            self.assertGreater(itens, 0)
            self.assertEqual(trecho.count('<span class="selo-ia">Produzido com IA</span>'), itens, pagina)
            self.assertIn("Material de suporte da apresentação, produzido com uso de inteligência artificial", trecho)

    def test_paginas_de_leitura_marcadas_como_ia(self):
        for pagina in [p for p in self.paginas if p.startswith("materiais/leitura/")]:
            texto = (DOCS / pagina).read_text(encoding="utf-8")
            self.assertIn("Produzido com IA", texto, pagina)

    def test_botoes_de_slides_no_lugar_do_download(self):
        p1 = (DOCS / "palestra-1-captacao.html").read_text(encoding="utf-8")
        p2 = (DOCS / "palestra-2-desafios.html").read_text(encoding="utf-8")
        self.assertIn('href="slides-palestra.html"', p1)
        self.assertIn('href="slides-painel.html"', p2)
        self.assertNotIn("Baixar", p1 + p2)

    def test_visualizador_tem_todos_os_slides_com_alt_e_texto(self):
        for pagina, pasta in [("slides-palestra.html", "palestra"), ("slides-painel.html", "painel")]:
            texto = (DOCS / pagina).read_text(encoding="utf-8")
            n = len([a for a in self.arquivos if a.startswith(f"slides/{pasta}/")])
            self.assertGreater(n, 0)
            self.assertEqual(len(re.findall(r'<li class="slide"', texto)), n)
            self.assertEqual(len(re.findall(r'alt="Slide \d+ de ' + str(n) + r': [^"]+"', texto)), n)
            self.assertEqual(len(re.findall(r'<details class="texto-slide"( open)?>', texto)), n)
            self.assertIn('aria-live="polite"', texto)
            self.assertNotIn("[Nome]", texto)
            ultimo = texto[texto.index(f'id="slide-{n}"'):]
            self.assertGreaterEqual(ultimo.count('target="_blank" rel="noopener"'), 8, pagina)
            self.assertIn("<details class=\"texto-slide\" open>", ultimo)

    def test_secao_acessos_necessarios(self):
        for pagina in ["index.html", "palestra-1-captacao.html", "palestra-2-desafios.html"]:
            self.assertIn('id="acessos"', (DOCS / pagina).read_text(encoding="utf-8"), pagina)


if __name__ == "__main__":
    unittest.main()
