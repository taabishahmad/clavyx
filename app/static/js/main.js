// Small, framework-free helpers used across the site. Kept in a file (not inline)
// so the Content Security Policy can stay strict.
(function () {
  "use strict";

  // Mobile navigation toggle
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () { links.classList.toggle("open"); });
  }

  // Graceful image fallback: if a generated image is missing, show the stone
  // placeholder instead of a broken icon.
  document.querySelectorAll("img[data-fallback]").forEach(function (img) {
    img.addEventListener("error", function () {
      var box = img.closest(".hero-art, .feature-art, .img-holder");
      if (box) { img.style.display = "none"; box.classList.add("img-fallback"); }
    });
  });

  // Live password strength meter on any element with data-strength
  document.querySelectorAll("input[data-strength]").forEach(function (input) {
    var bar = document.querySelector(input.getAttribute("data-strength"));
    if (!bar) return;
    var fill = bar.querySelector("span");
    input.addEventListener("input", function () {
      var v = input.value, score = 0;
      if (v.length >= 8) score++;
      if (/[A-Za-z]/.test(v) && /\d/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      if (v.length >= 12) score++;
      var pct = [0, 30, 60, 85, 100][score];
      var col = ["#D8CBB1", "#A9741F", "#A9741F", "#4F7350", "#4F7350"][score];
      fill.style.width = pct + "%"; fill.style.background = col;
    });
  });

  // Auto-dismiss flash messages after a while
  document.querySelectorAll("[data-autohide]").forEach(function (el) {
    setTimeout(function () { el.style.transition = "opacity .4s"; el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 400); }, 6000);
  });
})();
