/*
 * Shell — menu móvel da área do almoxarifado. Carregado com `defer` no <head>; os listeners
 * ficam em `document` e sobrevivem à troca do <body> pelo HTMX. Sem JavaScript, a navegação
 * aparece aberta (o botão só existe com `html.js`).
 */
(function () {
  "use strict";

  function fechar(lateral, devolverFoco) {
    var botao = lateral.querySelector("[data-menu-toggle]");
    lateral.removeAttribute("data-aberto");
    if (botao) {
      botao.setAttribute("aria-expanded", "false");
      if (devolverFoco) botao.focus();
    }
  }

  document.addEventListener("click", function (evento) {
    var alvo = evento.target;
    if (!alvo || !alvo.closest) return;
    var botao = alvo.closest("[data-menu-toggle]");
    if (!botao) return;
    var lateral = botao.closest(".app-lateral");
    if (!lateral) return;
    if (lateral.hasAttribute("data-aberto")) {
      fechar(lateral, false);
    } else {
      lateral.setAttribute("data-aberto", "");
      botao.setAttribute("aria-expanded", "true");
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    var lateral = document.querySelector(".app-lateral[data-aberto]");
    if (lateral) fechar(lateral, true);
  });
})();
