(function () {
  "use strict";
  var root = document.querySelector("[data-cipher-trace]");
  if (!root) return;
  var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-step-tab]"));
  function select(index, focus) {
    tabs.forEach(function (tab, i) {
      tab.setAttribute("aria-current", i === index ? "step" : "false");
    });
    var panel = root.querySelector("[data-step='" + index + "']");
    if (panel) panel.scrollIntoView({block: "nearest", behavior: "auto"});
    if (focus) tabs[index].focus();
  }
  tabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () { select(index, false); });
    tab.addEventListener("keydown", function (event) {
      var next = index;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault(); select(next, true);
    });
  });
}());
