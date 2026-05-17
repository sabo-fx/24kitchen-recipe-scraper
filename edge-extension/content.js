(() => {
  if (window.__k24PdfInjected) return;
  window.__k24PdfInjected = true;

  function injectButton() {
    if (document.getElementById("k24-pdf-button")) return;
    const button = document.createElement("button");
    button.id = "k24-pdf-button";
    button.type = "button";
    button.innerHTML = '<span class="k24-icon">\u2B07</span><span>Download als PDF</span>';
    button.addEventListener("click", onDownloadClick);
    document.body.appendChild(button);
  }

  async function onDownloadClick(event) {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const data = K24.collectRecipe(document, location.href);
      if (!data) {
        alert("Geen recept-gegevens gevonden op deze pagina.");
        return;
      }
      const key = `k24-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      await chrome.storage.local.set({ [key]: data });
      await chrome.runtime.sendMessage({ type: "open-print", key });
    } catch (err) {
      console.error("[24Kitchen PDF] failed:", err);
      alert("Kon de PDF-weergave niet openen. Zie de console voor details.");
    } finally {
      button.disabled = false;
    }
  }

  if (K24.findRecipeJsonLd(document)) injectButton();
})();
