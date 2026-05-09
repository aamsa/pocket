// Pocket — small client-side glue. No build step.
// - Re-runs Lucide icon rendering after HTMX swaps
// - Re-instantiates ApexCharts for any [data-apex-chart] block
// - Provides Alpine `x-rupiah` directive for IDR-formatted inputs

(function () {
  "use strict";

  function renderIcons() {
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  function rupiah(n) {
    var v = Math.round(Number(n) || 0);
    var sign = v < 0 ? "-" : "";
    return sign + "Rp " + Math.abs(v).toLocaleString("id-ID");
  }

  function applyFormatters(options) {
    if (!options || options._format !== "rupiah") return options;
    if (options.yaxis && options.yaxis.labels) options.yaxis.labels.formatter = rupiah;
    options.tooltip = options.tooltip || {};
    options.tooltip.y = Object.assign({}, options.tooltip.y, { formatter: rupiah });
    return options;
  }

  function hydrateCharts(root) {
    if (!window.ApexCharts) return;
    var nodes = (root || document).querySelectorAll("[data-apex-chart]");
    nodes.forEach(function (el) {
      if (el.__apexInstance) {
        el.__apexInstance.destroy();
        el.__apexInstance = null;
      }
      var dataId = el.getAttribute("data-source");
      var dataNode = dataId ? document.getElementById(dataId) : null;
      if (!dataNode) return;
      try {
        var options = applyFormatters(JSON.parse(dataNode.textContent));
        var chart = new ApexCharts(el, options);
        chart.render();
        el.__apexInstance = chart;
      } catch (err) {
        console.error("Chart hydration failed", err);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderIcons();
    hydrateCharts(document);
  });

  document.addEventListener("htmx:afterSwap", function (e) {
    renderIcons();
    hydrateCharts(e.target);
  });

  // Alpine plugin: x-rupiah formats the input as `1.250.000` on blur,
  // and writes the raw integer to a hidden sibling input on every change.
  document.addEventListener("alpine:init", function () {
    if (!window.Alpine) return;

    function digitsOnly(s) {
      return (s || "").toString().replace(/\D+/g, "");
    }
    function formatGrouped(d) {
      if (!d) return "";
      return d.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    }

    window.Alpine.directive("rupiah", function (el, { expression }, { evaluate }) {
      var hidden = document.querySelector(expression);

      function sync() {
        var raw = digitsOnly(el.value);
        el.value = formatGrouped(raw);
        if (hidden) hidden.value = raw;
      }

      el.setAttribute("inputmode", "numeric");
      el.setAttribute("autocomplete", "off");
      el.addEventListener("input", sync);
      el.addEventListener("blur", sync);
      sync();
    });
  });
})();
