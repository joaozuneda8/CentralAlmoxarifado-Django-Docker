/*
 * Página Catálogo, formulários dos robôs de importação (as abas são o componente comum, abas.js):
 * campo do arquivo CSV só quando a origem é "Enviar um CSV" e botões seguindo o andamento.
 * Carregado no <head> com defer. Sem JavaScript, o campo do arquivo aparece.
 */
(function () {
  "use strict";

  // O campo do arquivo só faz sentido com a origem "Enviar um CSV".
  function sincronizarOrigem(form) {
    var csv = form.querySelector('input[name="origem"][value="csv"]');
    var campo = form.querySelector("[data-robo-arquivo]");
    if (campo) campo.hidden = !(csv && csv.checked);
  }

  // Cadastro: "só os novos" não vale com CSV enviado (o arquivo é sempre o cadastro inteiro) nem
  // antes da primeira carga; o aviso de "forçar" só aparece na recarga completa e o botão diz qual.
  function sincronizarModo(form) {
    var modos = form.querySelector("[data-robo-modos]");
    if (!modos) return;
    var novos = modos.querySelector('input[value="novos"]');
    var completo = modos.querySelector('input[value="completo"]');
    var csv = form.querySelector('input[name="origem"][value="csv"]');
    var comCsv = !!(csv && csv.checked);
    var semCarga = modos.getAttribute("data-sem-carga") === "1";
    novos.disabled = comCsv || semCarga;
    if (novos.disabled && novos.checked) completo.checked = true;
    var dica = modos.querySelector("[data-dica-novos]");
    if (dica) {
      if (!dica.hasAttribute("data-texto-original")) {
        dica.setAttribute("data-texto-original", dica.textContent);
      }
      dica.textContent =
        comCsv && !semCarga ? dica.getAttribute("data-texto-csv") : dica.getAttribute("data-texto-original");
    }
    var risco = form.querySelector("[data-robo-risco]");
    if (risco) risco.hidden = !completo.checked;
    var texto = form.querySelector("[data-robo-texto][data-rotulo-completo]");
    if (texto) {
      if (!texto.hasAttribute("data-rotulo-original")) {
        texto.setAttribute("data-rotulo-original", texto.textContent);
      }
      texto.textContent = completo.checked
        ? texto.getAttribute("data-rotulo-completo")
        : texto.getAttribute("data-rotulo-original");
    }
  }

  // Saídas: "Usar o padrão" devolve o período que o comando usaria sozinho. Sem JavaScript o botão
  // fica escondido (apagar os campos faz o mesmo).
  document.addEventListener("click", function (e) {
    var botao = e.target.closest && e.target.closest("[data-periodo-padrao]");
    if (!botao || !botao.form) return;
    botao.form.elements.desde.value = botao.getAttribute("data-desde");
    botao.form.elements.ate.value = botao.getAttribute("data-ate");
  });

  document.addEventListener("change", function (e) {
    if (e.target.name === "origem" && e.target.form) sincronizarOrigem(e.target.form);
    if ((e.target.name === "origem" || e.target.name === "modo") && e.target.form) {
      sincronizarModo(e.target.form);
    }
  });

  function iniciar() {
    document.querySelectorAll("[data-periodo-padrao]").forEach(function (botao) {
      botao.hidden = false;
    });
    document.querySelectorAll("form[data-robo-form]").forEach(sincronizarOrigem);
    document.querySelectorAll("form[data-robo-form]").forEach(sincronizarModo);
  }
  document.addEventListener("DOMContentLoaded", iniciar);

  // A situação é recarregada pelo HTMX enquanto há importação; os botões dos robôs, que ficam fora
  // dela, acompanham o que ela informa.
  document.addEventListener("htmx:after:swap", function () {
    var situacao = document.getElementById("situacao-catalogo");
    if (!situacao) return;
    var andando = situacao.getAttribute("data-em-andamento") === "1";
    document.querySelectorAll("[data-robo-rodar]").forEach(function (botao) {
      botao.disabled = andando;
    });
    document.querySelectorAll("[data-robo-aviso]").forEach(function (aviso) {
      aviso.hidden = !andando;
    });
  });
})();
