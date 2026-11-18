# transferegov-contes-osc — versão pública da landing de apoio à palestra

Site estático de apoio a uma palestra e um painel sobre parcerias federais entre OSCs e a União pelo Transferegov.br. É a **versão pública** de uma landing mantida em repositório privado (a fonte). Este repositório guarda só o site montado (`docs/`) e as ferramentas que o montam e conferem.

**Não é serviço oficial do gov.br.** Cada página traz esse aviso no topo e `<meta name="robots" content="noindex">`.

## O que entra e o que não entra

- **Entra:** página inicial, página da palestra e do painel, CSS, JS, identidade, fonte Raleway, subconjunto do DS gov.br, os slides das duas apresentações **como imagens** (só para acompanhar, sem download) e o material didático do NotebookLM com `revisado: true` e `exibir: true` no catálogo da fonte, marcado como **produzido com IA** e como material de suporte da apresentação.
- **Não entra:** nenhum `.pptx`, material de estudo do apresentador, planejamento, scripts e testes da fonte, conteúdo-fonte, modelo Seges, fontes oficiais. A lista permitida e a lista proibida estão em `scripts/regras_publicacao.py`; a montagem para se sobrar qualquer arquivo fora da lista.

## Como montar

1. Renderizar os slides (PowerPoint instalado; o `.pptx` é aberto só para leitura e não é copiado):
   ```bash
   powershell -File scripts/renderizar_slides.ps1 -Arquivo "<fonte>/apresentacoes/palestra-captacao.pptx" -Saida gerado/slides/palestra
   ```
   ```bash
   powershell -File scripts/renderizar_slides.ps1 -Arquivo "<fonte>/apresentacoes/publico/painel-desafios.pptx" -Saida gerado/slides/painel
   ```
   O painel vem da versão pública (`apresentacoes/publico/painel-desafios.pptx`, sem a tarja "Pergunta ao painel" e sem o slide de votação); a palestra vem de `apresentacoes/palestra-captacao.pptx`.
2. Montar `docs/` a partir da fonte (somente leitura):
   ```bash
   python -I scripts/montar_publico.py --origem "<pasta da landing de origem>"
   ```
   Sem `--origem`, usa a variável `ORIGEM` ou a pasta irmã `LANDING-OSC-CAPTACAO-TRANSFEREGOV`.

`estilo/publico.css` (aviso, selo de IA, visualizador; só tokens) e `estilo/slides.js` (visualizador) são copiados para `docs/`.

## Testes

```bash
python -I -m unittest discover -s testes -p "test_*.py"
```

```bash
python -m http.server 8092 --bind 127.0.0.1 -d docs
```

```bash
node testes/verificar_navegador.mjs
```

O segundo comando serve o site local; o terceiro roda axe-core em 6 larguras (320 a 1920 px), procura rolagem horizontal e requisição externa, e confere o teclado no visualizador. Usa o Playwright e o axe-core de `FERRAMENTAS_TESTE` (variável opcional) e o Chrome instalado.

## Publicação

GitHub Pages servindo a pasta `/docs` do branch `main`. Endereço: `https://marcelofernandesgarcia-dev.github.io/transferegov-contes-osc/`. Atualizar o site = montar, testar, revisar a lista de arquivos e só então commitar e enviar.

## Pendências

- VLibras: endereço oficial do script a confirmar antes de incluir.
- Marca gov.br/Transferegov.br em site não oficial: mantida com aviso (decisão do usuário, 17/11/2026); a área de comunicação não foi consultada.
- Os slides seguem o Padrão visual Seges (uso interno): estão só como imagem, mas qualquer imagem exibida pode ser salva pelo navegador.

Licenças de terceiros: DS gov.br (MIT, `docs/vendor/govbr-ds/LICENSE`), Raleway (OFL 1.1, `docs/fonts/`).
