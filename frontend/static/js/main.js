// main.js - loaded on every page. Theme toggle, mobile menu, and helpers shared by other scripts.
(function () {
  "use strict";

  // ---------- Dark / light theme ----------
  const root = document.documentElement;
  const themeButton = document.getElementById("theme-toggle");

  function updateThemeIcon() {
    const isDark = root.getAttribute("data-theme") === "dark";
    themeButton.querySelector("i").className = isDark ? "fa-solid fa-sun" : "fa-solid fa-moon";
  }

  themeButton.addEventListener("click", function () {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("cc-theme", next); } catch (e) { /* storage may be blocked */ }
    updateThemeIcon();
  });
  updateThemeIcon();

  // ---------- Mobile navigation ----------
  const navToggle = document.getElementById("nav-toggle");
  const navLinks = document.getElementById("nav-links");
  navToggle.addEventListener("click", function () {
    const open = navLinks.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(open));
  });

  // ---------- Shared helpers ----------

  // Small pop-up message. textContent (not innerHTML) keeps it safe from injected HTML.
  function showToast(message, type, duration) {
    const toast = document.createElement("div");
    toast.className = "toast toast-" + (type || "info");
    toast.setAttribute("role", "status");
    toast.textContent = message;
    document.getElementById("toast-container").appendChild(toast);
    setTimeout(function () { toast.remove(); }, duration || 3500);
  }

  // Calls our Flask API. Returns the "data" part of the JSON, or throws an Error with a
  // readable message (this is what the pages show to the user).
  async function apiRequest(url, options) {
    const opts = options || {};
    const controller = new AbortController();
    const timer = setTimeout(function () { controller.abort(); }, opts.timeoutMs || 20000);
    let response;
    try {
      response = await fetch(url, {
        method: opts.method || "GET",
        headers: opts.body ? { "Content-Type": "application/json" } : {},
        body: opts.body ? JSON.stringify(opts.body) : undefined,
        signal: controller.signal,
      });
    } catch (err) {
      if (err.name === "AbortError") throw new Error("The request took too long. Please try again.");
      throw new Error("Could not reach the server. Make sure the Flask app is running.");
    } finally {
      clearTimeout(timer);
    }

    let payload = null;
    try { payload = await response.json(); } catch (err) { /* response was not JSON */ }

    if (!response.ok || !payload || payload.success !== true) {
      const message = payload && payload.error && payload.error.message
        ? payload.error.message
        : "Request failed (HTTP " + response.status + ").";
      throw new Error(message);
    }
    return payload.data;
  }

  // Copies text to the clipboard. Resolves to true on success, false on failure.
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      // Fallback for browsers without the Clipboard API
      const helper = document.createElement("textarea");
      helper.value = text;
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.appendChild(helper);
      helper.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      helper.remove();
      return ok;
    }
  }

  function formatDate(isoString) {
    const date = new Date(isoString);
    if (isNaN(date)) return isoString;
    return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
  }

  // Make the helpers available to generate.js and history.js
  window.ContentCraft = { showToast: showToast, apiRequest: apiRequest, copyText: copyText, formatDate: formatDate };
})();