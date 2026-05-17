from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(page_count)
            super().showPage()
        super().save()

    def _draw_page_number(self, page_count: int) -> None:
        page_width, _ = self._pagesize
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#23322d"))
        self.drawRightString(
            page_width - 18 * mm,
            10 * mm,
            f"Page {self._pageNumber} of {page_count}",
        )


@dataclass
class IngredientSection:
    title: str
    items: List[str]


@dataclass
class PreparationSection:
    title: str
    steps: List[str]


@dataclass
class RecipeData:
    title: str
    summary: str
    yield_text: str
    prep_time: str
    cook_time: str
    wait_time: str
    published: str
    hero_url: str
    sections: List[IngredientSection]
    equipment: List[str]
    preparation_sections: List[PreparationSection]
    program_name: str = ""
    program_url: str = ""
    source_url: str = ""


SITE_BASE_URL = "https://www.24kitchen.nl"


def resolve_site_url(href: str) -> str:
    if href.startswith("/"):
        return f"{SITE_BASE_URL}{href}"
    return href


def clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_recipe(html_path: Path) -> RecipeData:
    html_text = html_path.read_text(encoding="utf-8")

    ld_json = None
    for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.DOTALL):
        content = match.group(1)
        if '"@type": "Recipe"' in content:
            ld_json = json.loads(content)
            break
    if not ld_json:
        raise RuntimeError("Recipe JSON-LD not found in HTML source.")

    recipe = next(item for item in ld_json["@graph"] if item.get("@type") == "Recipe")

    summary_match = re.search(
        r'<div class="clearfix text-formatted field field--name-field-summary field--type-text-long field--label-hidden field__item">(.*?)</div>',
        html_text,
        re.DOTALL,
    )
    summary = clean_text(summary_match.group(1)) if summary_match else recipe["description"]

    def find_meta_text(index: int) -> str:
        items = re.findall(
            r'<div class="meta--recipe-time text-xs">.*?<span class="text">\s*(.*?)\s*</span>',
            html_text,
            re.DOTALL,
        )
        return clean_text(items[index]) if len(items) > index else ""

    published_match = re.search(
        r'<p class="node-meta__item node-meta__created">.*?<time[^>]*>\s*(.*?)\s*</time>',
        html_text,
        re.DOTALL,
    )
    published = clean_text(published_match.group(1)) if published_match else ""

    sections: List[IngredientSection] = []
    section_matches = re.finditer(
        r'<h3 class="ingredient-list-title heading-xs">(.*?)</h3>\s*<ul class="stripped list-recipe-ingredients">(.*?)</ul>',
        html_text,
        re.DOTALL,
    )
    for match in section_matches:
        title = clean_text(match.group(1))
        block = match.group(2)
        items = [clean_text(label) for label in re.findall(r"<label[^>]*>(.*?)</label>", block, re.DOTALL)]
        if items:
            sections.append(IngredientSection(title=title, items=items))

    equipment: List[str] = []
    equipment_match = re.search(
        r'<h2 id="ingredients"\s*class="section-title heading-s">Benodigdheden.*?</h2>\s*<ul class="content-list list--col1">(.*?)</ul>',
        html_text,
        re.DOTALL,
    )
    if equipment_match:
        equipment = [
            clean_text(item)
            for item in re.findall(
                r'<div class="field field--name-field-plain-text-short field--type-string field--label-hidden field__item">(.*?)</div>',
                equipment_match.group(1),
                re.DOTALL,
            )
        ]

    preparation_sections: List[PreparationSection] = []
    preparation_matches = re.finditer(
        r'<h3 class="ingredient-list-title heading-s">\s*(.*?)\s*</h3>\s*<ol class="field field--name-field-preparation-steps field--type-entity-reference-revisions field--label-hidden list--prepration-steps">(.*?)</ol>',
        html_text,
        re.DOTALL,
    )
    for match in preparation_matches:
        title = clean_text(match.group(1))
        block = match.group(2)
        steps = [
            clean_text(step)
            for step in re.findall(
                r'<div class="clearfix text-formatted field field--name-field-text field--type-text-long field--label-hidden field__item">(.*?)</div>',
                block,
                re.DOTALL,
            )
        ]
        if steps:
            preparation_sections.append(PreparationSection(title=title, steps=steps))

    if not preparation_sections:
        preparation_sections.append(
            PreparationSection(
                title="Bereiding",
                steps=[clean_text(step["text"]) for step in recipe["recipeInstructions"]],
            )
        )

    program_name = ""
    program_url = ""
    program_match = re.search(
        r'<div class="field field--name-field-program[^"]*">.*?'
        r'<a class="full-click-link" href="([^"]+)">.*?'
        r'<span class="field field--name-title[^"]*">(.*?)</span>',
        html_text,
        re.DOTALL,
    )
    if program_match:
        program_url = resolve_site_url(program_match.group(1))
        program_name = clean_text(program_match.group(2))

    return RecipeData(
        title=clean_text(recipe["name"]),
        summary=summary,
        yield_text=clean_text(recipe.get("recipeYield", "")),
        prep_time=find_meta_text(0),
        cook_time=find_meta_text(1),
        wait_time=find_meta_text(2),
        published=published,
        hero_url=recipe["image"]["url"],
        sections=sections,
        equipment=equipment,
        preparation_sections=preparation_sections,
        program_name=program_name,
        program_url=program_url,
    )


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="RecipeTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#134c3d"),
            spaceAfter=8,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="RecipeIntro",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11.5,
            leading=16,
            textColor=colors.HexColor("#30433b"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#134c3d"),
            spaceAfter=6,
            spaceBefore=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CardTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#134c3d"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallMeta",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#ffffff"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#23322d"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="StepText",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#23322d"),
            leftIndent=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PrepSectionTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            textColor=colors.HexColor("#e05a2a"),
            spaceBefore=6,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ProgramLine",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#23322d"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SourceFooter",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#23322d"),
        )
    )
    return styles


def meta_table(recipe: RecipeData, styles) -> Table:
    cells = [
        Paragraph("<b>Porties</b><br/>" + recipe.yield_text, styles["SmallMeta"]),
        Paragraph("<b>Voorbereiden</b><br/>" + recipe.prep_time, styles["SmallMeta"]),
        Paragraph("<b>Oventijd</b><br/>" + recipe.cook_time, styles["SmallMeta"]),
        Paragraph("<b>Wachttijd</b><br/>" + recipe.wait_time, styles["SmallMeta"]),
    ]
    table = Table([cells], colWidths=[40 * mm, 42 * mm, 38 * mm, 38 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e05a2a")),
                ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#e05a2a")),
                ("INNERGRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#f9d9c8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def ingredient_card(section: IngredientSection, styles, width_mm: float) -> Table:
    item_paragraphs = [Paragraph(f"• {item}", styles["BodySmall"]) for item in section.items]
    content = [Paragraph(section.title, styles["CardTitle"])] + item_paragraphs
    table = Table([[content]], colWidths=[width_mm * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8f2")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#efc4b0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def bullet_card(title: str, items: List[str], styles, width_mm: float) -> Table:
    content = [Paragraph(title, styles["CardTitle"])] + [Paragraph(f"• {item}", styles["BodySmall"]) for item in items]
    table = Table([[content]], colWidths=[width_mm * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f8f6")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#c8ddd5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def build_pdf(recipe: RecipeData, hero_path: Path, logo_path: Path, output_path: Path) -> None:
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=recipe.title,
        author="OpenAI Codex",
    )

    story = []

    if logo_path.exists():
        logo = Image(str(logo_path), width=18 * mm, height=20 * mm)
        story.append(logo)
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("24Kitchen receptkopie", styles["BodySmall"]))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph(recipe.title, styles["RecipeTitle"]))
    story.append(Paragraph(recipe.summary, styles["RecipeIntro"]))
    story.append(meta_table(recipe, styles))
    story.append(Spacer(1, 6 * mm))

    if hero_path.exists():
        hero = Image(str(hero_path), width=174 * mm, height=116 * mm)
        story.append(hero)
        story.append(Spacer(1, 5 * mm))

    if recipe.published:
        story.append(Paragraph(f"Gepubliceerd op: {recipe.published}", styles["BodySmall"]))
        story.append(Spacer(1, 2 * mm))

    if recipe.program_name:
        program_text = (
            '<b><font color="#134c3d">Dit recept komt voor in het programma:</font></b> '
            f'<a href="{recipe.program_url}" color="#e05a2a"><b>{recipe.program_name}</b></a>'
        )
        story.append(Paragraph(program_text, styles["ProgramLine"]))
        story.append(Spacer(1, 5 * mm))
    elif recipe.published:
        story.append(Spacer(1, 3 * mm))

    cards = [ingredient_card(section, styles, 84) for section in recipe.sections]
    if cards:
        story.append(
            KeepTogether(
                [
                    Paragraph("Ingrediënten", styles["SectionTitle"]),
                    Spacer(1, 1 * mm),
                    cards[0],
                    Spacer(1, 3 * mm),
                ]
            )
        )
        for card in cards[1:]:
            story.append(KeepTogether([card, Spacer(1, 3 * mm)]))
    else:
        story.append(Paragraph("Ingrediënten", styles["SectionTitle"]))
        story.append(Spacer(1, 1 * mm))

    if recipe.equipment:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Benodigdheden", styles["SectionTitle"]))
        story.append(Spacer(1, 1 * mm))
        story.append(bullet_card(f"Benodigdheden voor {recipe.title.lower()}", recipe.equipment, styles, 174))

    preparation_flowables = [
        Spacer(1, 3 * mm),
        Paragraph("Bereiding", styles["SectionTitle"]),
    ]

    for section in recipe.preparation_sections:
        preparation_flowables.append(Paragraph(section.title, styles["PrepSectionTitle"]))
        list_items = [
            ListItem(Paragraph(step, styles["StepText"]), leftIndent=0, value=index + 1)
            for index, step in enumerate(section.steps)
        ]
        preparation_flowables.append(
            ListFlowable(
                list_items,
                bulletType="1",
                start="1",
                leftIndent=20,
                bulletFontName="Helvetica-Bold",
                bulletFontSize=10.5,
                bulletColor=colors.HexColor("#e05a2a"),
            )
        )
        preparation_flowables.append(Spacer(1, 2 * mm))

    story.append(KeepTogether(preparation_flowables))

    if recipe.source_url:
        story.append(Spacer(1, 6 * mm))
        source_text = (
            f'Bron: <a href="{recipe.source_url}" color="#134c3d">{recipe.source_url}</a>'
        )
        story.append(Paragraph(source_text, styles["SourceFooter"]))

    doc.build(story, canvasmaker=NumberedCanvas)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True)
    parser.add_argument("--hero", required=True)
    parser.add_argument("--logo", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-url", default="")
    args = parser.parse_args()

    recipe = load_recipe(Path(args.html))
    if args.source_url:
        recipe.source_url = args.source_url
    build_pdf(recipe, Path(args.hero), Path(args.logo), Path(args.output))


if __name__ == "__main__":
    main()
