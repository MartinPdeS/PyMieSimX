(function () {
  "use strict";

  document.addEventListener("click", function (event) {
    const target = event.target;
    if (!(target instanceof Element) || !target.closest("#page-content")) {
      return;
    }
    // Controls and plots remain usable while a configuration panel is open.
    if (target.closest(".right-tab-rail, .right-sidebar-panel, button, a, input, select, textarea, label, summary, [role='button'], [role='option'], [role='combobox'], .Select, .js-plotly-plot, [contenteditable='true']")) {
      return;
    }
    if (document.querySelector(".right-sidebar-panel.open") && window.dash_clientside?.set_props) {
      window.dash_clientside.set_props("sidebar-background-click", {data: Date.now()});
    }
  });
})();
