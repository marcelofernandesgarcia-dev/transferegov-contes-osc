/* app.js — comportamento dos recursos interativos. Regras em js/regras.js; valores em js/parametros.js.
 * Sem coleta nem armazenamento de dados: nada vai para rede, localStorage ou cookies.
 * Melhoria progressiva: sem JavaScript, os formulários ficam ocultos e as tabelas e listas da página seguem válidas.
 */
(function () {
  "use strict";

  var R = window.RegrasOSC;
  var P = window.ParametrosOSC;

  /** Registro estruturado de falha inesperada (sem dado pessoal: só contexto e código). */
  function registrarFalha(contexto, erro) {
    if (window.console && console.error) {
      console.error(JSON.stringify({ nivel: "erro", contexto: contexto, codigo: (erro && (erro.codigo || erro.name)) || "desconhecido" }));
    }
  }

  function texto(el, conteudo) { el.textContent = conteudo; }

  /* ---------------- Árvore de decisão do instrumento (Manual MROSC, item 4.11) */
  var NOMES = {
    "acordo-de-cooperacao": ["Acordo de cooperação", "Parceria sem repasse de recursos. Em regra não tem chamamento público, salvo se envolver comodato, doação de bens ou compartilhamento patrimonial."],
    "termo-de-colaboracao": ["Termo de colaboração", "Parceria com repasse, com plano de trabalho concebido pela administração pública. Em regra, há chamamento público."],
    "termo-de-fomento": ["Termo de fomento", "Parceria com repasse, com projeto concebido pela OSC. Em regra, há chamamento público."]
  };
  var ORDEM = ["repasse", "objeto", "define"];

  function iniciarArvore() {
    var form = document.getElementById("arvore");
    if (!form) return;
    var saida = document.getElementById("arvore-resultado");
    form.hidden = false;

    function respostas() {
      var r = {};
      ORDEM.forEach(function (nome) {
        var marcado = form.querySelector('input[name="' + nome + '"]:checked');
        if (marcado) r[nome] = marcado.value;
      });
      return r;
    }

    function atualizar(alterado) {
      // Mudou uma resposta anterior: apaga as seguintes, para não misturar caminhos.
      var idx = ORDEM.indexOf(alterado);
      if (idx >= 0) {
        ORDEM.slice(idx + 1).forEach(function (nome) {
          form.querySelectorAll('input[name="' + nome + '"]').forEach(function (i) { i.checked = false; });
        });
      }
      try {
        var r = respostas();
        var d = R.decidirInstrumento(r);
        // Pergunta 2 só com repasse; pergunta 3 só quando o objeto é projeto.
        form.querySelector('fieldset[data-pergunta="objeto"]').hidden = r.repasse !== "sim";
        form.querySelector('fieldset[data-pergunta="define"]').hidden = !(r.repasse === "sim" && r.objeto === "projeto");
        if (d.instrumento) {
          var n = NOMES[d.instrumento];
          saida.innerHTML = "";
          var forte = document.createElement("strong");
          texto(forte, n[0]);
          var p = document.createElement("p");
          texto(p, n[1]);
          saida.appendChild(forte);
          saida.appendChild(p);
        } else {
          texto(saida, "");
        }
      } catch (e) {
        registrarFalha("arvore", e);
        texto(saida, "Não foi possível indicar o instrumento com essas respostas. Use o botão Recomeçar e responda de novo.");
      }
    }

    form.addEventListener("change", function (ev) { atualizar(ev.target.name); });
    form.addEventListener("reset", function () { window.setTimeout(function () { atualizar("repasse"); form.querySelector("input").focus(); }, 0); });
    form.addEventListener("submit", function (ev) { ev.preventDefault(); });
    atualizar(null);
  }

  /* ---------------- Calculadora do custo de elaboração da proposta (Manual MROSC, item 6.11.6) */
  var MENSAGENS = {
    "vazio": "Informe o valor global para calcular.",
    "invalido": "Use apenas números, com vírgula para os centavos. Exemplo: 350.000,00.",
    "nao-positivo": "O valor global precisa ser maior que zero."
  };

  function iniciarCalculadora() {
    var form = document.getElementById("calculadora");
    if (!form) return;
    var campo = document.getElementById("valor-global");
    var erro = document.getElementById("valor-erro");
    var saida = document.getElementById("calc-resultado");
    form.hidden = false;

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      texto(erro, "");
      campo.removeAttribute("aria-invalid");
      saida.innerHTML = "";
      try {
        var valor = R.lerValorReais(campo.value);
        var r = R.tetoCustoElaboracao(valor, P);
        var forte = document.createElement("strong");
        texto(forte, "Até " + R.formatarReais(r.teto));
        var p = document.createElement("p");
        texto(p, "podem ser previstos no plano de trabalho para custear a elaboração da proposta, se a parceria for celebrada." +
          (r.limitadoPeloTeto ? " O valor ficou limitado ao teto de " + R.formatarReais(P.custo_elaboracao_proposta.teto_reais) + "." : ""));
        saida.appendChild(forte);
        saida.appendChild(p);
      } catch (e) {
        var msg = e && e.name === "ErroEntrada" ? MENSAGENS[e.codigo] : null;
        if (!msg) {
          registrarFalha("calculadora", e);
          msg = "Não foi possível calcular agora. Recarregue a página e tente de novo.";
        }
        texto(erro, msg);
        campo.setAttribute("aria-invalid", "true");
        campo.focus();
      }
    });
  }

  /* ---------------- Checklists (prontidão: Manual MROSC 6.1 a 6.7 e 7.1.2; editais e execução: ver cada formulário).
   * Cada <form class="checklist"> tem a sua área .resultado; data-completo traz a mensagem de lista completa. */
  var MSG_COMPLETO_PADRAO = "Sua organização reúne os documentos que o Manual MROSC lista para a celebração. Confira também as exigências específicas do edital.";

  function iniciarChecklists() {
    Array.prototype.forEach.call(document.querySelectorAll("form.checklist"), iniciarChecklist);
  }

  function iniciarChecklist(form) {
    var saida = form.querySelector(".resultado");
    var caixas = Array.prototype.slice.call(form.querySelectorAll('input[type="checkbox"]'));
    if (!saida || !caixas.length) return;
    var msgCompleto = form.getAttribute("data-completo") || MSG_COMPLETO_PADRAO;
    form.hidden = false;

    function atualizar(anunciar) {
      try {
        var r = R.avaliarChecklist(caixas.map(function (c) { return { id: c.id, marcado: c.checked }; }));
        saida.innerHTML = "";
        saida.classList.toggle("resultado-ok", r.completo);
        if (!anunciar && r.marcados === 0) return; // estado inicial: sem mensagem
        var forte = document.createElement("strong");
        if (r.completo) {
          texto(forte, "Todos os itens marcados.");
          var ok = document.createElement("p");
          texto(ok, msgCompleto);
          saida.appendChild(forte);
          saida.appendChild(ok);
          return;
        }
        texto(forte, r.faltam === 1 ? "Falta 1 item." : "Faltam " + r.faltam + " itens.");
        saida.appendChild(forte);
        var lista = document.createElement("ul");
        lista.className = "pendentes";
        r.pendentes.forEach(function (id) {
          var caixa = document.getElementById(id);
          var li = document.createElement("li");
          var a = document.createElement("a");
          a.href = caixa.getAttribute("data-secao") || "#prepare-se";
          texto(a, form.querySelector('label[for="' + id + '"]').textContent);
          li.appendChild(a);
          lista.appendChild(li);
        });
        saida.appendChild(lista);
      } catch (e) {
        registrarFalha("checklist", e);
        texto(saida, "Não foi possível atualizar o checklist. Use a tabela de requisitos como lista de conferência.");
      }
    }

    form.addEventListener("change", function () { atualizar(true); });
    form.addEventListener("reset", function () { window.setTimeout(function () { atualizar(false); caixas[0].focus(); }, 0); });
    form.addEventListener("submit", function (ev) { ev.preventDefault(); });
    atualizar(false);
  }

  /* ---------------- Perguntas de fixação (uma ao fim de cada seção).
   * Cada <form class="fixacao" data-correta="…"> traz as opções e, em .explicacoes, uma explicação por opção.
   * A resposta é conferida no navegador: nada é enviado nem guardado. */
  function iniciarFixacoes() {
    Array.prototype.forEach.call(document.querySelectorAll("form.fixacao"), iniciarFixacao);
  }

  function iniciarFixacao(form) {
    var saida = form.querySelector(".resultado");
    var correta = form.getAttribute("data-correta");
    if (!saida || !correta) return;
    form.hidden = false;

    function explicacao(valor) {
      var p = form.querySelector('.explicacoes [data-opcao="' + valor + '"]');
      return p ? p.textContent : "";
    }
    function rotulo(valor) {
      var i = form.querySelector('input[value="' + valor + '"]');
      return i && i.parentNode ? i.parentNode.textContent.trim() : "";
    }
    function limpar() {
      saida.innerHTML = "";
      saida.classList.remove("resultado-ok", "resultado-erro");
    }

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      limpar();
      try {
        var marcada = form.querySelector('input[type="radio"]:checked');
        var r = R.avaliarFixacao(marcada ? marcada.value : null, correta);
        var forte = document.createElement("strong");
        if (r.situacao === "vazio") {
          texto(forte, "Escolha uma resposta para conferir.");
          saida.appendChild(forte);
          return;
        }
        // Certo e errado têm texto próprio, não só cor.
        texto(forte, r.situacao === "certo" ? "Correto." : "Ainda não.");
        saida.classList.add(r.situacao === "certo" ? "resultado-ok" : "resultado-erro");
        saida.appendChild(forte);
        var p = document.createElement("p");
        texto(p, explicacao(marcada.value));
        saida.appendChild(p);
        if (r.situacao === "errado") {
          var certa = document.createElement("p");
          texto(certa, "Resposta certa: " + rotulo(correta) + ". " + explicacao(correta));
          saida.appendChild(certa);
        }
      } catch (e) {
        registrarFalha("fixacao", e);
        texto(saida, "Não foi possível conferir a resposta. Recarregue a página e tente de novo.");
      }
    });
    form.addEventListener("reset", function () {
      window.setTimeout(function () { limpar(); var i = form.querySelector("input"); if (i) i.focus(); }, 0);
    });
  }

  /* Camada que substitui um recurso interativo quando não há JavaScript (ex.: a tabela de requisitos, que o
   * <noscript> do checklist indica): vem aberta no HTML e é fechada aqui, com o interativo já disponível. */
  function fecharCamadasComJs() {
    Array.prototype.forEach.call(document.querySelectorAll("details[data-fechar-com-js]"), function (d) { d.open = false; });
  }

  function iniciar() {
    fecharCamadasComJs();
    if (!R || !P) {
      registrarFalha("inicio", { codigo: !R ? "regras-ausentes" : "parametros-ausentes" });
      return; // formulários continuam ocultos; o conteúdo estático da página segue válido
    }
    iniciarArvore();
    iniciarCalculadora();
    iniciarChecklists();
    iniciarFixacoes();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
