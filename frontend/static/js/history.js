// history.js - lists saved items from /api/history, opens one in a dialog, deletes with confirmation.
(function () {
  "use strict";

  const { apiRequest, showToast, copyText, formatDate } = window.ContentCraft;

  const listEl = document.getElementById("history-list");
  const loadingEl = document.getElementById("history-loading");
  const errorEl = document.getElementById("history-error");
  const emptyEl = document.getElementById("history-empty");
  const dialog = document.getElementById("item-dialog");
  const dialogTitle = document.getElementById("dialog-title");
  const dialogMeta = document.getElementById("dialog-meta");
  const dialogInput = document.getElementById("dialog-input");
  const dialogOutput = document.getElementById("dialog-output");
  const typeLabels = JSON.parse(document.getElementById("type-labels").textContent);

  let openItemId = null;

  // Small helper to build an element with text. textContent keeps user text from being run as HTML.
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function labelFor(type) {
    return typeLabels[type] || type;
  }

  function buildCard(item) {
    const card = el("article", "history-card");
    card.id = "item-" + item.id;

    const meta = el("div", "history-meta");
    meta.appendChild(el("span", "badge", labelFor(item.content_type)));
    meta.appendChild(el("span", "", formatDate(item.created_at)));

    const preview = item.preview + (item.content_length > item.preview.length ? "\u2026" : "");

    const actions = el("div", "history-actions");
    const viewBtn = el("button", "btn btn-ghost", "View");
    viewBtn.type = "button";
    viewBtn.addEventListener("click", function () { openItem(item.id); });
    const deleteBtn = el("button", "btn btn-danger", "Delete");
    deleteBtn.type = "button";
    deleteBtn.addEventListener("click", function () { deleteItem(item.id); });
    actions.append(viewBtn, deleteBtn);

    card.append(meta, el("h3", "", item.title), el("p", "history-preview", preview), actions);
    return card;
  }

  function updateEmptyState() {
    emptyEl.hidden = listEl.children.length > 0;
  }

  async function loadHistory() {
    try {
      const data = await apiRequest("/api/history?limit=100");
      listEl.replaceChildren();
      data.items.forEach(function (item) { listEl.appendChild(buildCard(item)); });
      updateEmptyState();
      openFromHash();
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    } finally {
      loadingEl.hidden = true;
    }
  }

  async function openItem(id) {
    try {
      const item = await apiRequest("/api/history/" + id);
      openItemId = item.id;
      dialogTitle.textContent = item.title;
      dialogMeta.textContent = labelFor(item.content_type) + " \u00b7 " + item.tone + " \u00b7 " +
        item.output_length + " \u00b7 " + formatDate(item.created_at);
      dialogInput.textContent = item.user_input;
      dialogOutput.textContent = item.generated_content;
      if (!dialog.open) dialog.showModal();
    } catch (err) {
      showToast(err.message, "error", 5000);
    }
  }

  async function deleteItem(id) {
    if (!window.confirm("Delete this saved item? This cannot be undone.")) return;
    try {
      await apiRequest("/api/history/" + id, { method: "DELETE" });
      const card = document.getElementById("item-" + id);
      if (card) card.remove();
      if (openItemId === id && dialog.open) dialog.close();
      updateEmptyState();
      showToast("Item deleted.", "success");
    } catch (err) {
      showToast(err.message, "error", 5000);
    }
  }

  // Links like /history#item-5 (from the dashboard) open that item directly.
  function openFromHash() {
    const match = /^#item-(\d+)$/.exec(window.location.hash);
    if (match) openItem(Number(match[1]));
  }

  document.getElementById("dialog-close").addEventListener("click", function () { dialog.close(); });
  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) dialog.close();   // click on the dark backdrop closes it
  });
  document.getElementById("dialog-copy").addEventListener("click", async function () {
    const ok = await copyText(dialogOutput.textContent);
    showToast(ok ? "Copied to clipboard." : "Could not copy.", ok ? "success" : "error");
  });
  document.getElementById("dialog-delete").addEventListener("click", function () {
    if (openItemId !== null) deleteItem(openItemId);
  });

  loadHistory();
})();