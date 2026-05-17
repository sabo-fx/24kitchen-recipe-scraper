// Pure DOM-extraction helpers for 24Kitchen recipe pages.
// Loaded as a content script (before content.js) and reused by the smoke test
// in tests/ so the parsing logic can be validated without launching Edge.
(function (global) {
  const normalize = (value) => (value || "").replace(/\s+/g, " ").trim();

  function findRecipeJsonLd(doc) {
    const scripts = doc.querySelectorAll('script[type="application/ld+json"]');
    for (const script of scripts) {
      const raw = script.textContent;
      if (!raw || !raw.includes('"Recipe"')) continue;
      let data;
      try { data = JSON.parse(raw); } catch { continue; }
      const candidates = Array.isArray(data)
        ? data
        : Array.isArray(data["@graph"])
          ? data["@graph"]
          : [data];
      const recipe = candidates.find((item) => item && item["@type"] === "Recipe");
      if (recipe) return recipe;
    }
    return null;
  }

  function extractSummary(doc, recipe) {
    const el = doc.querySelector(".field--name-field-summary");
    const text = el ? normalize(el.textContent) : "";
    return text || normalize((recipe && recipe.description) || "");
  }

  function extractMetaTimes(doc) {
    const nodes = doc.querySelectorAll(".meta--recipe-time .text");
    return Array.from(nodes).slice(0, 3).map((n) => normalize(n.textContent));
  }

  function extractPublished(doc) {
    const el = doc.querySelector(".node-meta__created time");
    return el ? normalize(el.textContent) : "";
  }

  function extractIngredientSections(doc) {
    const sections = [];
    doc.querySelectorAll("h3.ingredient-list-title.heading-xs").forEach((h3) => {
      const ul = h3.nextElementSibling;
      if (!ul || !ul.matches("ul.list-recipe-ingredients")) return;
      const items = Array.from(ul.querySelectorAll("label"))
        .map((l) => normalize(l.textContent))
        .filter(Boolean);
      if (items.length) sections.push({ title: normalize(h3.textContent), items });
    });
    return sections;
  }

  function extractEquipment(doc) {
    const h2 = doc.querySelector("h2#ingredients");
    if (!h2 || !/Benodigdheden/i.test(h2.textContent)) return [];
    const ul = h2.nextElementSibling;
    if (!ul || !ul.matches("ul.content-list.list--col1")) return [];
    return Array.from(ul.querySelectorAll(".field--name-field-plain-text-short"))
      .map((d) => normalize(d.textContent))
      .filter(Boolean);
  }

  function extractPreparationSections(doc, recipe) {
    const sections = [];
    doc.querySelectorAll("h3.ingredient-list-title.heading-s").forEach((h3) => {
      const ol = h3.nextElementSibling;
      if (!ol || !ol.matches("ol.list--prepration-steps")) return;
      const steps = Array.from(ol.querySelectorAll(".field--name-field-text"))
        .map((d) => normalize(d.textContent))
        .filter(Boolean);
      if (steps.length) sections.push({ title: normalize(h3.textContent), steps });
    });
    if (sections.length === 0 && recipe && Array.isArray(recipe.recipeInstructions)) {
      const steps = recipe.recipeInstructions
        .map((s) => normalize(typeof s === "string" ? s : s && s.text))
        .filter(Boolean);
      if (steps.length) sections.push({ title: "Bereiding", steps });
    }
    return sections;
  }

  function extractProgram(doc) {
    const container = doc.querySelector(".field--name-field-program");
    if (!container) return null;
    const anchor = container.querySelector("a.full-click-link[href]");
    if (!anchor) return null;
    const titleEl =
      anchor.querySelector(".field--name-title") ||
      anchor.querySelector(".program__text") ||
      anchor;
    const name = normalize(titleEl.textContent);
    if (!name) return null;
    const href = anchor.getAttribute("href") || "";
    let url = href;
    if (href.startsWith("/")) url = `https://www.24kitchen.nl${href}`;
    return { name, url };
  }

  function extractHeroUrl(recipe) {
    const img = recipe && recipe.image;
    if (!img) return "";
    if (typeof img === "string") return img;
    if (Array.isArray(img)) return (img[0] && (img[0].url || img[0])) || "";
    return img.url || "";
  }

  function slugFromUrl(href) {
    try {
      const parts = new URL(href).pathname.split("/").filter(Boolean);
      return parts[parts.length - 1] || "recept";
    } catch {
      return "recept";
    }
  }

  function collectRecipe(doc, sourceUrl) {
    const recipe = findRecipeJsonLd(doc);
    if (!recipe) return null;
    const meta = extractMetaTimes(doc);
    return {
      sourceUrl,
      slug: slugFromUrl(sourceUrl),
      title: normalize(recipe.name || doc.title),
      summary: extractSummary(doc, recipe),
      yieldText: normalize(recipe.recipeYield || ""),
      prepTime: meta[0] || "",
      cookTime: meta[1] || "",
      waitTime: meta[2] || "",
      published: extractPublished(doc),
      heroUrl: extractHeroUrl(recipe),
      sections: extractIngredientSections(doc),
      equipment: extractEquipment(doc),
      preparationSections: extractPreparationSections(doc, recipe),
      program: extractProgram(doc),
    };
  }

  global.K24 = {
    normalize,
    findRecipeJsonLd,
    extractSummary,
    extractMetaTimes,
    extractPublished,
    extractIngredientSections,
    extractEquipment,
    extractPreparationSections,
    extractProgram,
    extractHeroUrl,
    slugFromUrl,
    collectRecipe,
  };
})(typeof window !== "undefined" ? window : globalThis);
