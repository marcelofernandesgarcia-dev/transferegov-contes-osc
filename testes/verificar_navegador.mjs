// Verificação no navegador do site público (docs/): axe-core em 6 larguras, rolagem horizontal,
// erros de console, rede só local, e teclado no visualizador de slides. Somente leitura.
// Uso: python -m http.server 8092 --bind 127.0.0.1 -d docs   (em outro terminal)
//      node testes/verificar_navegador.mjs [http://127.0.0.1:8092/]
// Playwright e axe-core vêm de FERRAMENTAS_TESTE (padrão C:\Users\<usuário>\FerramentasTeste).
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { join } from 'node:path';

const BASE = process.argv[2] || 'http://127.0.0.1:8092/';
const FERRAMENTAS = process.env.FERRAMENTAS_TESTE || join(homedir(), 'FerramentasTeste');
const require = createRequire(join(FERRAMENTAS, 'package.json'));
const { chromium } = require('playwright');
const AXE = require.resolve('axe-core/axe.min.js');

const larguras = [320, 375, 768, 1024, 1280, 1920];
const paginas = ['index.html', 'palestra-1-captacao.html', 'palestra-2-desafios.html',
  'slides-palestra.html', 'slides-painel.html', 'materiais/leitura/p1-texto-guia-transferegov-osc.html'];
const falhas = [];
const navegador = await chromium.launch({ channel: 'chrome', headless: true });

for (const largura of larguras) {
  const ctx = await navegador.newContext({ viewport: { width: largura, height: 900 } });
  for (const p of paginas) {
    const pg = await ctx.newPage();
    const erros = [];
    pg.on('console', (m) => { if (m.type() === 'error') erros.push(m.text().slice(0, 160)); });
    pg.on('request', (r) => { const h = new URL(r.url()).host; if (h && !h.startsWith('127.0.0.1')) erros.push('rede externa: ' + h); });
    await pg.goto(BASE + p, { waitUntil: 'load' });
    await pg.addScriptTag({ path: AXE });
    const r = await pg.evaluate(async () => {
      const a = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } });
      return {
        violacoes: a.violations.map((v) => `${v.id} (${v.nodes.length}): ${v.nodes[0].target.join(' ')}`),
        rolagem: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    });
    const linha = `${largura}px ${p}: axe ${r.violacoes.length}${r.rolagem ? ' ROLAGEM-HORIZONTAL' : ''}${erros.length ? ' console/rede: ' + erros.join(' | ') : ''}`;
    console.log(linha);
    if (r.violacoes.length || r.rolagem || erros.length) falhas.push(linha + '\n   ' + r.violacoes.join('\n   '));
    await pg.close();
  }
  await ctx.close();
}

// Teclado no visualizador
const ctx = await navegador.newContext({ viewport: { width: 1280, height: 900 } });
const pg = await ctx.newPage();
await pg.goto(BASE + 'slides-palestra.html', { waitUntil: 'load' });
const visivel = () => pg.evaluate(() => [...document.querySelectorAll('.slide')].findIndex((s) => !s.hidden) + 1);
const posicao = () => pg.textContent('.posicao-slide');
const checar = (cond, msg) => { console.log((cond ? 'ok   ' : 'FALHA ') + msg); if (!cond) falhas.push(msg); };

checar(await visivel() === 1 && (await posicao()) === 'Slide 1 de 17', 'abre no slide 1');
// Tab: atalho → título (link) → voltar → anterior → próximo
const focos = [];
let semContorno = [];
for (let i = 0; i < 6; i++) {
  await pg.keyboard.press('Tab');
  const f = await pg.evaluate(() => {
    const e = document.activeElement; const s = getComputedStyle(e);
    return { nome: (e.textContent || e.tagName).trim().slice(0, 30), contorno: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2 };
  });
  focos.push(f.nome);
  if (!f.contorno) semContorno.push(f.nome);
}
console.log('     ordem de foco:', focos.join(' → '));
checar(focos[0] === 'Ir para o conteúdo', 'primeiro Tab no atalho');
checar(focos.includes('Slide anterior') && focos.includes('Próximo slide'), 'botões alcançáveis por Tab');
checar(semContorno.length === 0, 'foco visível em todos os elementos percorridos' + (semContorno.length ? ': ' + semContorno.join(', ') : ''));
await pg.focus('[data-ir="1"]');
await pg.keyboard.press('Enter');
checar(await visivel() === 2 && (await posicao()) === 'Slide 2 de 17', 'Enter no Próximo vai ao slide 2');
await pg.keyboard.press('ArrowRight');
checar(await visivel() === 3, 'seta direita vai ao slide 3');
await pg.keyboard.press('ArrowLeft');
checar(await visivel() === 2, 'seta esquerda volta ao slide 2');
checar(pg.url().endsWith('#slide-2'), 'endereço #slide-2');
await pg.goto(BASE + 'slides-palestra.html#slide-17', { waitUntil: 'load' });
checar(await visivel() === 17, 'abre direto no #slide-17');
await pg.keyboard.press('ArrowRight');
checar(await visivel() === 17, 'não passa do último');
checar(await pg.getAttribute('[data-ir="1"]', 'aria-disabled') === 'true', 'Próximo marcado como indisponível no último');
await pg.click('.slide:not([hidden]) summary');
checar(await pg.isVisible('.slide:not([hidden]) .texto-slide p'), 'texto do slide abre');
// Sem JavaScript: todos os slides em lista
const semJs = await navegador.newContext({ javaScriptEnabled: false });
const pj = await semJs.newPage();
await pj.goto(BASE + 'slides-painel.html', { waitUntil: 'load' });
checar(await pj.evaluate(() => [...document.querySelectorAll('.slide')].every((s) => !s.hidden)), 'sem JavaScript, todos os slides visíveis');
checar(await pj.isHidden('.controles-slides'), 'sem JavaScript, sem botões inúteis');

await navegador.close();
console.log(falhas.length ? `\n${falhas.length} FALHA(S)\n` + falhas.join('\n') : '\nSem falhas.');
process.exit(falhas.length ? 1 : 0);
