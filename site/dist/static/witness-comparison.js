(function () {
  "use strict";
  var root = document.querySelector("[data-witness-comparison]");
  if (!root) return;
  var stage = root.querySelector(".comparison-stage");
  var svg = root.querySelector(".comparison-ribbons");

  function drawRibbons() {
    if (!stage || !svg || window.innerWidth <= 800) return;
    var box = stage.getBoundingClientRect();
    svg.setAttribute("viewBox", "0 0 " + box.width + " " + box.height);
    svg.replaceChildren();
    for (var line = 1; line <= 4; line += 1) {
      var nodes = stage.querySelectorAll('.witness-lines:not([hidden]) [data-verse-line="' + line + '"]');
      for (var i = 0; i < nodes.length - 1; i += 1) {
        var a = nodes[i].getBoundingClientRect();
        var b = nodes[i + 1].getBoundingClientRect();
        var x1 = a.right - box.left, y1 = a.top + a.height / 2 - box.top;
        var x2 = b.left - box.left, y2 = b.top + b.height / 2 - box.top;
        var bend = Math.max(16, (x2 - x1) * .45);
        var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", "M" + x1 + "," + y1 + " C" + (x1 + bend) + "," + y1 + " " + (x2 - bend) + "," + y2 + " " + x2 + "," + y2);
        svg.appendChild(path);
      }
    }
  }

  root.querySelectorAll("[data-layer]").forEach(function (button) {
    button.addEventListener("click", function () {
      var layer = button.getAttribute("data-layer");
      root.querySelectorAll("[data-layer]").forEach(function (item) {
        item.setAttribute("aria-pressed", item === button ? "true" : "false");
      });
      root.querySelectorAll(".witness-lines").forEach(function (list) {
        list.hidden = !list.classList.contains("witness-lines-" + layer);
      });
      drawRibbons();
    });
  });
  window.addEventListener("resize", drawRibbons);
  window.addEventListener("load", drawRibbons);
  drawRibbons();
}());
