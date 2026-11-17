// Visualizador de slides: sem JavaScript, todos os slides aparecem em lista;
// com JavaScript, um slide por vez, com botões, setas do teclado e endereço #slide-N.
// Não grava nada e não acessa a rede.
(function () {
  'use strict';
  var secao = document.querySelector('.apresentacao');
  if (!secao) { return; }
  var slides = Array.prototype.slice.call(secao.querySelectorAll('.slide'));
  var total = slides.length;
  var controles = secao.querySelector('.controles-slides');
  if (!total || !controles) { return; }
  var posicao = controles.querySelector('.posicao-slide');
  var anterior = controles.querySelector('[data-ir="-1"]');
  var proximo = controles.querySelector('[data-ir="1"]');
  var atual = 0;

  function indiceDoEndereco() {
    var m = /^#slide-(\d+)$/.exec(window.location.hash);
    var n = m ? parseInt(m[1], 10) : 1;
    return n >= 1 && n <= total ? n - 1 : 0;
  }

  function mostrar(i, gravarEndereco) {
    atual = Math.max(0, Math.min(total - 1, i));
    slides.forEach(function (s, k) { s.hidden = k !== atual; });
    var img = slides[atual].querySelector('img');
    if (img) { img.loading = 'eager'; }
    anterior.setAttribute('aria-disabled', String(atual === 0));
    proximo.setAttribute('aria-disabled', String(atual === total - 1));
    posicao.textContent = 'Slide ' + (atual + 1) + ' de ' + total;
    // Só grava #slide-N depois de uma ação: na abertura, mudar o endereço desloca o ponto de partida do Tab no Chrome.
    if (gravarEndereco && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#slide-' + (atual + 1));
    }
  }

  function ir(passo) {
    var destino = atual + passo;
    if (destino < 0 || destino > total - 1) { return; }
    mostrar(destino, true);
  }

  controles.addEventListener('click', function (ev) {
    var botao = ev.target.closest('[data-ir]');
    if (botao) { ir(parseInt(botao.getAttribute('data-ir'), 10)); }
  });

  document.addEventListener('keydown', function (ev) {
    if (ev.altKey || ev.ctrlKey || ev.metaKey) { return; }
    var alvo = ev.target;
    if (alvo && /^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName)) { return; }
    // Só as setas laterais: Page Up/Down, Home e End continuam rolando a página.
    if (ev.key === 'ArrowRight') { ev.preventDefault(); ir(1); }
    else if (ev.key === 'ArrowLeft') { ev.preventDefault(); ir(-1); }
  });

  window.addEventListener('hashchange', function () { mostrar(indiceDoEndereco()); });

  secao.classList.add('ativa');
  controles.hidden = false;
  // Controles antes da lista, para virem logo depois do título na ordem de leitura e de foco.
  secao.insertBefore(controles, secao.firstChild);
  mostrar(indiceDoEndereco());
})();
