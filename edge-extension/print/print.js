(async () => {
  const key = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  if (!key) {
    showError("Geen recept-id in de URL gevonden.");
    return;
  }

  let stored;
  try {
    stored = await chrome.storage.local.get(key);
  } catch (err) {
    showError("Kon recept-data niet uit de opslag laden.");
    console.error(err);
    return;
  }

  const data = stored[key];
  if (!data) {
    showError("Recept-data niet gevonden in de extensie-opslag.");
    return;
  }

  // Clean up the stored payload once we have it in memory.
  chrome.storage.local.remove(key).catch(() => {});

  populate(data);
  setupPrintButton();
  await whenImagesSettled();
  // Give layout one tick so the browser computes pagination before opening the dialog.
  setTimeout(() => window.print(), 250);
})();

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value || "";
}

function showError(message) {
  document.body.innerHTML = `<p style="padding:24px;font:14px/1.5 system-ui;color:#b3261e">${escapeHtml(message)}</p>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function populate(data) {
  document.title = `24kitchen-${data.slug || "recept"}`;

  setText("title", data.title);
  setText("summary", data.summary);
  setText("meta-yield", data.yieldText);
  setText("meta-prep", data.prepTime);
  setText("meta-cook", data.cookTime);
  setText("meta-wait", data.waitTime);

  const hero = document.getElementById("hero");
  if (data.heroUrl) {
    hero.src = data.heroUrl;
    hero.alt = data.title || "";
  } else {
    hero.remove();
  }

  const published = document.getElementById("published");
  if (data.published) {
    published.textContent = `Gepubliceerd op: ${data.published}`;
  } else {
    published.remove();
  }

  const program = document.getElementById("program");
  if (data.program && data.program.name) {
    const link = document.getElementById("program-link");
    link.textContent = data.program.name;
    link.href = data.program.url || "#";
    program.hidden = false;
  } else {
    program.remove();
  }

  const sourceFooter = document.getElementById("source-footer");
  if (data.sourceUrl) {
    const link = document.getElementById("source-link");
    link.textContent = data.sourceUrl;
    link.href = data.sourceUrl;
    sourceFooter.hidden = false;
  } else {
    sourceFooter.remove();
  }

  const logo = document.getElementById("logo");
  if (logo) logo.addEventListener("error", () => logo.setAttribute("data-broken", "true"));

  renderIngredients(data.sections || []);
  renderEquipment(data.equipment || [], data.title || "");
  renderPreparation(data.preparationSections || []);
}

function renderIngredients(sections) {
  const wrap = document.getElementById("ingredient-cards");
  const section = document.getElementById("ingredients-section");
  if (!sections.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  wrap.innerHTML = "";
  for (const s of sections) {
    const card = document.createElement("div");
    card.className = "card ingredient";
    const title = document.createElement("h3");
    title.textContent = s.title || "";
    const list = document.createElement("ul");
    for (const item of s.items) {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    }
    card.appendChild(title);
    card.appendChild(list);
    wrap.appendChild(card);
  }
}

function renderEquipment(items, recipeTitle) {
  const wrap = document.getElementById("equipment-card");
  const section = document.getElementById("equipment-section");
  if (!items.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  wrap.innerHTML = "";
  const card = document.createElement("div");
  card.className = "card equipment";
  const title = document.createElement("h3");
  title.textContent = `Benodigdheden voor ${recipeTitle.toLowerCase()}`;
  const list = document.createElement("ul");
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  }
  card.appendChild(title);
  card.appendChild(list);
  wrap.appendChild(card);
}

function renderPreparation(sections) {
  const wrap = document.getElementById("prep-blocks");
  const section = document.getElementById("prep-section");
  if (!sections.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  wrap.innerHTML = "";
  for (const s of sections) {
    const block = document.createElement("div");
    block.className = "prep-block";
    const title = document.createElement("h3");
    title.textContent = s.title || "";
    const list = document.createElement("ol");
    for (const step of s.steps) {
      const li = document.createElement("li");
      li.textContent = step;
      list.appendChild(li);
    }
    block.appendChild(title);
    block.appendChild(list);
    wrap.appendChild(block);
  }
}

function setupPrintButton() {
  const button = document.getElementById("print-btn");
  if (button) button.addEventListener("click", () => window.print());
}

function whenImagesSettled() {
  const images = Array.from(document.images);
  if (!images.length) return Promise.resolve();
  return Promise.all(
    images.map((img) =>
      img.complete
        ? Promise.resolve()
        : new Promise((resolve) => {
            img.addEventListener("load", resolve, { once: true });
            img.addEventListener("error", resolve, { once: true });
          })
    )
  );
}
