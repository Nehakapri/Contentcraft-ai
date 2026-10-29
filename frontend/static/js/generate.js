// generate.js - the content workspace: validate, call /api/generate, show/copy/save the result.
(function () {
  "use strict";

  const { apiRequest, showToast, copyText } = window.ContentCraft;

  // ----- Page elements -----
  const form = document.getElementById("generate-form");
  const userInput = document.getElementById("user-input");
  const charCount = document.getElementById("char-count");
  const toneSelect = document.getElementById("tone");
  const lengthSelect = document.getElementById("length");
  const extraInput = document.getElementById("extra-instructions");
  const formError = document.getElementById("form-error");
  const generateBtn = document.getElementById("generate-btn");
  const generateLabel = document.getElementById("generate-label");
  const outputEmpty = document.getElementById("output-empty");
  const outputText = document.getElementById("output-text");
  const outputActions = document.getElementById("output-actions");
  const copyBtn = document.getElementById("copy-btn");
  const saveBtn = document.getElementById("save-btn");
  const saveLabel = document.getElementById("save-label");
  const regenerateBtn = document.getElementById("regenerate-btn");
  const clearBtn = document.getElementById("clear-btn");

  const MAX_CHARS = Number(userInput.dataset.max);

  // ----- State -----
  let lastRequest = null;   // the data we last sent (used by Regenerate and Save)
  let lastResult = "";      // the text we last received
  let isSaved = false;

  // ----- Small helpers -----
  function selectedRadio() {
    return form.querySelector('input[name="content_type"]:checked');
  }

  function updatePlaceholder() {
    const radio = selectedRadio();
    if (radio) userInput.placeholder = radio.dataset.placeholder;
  }

  function updateCounter() {
    const length = userInput.value.length;
    charCount.textContent = length + " / " + MAX_CHARS;
    charCount.classList.toggle("over-limit", length > MAX_CHARS);
  }

  function showError(message) {
    formError.textContent = message;   // textContent: never interpret text as HTML
    formError.hidden = false;
  }

  function clearError() {
    formError.hidden = true;
    formError.textContent = "";
  }

  function readForm() {
    return {
      content_type: selectedRadio().value,
      user_input: userInput.value.trim(),
      tone: toneSelect.value,
      output_length: lengthSelect.value,
      extra_instructions: extraInput.value.trim(),
    };
  }

  // Browser-side validation (the server validates again).
  function validate(data) {
    if (!data.user_input) return "Please enter a topic, instructions or some text first.";
    if (data.user_input.length < 3) return "Your input is too short. Add a little more detail.";
    if (data.user_input.length > MAX_CHARS) return "Your input is too long. Please keep it under " + MAX_CHARS + " characters.";
    return "";
  }

  function setLoading(isLoading) {
    generateBtn.disabled = isLoading;
    regenerateBtn.disabled = isLoading;
    generateBtn.classList.toggle("loading", isLoading);
    generateLabel.textContent = isLoading ? "Generating\u2026" : "Generate";
  }

  function showResult(text) {
    outputEmpty.hidden = true;
    outputText.hidden = false;
    outputActions.hidden = false;
    outputText.textContent = text;       // safe: displayed as plain text, never as HTML
    saveBtn.disabled = false;
    saveLabel.textContent = "Save";
  }

  function resetOutput() {
    lastRequest = null;
    lastResult = "";
    isSaved = false;
    outputText.textContent = "";
    outputText.hidden = true;
    outputActions.hidden = true;
    outputEmpty.hidden = false;
  }

  // ----- Main action: send the request to Flask -----
  async function runGeneration(requestData) {
    clearError();
    setLoading(true);
    try {
      const data = await apiRequest("/api/generate", {
        method: "POST",
        body: requestData,
        timeoutMs: 70000,   // a little longer than the server's own AI timeout
      });
      lastRequest = requestData;
      lastResult = data.generated_content;
      isSaved = false;
      showResult(lastResult);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ----- Event listeners -----
  form.addEventListener("submit", function (event) {
    event.preventDefault();              // stop the browser from reloading the page
    const data = readForm();
    const problem = validate(data);
    if (problem) { showError(problem); return; }
    runGeneration(data);
  });

  userInput.addEventListener("input", updateCounter);
  userInput.addEventListener("keydown", function (event) {
    if (event.ctrlKey && event.key === "Enter") form.requestSubmit();
  });
  form.querySelectorAll('input[name="content_type"]').forEach(function (radio) {
    radio.addEventListener("change", updatePlaceholder);
  });

  copyBtn.addEventListener("click", async function () {
    const ok = await copyText(lastResult);
    showToast(ok ? "Copied to clipboard." : "Could not copy. Select the text and press Ctrl+C.", ok ? "success" : "error");
  });

  saveBtn.addEventListener("click", async function () {
    if (!lastResult || isSaved) return;
    saveBtn.disabled = true;
    try {
      await apiRequest("/api/history", {
        method: "POST",
        body: Object.assign({}, lastRequest, { generated_content: lastResult }),
      });
      isSaved = true;
      saveLabel.textContent = "Saved";
      showToast("Saved to your history.", "success");
    } catch (err) {
      saveBtn.disabled = false;
      showToast(err.message, "error", 5000);
    }
  });

  regenerateBtn.addEventListener("click", function () {
    if (lastRequest) runGeneration(lastRequest);
  });

  clearBtn.addEventListener("click", function () {
    resetOutput();
    userInput.value = "";
    extraInput.value = "";
    clearError();
    updateCounter();
    userInput.focus();
  });

  // ----- Start-up -----
  updatePlaceholder();
  updateCounter();
})();