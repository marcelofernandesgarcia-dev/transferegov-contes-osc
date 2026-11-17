# Design System gov.br — subconjunto usado pela landing

- Pacote: `@govbr-ds/core` **3.7.0** (SERPRO), licença **MIT** (`LICENSE` nesta pasta).
- Origem: registro npm (`npm pack @govbr-ds/core@3.7.0`), obtido em 07/11/2026.
- SHA-256 do `.tgz`: `2B8F13B0A1427F101F9F7AA81751B1BAFE829E17305B1727FC2A0E3326781247` (igual ao auditado em 17/10/2026 na landing de treinamento).

## Arquivos (copiados sem alteração de `dist/`)

| Arquivo aqui | Origem no pacote | Uso previsto |
|---|---|---|
| `tokens-ds.min.css` | `dist/core-tokens.min.css` | cores, espaçamentos, raios, tipografia, foco |
| `button.min.css` | `dist/components/button/` | botões e CTAs |
| `header.min.css` | `dist/components/header/` | cabeçalho |
| `footer.min.css` | `dist/components/footer/` | rodapé |
| `skiplink.min.css` | `dist/components/skiplink/` | atalhos de acessibilidade |
| `message.min.css` | `dist/components/message/` | avisos (orientativo, erros da calculadora) |
| `divider.min.css` | `dist/components/divider/` | divisores |
| `list.min.css` | `dist/components/list/` | sumário e listas de materiais |
| `checkbox.min.css` | `dist/components/checkbox/` | checklist de prontidão |
| `input.min.css` | `dist/components/input/` | calculadora |
| `table.min.css` | `dist/components/table/` | quadros comparativos e de requisitos |
| `tag.min.css` | `dist/components/tag/` | rótulos de gravidade e de fonte |

## Não usado, e por quê
- `core.min.js`: comportamento próprio em JS mínimo; sem dependência do script do DS.
- Ícones (Font Awesome): não vêm no pacote; ícones SVG próprios em sprite.
- Rawline: não vem no pacote; licença de distribuição não localizada. Usa-se Raleway (`../../fonts/LEIA-ME.txt`).
- Accordion: `<details>` nativo com a aparência do DS (teclado e leitor de tela nativos, sem JS).

## Como atualizar
`npm pack @govbr-ds/core@<versão>`, copiar os mesmos arquivos de `dist/`, atualizar versão, data e hash e reverificar de 320 a 1440 px.
