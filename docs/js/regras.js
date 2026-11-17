/* regras.js — regras de negócio puras da landing (sem DOM, sem estado, sem dependência).
 * Fonte das regras: Manual MROSC 2025 (F1). Valores vêm de js/parametros.js (gerado de conteudo/parametros.json).
 * Formato UMD simples: no navegador expõe window.RegrasOSC (funciona aberto pelo arquivo, sem módulos ES);
 * no Node exporta via module.exports para os testes (testes/regras.test.js).
 */
(function (raiz, fabrica) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = fabrica();
  } else {
    raiz.RegrasOSC = fabrica();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /** Erro de entrada com código estável, para a interface escolher a mensagem ao usuário. */
  function ErroEntrada(codigo) {
    var e = new Error(codigo);
    e.name = "ErroEntrada";
    e.codigo = codigo;
    return e;
  }

  /**
   * Converte texto em reais no formato brasileiro ("1.234.567,89", "R$ 50000", "50000,5") em número.
   * Lança ErroEntrada: "vazio" | "invalido" | "nao-positivo".
   */
  function lerValorReais(texto) {
    if (texto === null || texto === undefined) throw ErroEntrada("vazio");
    var s = String(texto).replace(/R\$/i, "").replace(/\s/g, "");
    if (s === "") throw ErroEntrada("vazio");
    // Só dígitos, pontos de milhar opcionais e até duas casas decimais após a vírgula.
    if (!/^-?(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?$/.test(s)) throw ErroEntrada("invalido");
    var n = Number(s.replace(/\./g, "").replace(",", "."));
    if (!isFinite(n)) throw ErroEntrada("invalido");
    if (n <= 0) throw ErroEntrada("nao-positivo");
    return n;
  }

  /** Arredonda para centavos sem erro de ponto flutuante acumulado. */
  function centavos(n) {
    return Math.round(n * 100) / 100;
  }

  /**
   * Teto do custo de elaboração da proposta: menor valor entre percentual × valor global e o teto em reais.
   * F1 §6.11.6 (cita Decreto nº 8.726/2016, art. 39, V). Retorna { teto, limitadoPeloTeto }.
   */
  function tetoCustoElaboracao(valorGlobal, parametros) {
    if (typeof valorGlobal !== "number" || !isFinite(valorGlobal)) throw ErroEntrada("invalido");
    if (valorGlobal <= 0) throw ErroEntrada("nao-positivo");
    var p = parametros && parametros.custo_elaboracao_proposta;
    if (!p || !(p.percentual_valor_global > 0) || !(p.teto_reais > 0)) throw ErroEntrada("parametros");
    var porPercentual = centavos(valorGlobal * p.percentual_valor_global);
    var limitado = porPercentual >= p.teto_reais;
    return { teto: limitado ? p.teto_reais : porPercentual, limitadoPeloTeto: limitado };
  }

  /** Formata número como moeda brasileira ("R$ 50.000,00") sem depender de Intl. */
  function formatarReais(n) {
    var partes = centavos(n).toFixed(2).split(".");
    var inteiro = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return "R$ " + inteiro + "," + partes[1];
  }

  /**
   * Árvore de decisão do instrumento (F1 §4.11).
   * respostas: { repasse: "sim"|"nao", objeto: "atividade"|"projeto", define: "administracao"|"osc" }
   * Retorna { instrumento, proxima }: instrumento definido, ou a próxima pergunta a responder.
   */
  function decidirInstrumento(respostas) {
    var r = respostas || {};
    if (r.repasse === undefined || r.repasse === null || r.repasse === "") return { instrumento: null, proxima: "repasse" };
    if (r.repasse === "nao") return { instrumento: "acordo-de-cooperacao", proxima: null };
    if (r.repasse !== "sim") throw ErroEntrada("invalido");
    if (!r.objeto) return { instrumento: null, proxima: "objeto" };
    if (r.objeto === "atividade") return { instrumento: "termo-de-colaboracao", proxima: null };
    if (r.objeto !== "projeto") throw ErroEntrada("invalido");
    if (!r.define) return { instrumento: null, proxima: "define" };
    if (r.define === "administracao") return { instrumento: "termo-de-colaboracao", proxima: null };
    if (r.define === "osc") return { instrumento: "termo-de-fomento", proxima: null };
    throw ErroEntrada("invalido");
  }

  /**
   * Situação do checklist de prontidão.
   * itens: [{ id, marcado }]. Retorna { total, marcados, faltam, pendentes: [ids], completo }.
   */
  function avaliarChecklist(itens) {
    if (!Array.isArray(itens)) throw ErroEntrada("invalido");
    var pendentes = [];
    var marcados = 0;
    for (var i = 0; i < itens.length; i++) {
      if (itens[i] && itens[i].marcado === true) marcados++;
      else pendentes.push(itens[i] ? itens[i].id : null);
    }
    return {
      total: itens.length,
      marcados: marcados,
      faltam: itens.length - marcados,
      pendentes: pendentes,
      completo: itens.length > 0 && marcados === itens.length
    };
  }

  /**
   * Confere a resposta de uma pergunta de fixação (prática de recuperação; nada é guardado).
   * escolhida: valor marcado pelo participante (vazio se nenhum); correta: valor certo definido na página.
   * Retorna { situacao: "vazio" | "certo" | "errado" }. Lança ErroEntrada("invalido") se a página não definir a resposta certa.
   */
  function avaliarFixacao(escolhida, correta) {
    if (correta === null || correta === undefined || String(correta).trim() === "") throw ErroEntrada("invalido");
    if (escolhida === null || escolhida === undefined || String(escolhida).trim() === "") return { situacao: "vazio" };
    return { situacao: String(escolhida).trim() === String(correta).trim() ? "certo" : "errado" };
  }

  return {
    ErroEntrada: ErroEntrada,
    avaliarFixacao: avaliarFixacao,
    lerValorReais: lerValorReais,
    tetoCustoElaboracao: tetoCustoElaboracao,
    formatarReais: formatarReais,
    decidirInstrumento: decidirInstrumento,
    avaliarChecklist: avaliarChecklist
  };
});
