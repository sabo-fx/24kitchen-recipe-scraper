import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { JSDOM } from "jsdom";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const extractSrc = readFileSync(path.join(root, "extract.js"), "utf8");

function loadFixture(name, url = "https://www.24kitchen.nl/recepten/test-recept") {
  const html = readFileSync(path.join(here, "fixtures", name), "utf8");
  const dom = new JSDOM(html, { url, runScripts: "dangerously" });
  const script = dom.window.document.createElement("script");
  script.textContent = extractSrc;
  dom.window.document.head.appendChild(script);
  return dom;
}

// Clone extracted data into Node's realm so deepStrictEqual doesn't trip over
// jsdom-realm Array/Object prototypes (same structure, different identity).
function collect(window) {
  return JSON.parse(
    JSON.stringify(window.K24.collectRecipe(window.document, window.location.href)),
  );
}

test("extract.js exposes K24 with the expected API", () => {
  const { window } = loadFixture("recipe.html");
  assert.ok(window.K24, "K24 namespace should exist on window");
  for (const fn of ["collectRecipe", "findRecipeJsonLd", "slugFromUrl", "normalize"]) {
    assert.equal(typeof window.K24[fn], "function", `K24.${fn} should be a function`);
  }
});

test("collectRecipe extracts every field from a full recipe page", () => {
  const { window } = loadFixture("recipe.html");
  const data = collect(window);

  assert.equal(data.title, "Test recept");
  assert.equal(data.slug, "test-recept");
  assert.equal(data.sourceUrl, "https://www.24kitchen.nl/recepten/test-recept");
  assert.equal(data.summary, "Dit is een korte beschrijving van het recept.");
  assert.equal(data.yieldText, "4 porties");
  assert.equal(data.prepTime, "20 min");
  assert.equal(data.cookTime, "40 min");
  assert.equal(data.waitTime, "10 min");
  assert.equal(data.published, "12 mei 2024");
  assert.equal(data.heroUrl, "https://example.com/hero.jpg");

  assert.equal(data.sections.length, 2);
  assert.equal(data.sections[0].title, "Hoofdgerecht");
  assert.deepEqual(data.sections[0].items, ["2 uien", "300 g rundvlees"]);
  assert.equal(data.sections[1].title, "Saus");
  assert.deepEqual(data.sections[1].items, ["200 ml rode wijn"]);

  assert.deepEqual(data.equipment, ["Braadpan", "Houten lepel"]);

  assert.equal(data.preparationSections.length, 2);
  assert.equal(data.preparationSections[0].title, "Bereiding hoofdgerecht");
  assert.deepEqual(data.preparationSections[0].steps, [
    "Snijd de uien fijn.",
    "Bak het vlees rondom bruin.",
  ]);
  assert.deepEqual(data.preparationSections[1].steps, ["Blus af met rode wijn."]);

  assert.deepEqual(data.program, {
    name: "De Brigade",
    url: "https://www.24kitchen.nl/programmas/de-brigade",
  });
});

test("collectRecipe surfaces the source URL passed in by the caller", () => {
  const { window } = loadFixture(
    "recipe.html",
    "https://www.24kitchen.nl/recepten/some-other-slug",
  );
  const data = collect(window);
  assert.equal(data.sourceUrl, "https://www.24kitchen.nl/recepten/some-other-slug");
  assert.equal(data.slug, "some-other-slug");
});

test("collectRecipe returns null program when the page has no programma block", () => {
  const { window } = loadFixture(
    "recipe-no-prep.html",
    "https://www.24kitchen.nl/recepten/fallback-recept",
  );
  const data = collect(window);
  assert.equal(data.program, null);
});

test("collectRecipe falls back to JSON-LD when no HTML prep sections exist", () => {
  const { window } = loadFixture(
    "recipe-no-prep.html",
    "https://www.24kitchen.nl/recepten/fallback-recept",
  );
  const data = collect(window);

  assert.equal(data.title, "Fallback recept");
  assert.equal(data.slug, "fallback-recept");
  assert.equal(data.summary, "Alleen JSON-LD beschikbaar.");
  assert.equal(data.heroUrl, "https://example.com/fallback-hero.jpg");
  assert.deepEqual(data.sections, []);
  assert.deepEqual(data.equipment, []);
  assert.equal(data.preparationSections.length, 1);
  assert.equal(data.preparationSections[0].title, "Bereiding");
  assert.deepEqual(data.preparationSections[0].steps, [
    "Stap een tekst.",
    "Stap twee tekst.",
  ]);
});

test("findRecipeJsonLd returns null for non-recipe pages", () => {
  const dom = new JSDOM(
    '<html><body><script type="application/ld+json">{"@type":"WebPage","name":"x"}</script></body></html>',
    { url: "https://www.24kitchen.nl/recepten/none", runScripts: "dangerously" },
  );
  const script = dom.window.document.createElement("script");
  script.textContent = extractSrc;
  dom.window.document.head.appendChild(script);

  assert.equal(dom.window.K24.findRecipeJsonLd(dom.window.document), null);
  assert.equal(
    dom.window.K24.collectRecipe(dom.window.document, dom.window.location.href),
    null,
  );
});

test("slugFromUrl handles trailing slashes and missing segments", () => {
  const { window } = loadFixture("recipe.html");
  assert.equal(window.K24.slugFromUrl("https://www.24kitchen.nl/recepten/foo-bar"), "foo-bar");
  assert.equal(window.K24.slugFromUrl("https://www.24kitchen.nl/recepten/foo-bar/"), "foo-bar");
  assert.equal(window.K24.slugFromUrl("https://www.24kitchen.nl/"), "recept");
  assert.equal(window.K24.slugFromUrl("not a url"), "recept");
});

test("normalize collapses whitespace and trims", () => {
  const { window } = loadFixture("recipe.html");
  assert.equal(window.K24.normalize("  hello\n   world\t!  "), "hello world !");
  assert.equal(window.K24.normalize(""), "");
  assert.equal(window.K24.normalize(null), "");
});
