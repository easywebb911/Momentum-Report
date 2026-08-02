/* Menue + Textgroesse. Kein Framework, kein Netzwerkzugriff.
   Die Textgroesse setzt --app-fs auf <html>; weil die gesamte UI in rem
   bemessen ist, skaliert damit alles mit. */
(function () {
  "use strict";

  var KEY = "momentum-report:fs";
  var root = document.documentElement;
  var btn = document.getElementById("menu-btn");
  var overlay = document.getElementById("overlay");

  function setFontSize(px, persist) {
    root.style.setProperty("--app-fs", px + "px");
    if (persist) {
      try { localStorage.setItem(KEY, String(px)); } catch (err) { /* Privatmodus */ }
    }
    var buttons = document.querySelectorAll(".fs-btn");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute(
        "aria-pressed",
        buttons[i].getAttribute("data-fs") === String(px) ? "true" : "false"
      );
    }
  }

  var stored = null;
  try { stored = localStorage.getItem(KEY); } catch (err) { stored = null; }
  setFontSize(stored ? parseInt(stored, 10) : 16, false);

  function openMenu() {
    overlay.hidden = false;
    btn.setAttribute("aria-expanded", "true");
  }
  function closeMenu() {
    overlay.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  }

  if (btn && overlay) {
    btn.addEventListener("click", function () {
      if (overlay.hidden) { openMenu(); } else { closeMenu(); }
    });
    overlay.addEventListener("click", function (event) {
      if (event.target.hasAttribute("data-close")) { closeMenu(); }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !overlay.hidden) { closeMenu(); }
    });
  }

  document.addEventListener("click", function (event) {
    var target = event.target.closest ? event.target.closest(".fs-btn") : null;
    if (target) { setFontSize(parseInt(target.getAttribute("data-fs"), 10), true); }
  });
})();
