// Wires the saved-analysis page: tab switching and the interactive stress meter.
// Reads everything from the server-rendered DOM, so no inline script is needed.
(function () {
  "use strict";
  var root = document.getElementById("result-view");
  if (!root) return;

  var tabs = root.querySelectorAll(".tab");
  tabs.forEach(function (t) {
    t.addEventListener("click", function () {
      tabs.forEach(function (x) { x.classList.remove("active"); });
      t.classList.add("active");
      var i = t.getAttribute("data-tab");
      root.querySelectorAll(".panel").forEach(function (p) {
        p.classList.toggle("active", p.getAttribute("data-panel") === i);
      });
    });
  });

  var fill = root.querySelector("#meter-fill");
  var val = root.querySelector("#meter-val");
  var switches = root.querySelectorAll(".switch");
  function recompute() {
    var support = 100;
    switches.forEach(function (s) {
      if (s.classList.contains("off")) support -= parseInt(s.getAttribute("data-w"), 10);
    });
    support = Math.max(0, Math.min(100, support));
    if (fill) { fill.style.width = support + "%";
      fill.style.background = support < 45 ? "#9E3B2A" : (support < 75 ? "#A9741F" : "linear-gradient(90deg,#A97C22,#4F7350)"); }
    if (val) val.textContent = support;
  }
  switches.forEach(function (s) {
    s.addEventListener("click", function () {
      s.classList.toggle("off");
      s.textContent = s.classList.contains("off") ? "false" : "holds";
      recompute();
    });
  });
})();
