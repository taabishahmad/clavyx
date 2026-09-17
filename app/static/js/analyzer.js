// The analyzer: send the argument to the API, then render the full result with
// tabs, the foundations map, the keystone view, an interactive stress test, the
// opposing case, the weakest link, and the evidence ledger.
(function () {
  "use strict";
  var form = document.getElementById("analyze-form");
  if (!form) return;

  var input = document.getElementById("arg-input");
  var count = document.getElementById("char-count");
  var out = document.getElementById("result-area");
  var btn = document.getElementById("analyze-btn");
  var csrf = document.querySelector('meta[name="csrf"]').getAttribute("content");

  if (input && count) {
    var upd = function () { count.textContent = input.value.length + " / 6000"; };
    input.addEventListener("input", upd); upd();
  }

  document.querySelectorAll(".chip[data-example]").forEach(function (c) {
    c.addEventListener("click", function () {
      input.value = c.getAttribute("data-example");
      input.dispatchEvent(new Event("input")); input.focus();
    });
  });

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = (input.value || "").trim();
    if (text.length < 20) { out.innerHTML = alert_("Please paste a real argument, at least a couple of sentences."); return; }
    btn.disabled = true;
    out.innerHTML = '<div class="loading"><div class="spinner"></div>Reading your argument and finding its keystone...</div>';

    fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ text: text })
    }).then(function (r) {
      return r.json().then(function (data) { return { ok: r.ok, data: data }; });
    }).then(function (res) {
      btn.disabled = false;
      if (!res.ok) { out.innerHTML = alert_(res.data.error || "Something went wrong. Please try again."); return; }
      render(res.data);
    }).catch(function () {
      btn.disabled = false;
      out.innerHTML = alert_("Could not reach the server. Please try again.");
    });
  });

  function alert_(msg) { return '<div class="alert alert-error">' + esc(msg) + "</div>"; }

  function render(d) {
    var minimalSet = d.minimal_set || [];
    var isKey = {}; minimalSet.forEach(function (m) { isKey[m] = true; });

    // tabs
    var html = '';
    html += '<div class="result-head">';
    html += '<div><span class="pill">Analysis complete</span> ';
    html += '<span class="pill pill-stone">engine: ' + esc(d.engine) + '</span></div>';
    if (d._id) html += '<a class="btn btn-ghost" href="/analysis/' + d._id + '">Open saved view</a>';
    html += '</div>';

    html += '<div class="tabs">';
    ["Foundations", "Keystone", "Stress test", "Opposing case", "Weakest link", "Evidence"].forEach(function (t, i) {
      html += '<button class="tab' + (i === 0 ? " active" : "") + '" data-tab="' + i + '">' + t + '</button>';
    });
    html += '</div>';

    // 0: foundations map
    html += panel(0, foundations(d, isKey));
    // 1: keystone
    html += panel(1, keystone(minimalSet));
    // 2: stress test
    html += panel(2, stress(d));
    // 3: opposing case
    html += panel(3, '<div class="card card-pad"><h3>The strongest fair opposing case</h3><p>' + esc(d.opposing_case) + '</p><p class="muted" style="font-size:.85rem">A steelman, not a strawman. It targets the load bearing assumption rather than a weak side point.</p></div>');
    // 4: weakest link
    html += panel(4, '<div class="card card-pad"><span class="pill">Most fragile step</span><h3 style="margin-top:12px">' + esc(d.weakest_link.text) + '</h3><p>' + esc(d.weakest_link.why) + '</p></div>');
    // 5: evidence
    html += panel(5, evidence(d));

    out.innerHTML = html;
    wireTabs();
    wireStress(d);
  }

  function panel(i, inner) { return '<div class="panel' + (i === 0 ? " active" : "") + '" data-panel="' + i + '">' + inner + "</div>"; }

  function foundations(d, isKey) {
    var h = '<div class="map">';
    h += '<div class="node concl">' + esc(d.conclusion) + '</div>';
    h += '<div class="stem"></div>';
    h += '<div class="legs">';
    (d.assumptions || []).forEach(function (a) {
      var key = isKey[a.text];
      h += '<div class="leg"><div class="node ' + (key ? "key" : "") + '">';
      h += (key ? '<span class="badge medium">keystone</span><br>' : "");
      h += esc(a.text);
      h += '<div style="margin-top:8px"><span class="badge ' + a.influence + '">' + a.influence + " influence</span></div>";
      h += '</div></div>';
    });
    h += '</div>';
    h += '<p class="estimate-note">Highlighted stones are the keystones: the assumptions the conclusion cannot stand without.</p>';
    h += '</div>';
    return h;
  }

  function keystone(minimal) {
    var h = '<div class="card card-pad"><span class="pill pill-brass">Minimal sufficient set</span>';
    h += '<h3 style="margin-top:12px">The few assumptions your conclusion truly needs</h3>';
    h += '<p class="muted">Remove any one of these and the conclusion loses its support. Everything else is secondary.</p>';
    if (!minimal.length) { h += '<p>No single keystone stood out for this argument.</p>'; }
    else { h += '<div style="margin-top:10px">'; minimal.forEach(function (m) {
      h += '<div class="assum"><div class="rk">key</div><div>' + esc(m) + '</div></div>'; }); h += '</div>'; }
    h += '</div>';
    return h;
  }

  function stress(d) {
    var h = '<div class="card card-pad"><h3>Stress test</h3>';
    h += '<p class="muted">Turn an assumption off to see, not just be told, how much your conclusion leans on it.</p>';
    h += '<div class="meter-wrap"><div class="meter"><span id="meter-fill" style="width:100%"></span></div>';
    h += '<p style="margin-top:8px"><b>Estimated support: <span id="meter-val">100</span>%</b></p></div>';
    h += '<div class="toggles" id="stress-toggles">';
    (d.assumptions || []).forEach(function (a, i) {
      h += '<div class="toggle"><span>' + esc(a.text) + ' <span class="badge ' + a.influence + '">' + a.influence + '</span></span>';
      h += '<span class="switch" data-i="' + i + '" data-w="' + weightFor(a) + '">holds</span></div>';
    });
    h += '</div>';
    h += '<p class="estimate-note">This support figure is an estimate produced by the model, shown to make dependency tangible. It is not a measured probability.</p>';
    h += '</div>';
    return h;
  }

  function weightFor(a) { return a.influence === "high" ? 45 : (a.influence === "medium" ? 22 : 9); }

  function evidence(d) {
    var h = '<div class="card card-pad"><h3>Evidence ledger</h3><p class="muted">What would rationally change your mind, tied to the assumption it tests.</p>';
    h += '<table class="ledger"><thead><tr><th>Assumption</th><th>Evidence that would settle it</th></tr></thead><tbody>';
    (d.evidence || []).forEach(function (e) {
      h += '<tr><td>' + esc(e.assumption) + '</td><td>' + esc(e.evidence) + '</td></tr>';
    });
    h += '</tbody></table></div>';
    return h;
  }

  function wireTabs() {
    var tabs = out.querySelectorAll(".tab");
    tabs.forEach(function (t) {
      t.addEventListener("click", function () {
        tabs.forEach(function (x) { x.classList.remove("active"); });
        t.classList.add("active");
        var i = t.getAttribute("data-tab");
        out.querySelectorAll(".panel").forEach(function (p) {
          p.classList.toggle("active", p.getAttribute("data-panel") === i);
        });
      });
    });
  }

  function wireStress() {
    var fill = out.querySelector("#meter-fill");
    var val = out.querySelector("#meter-val");
    var switches = out.querySelectorAll(".switch");
    function recompute() {
      var support = 100;
      switches.forEach(function (s) {
        if (s.classList.contains("off")) support -= parseInt(s.getAttribute("data-w"), 10);
      });
      support = Math.max(0, Math.min(100, support));
      fill.style.width = support + "%";
      fill.style.background = support < 45 ? "#9E3B2A" : (support < 75 ? "#A9741F" : "linear-gradient(90deg,#A97C22,#4F7350)");
      val.textContent = support;
    }
    switches.forEach(function (s) {
      s.addEventListener("click", function () {
        s.classList.toggle("off");
        s.textContent = s.classList.contains("off") ? "false" : "holds";
        recompute();
      });
    });
  }
})();
