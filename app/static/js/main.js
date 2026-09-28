// Remembers light or dark mode in this browser. Bootstrap reads data-bs-theme.
(function () {
  var storageKey = "queueless-theme";
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");
  var saved = localStorage.getItem(storageKey);
  var theme = saved || "light";

  function apply(next) {
    theme = next;
    root.setAttribute("data-bs-theme", theme);
    localStorage.setItem(storageKey, theme);
    if (toggle) {
      toggle.innerHTML = theme === "dark"
        ? '<i class="bi bi-sun"></i>'
        : '<i class="bi bi-moon-stars"></i>';
      toggle.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
      );
    }
  }

  apply(theme);
  if (toggle) {
    toggle.addEventListener("click", function () {
      apply(theme === "dark" ? "light" : "dark");
    });
  }
})();
