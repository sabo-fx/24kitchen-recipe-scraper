from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from render_recipe_pdf import build_pdf, load_recipe


DEFAULT_LOGO_URL = "https://www.24kitchen.nl/themes/kitchen/24k-logo.png"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-")


def read_url_list(path: Path) -> list[str]:
    urls: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def download_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read()


def ensure_download(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(download_bytes(url))
    return path


def remove_file_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def remove_dir_if_empty(path: Path) -> None:
    if path.exists() and path.is_dir():
        try:
            next(path.iterdir())
        except StopIteration:
            path.rmdir()


def extension_from_url(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    return suffix if suffix else fallback


def build_paths(url: str, output_dir: Path, assets_dir: Path) -> tuple[str, Path, Path]:
    parsed = urlparse(url)
    slug = slugify(parsed.path.rstrip("/").split("/")[-1] or parsed.netloc or "recipe")
    base_name = f"24kitchen-{slug}"
    html_path = output_dir / f"{base_name}-source.html"
    pdf_path = output_dir / f"{base_name}.pdf"
    return base_name, html_path, pdf_path


def process_url(url: str, output_dir: Path, assets_dir: Path, logo_path: Path, keep_temp: bool) -> Path:
    base_name, html_path, pdf_path = build_paths(url, output_dir, assets_dir)
    hero_path: Path | None = None
    try:
        html_path.write_bytes(download_bytes(url))
        recipe = load_recipe(html_path)
        recipe.source_url = url
        hero_ext = extension_from_url(recipe.hero_url, ".jpg")
        hero_path = assets_dir / f"{base_name}-hero{hero_ext}"
        ensure_download(recipe.hero_url, hero_path)
        build_pdf(recipe, hero_path, logo_path, pdf_path)
        return pdf_path
    finally:
        if not keep_temp:
            remove_file_if_exists(html_path)
            if hero_path is not None:
                remove_file_if_exists(hero_path)


def iter_results(urls: Iterable[str], output_dir: Path, assets_dir: Path, logo_path: Path, keep_temp: bool) -> int:
    failures = 0
    for url in urls:
        print(f"Processing {url}")
        try:
            pdf_path = process_url(url, output_dir, assets_dir, logo_path, keep_temp)
            print(f"Created {pdf_path}")
        except Exception as exc:  # pragma: no cover - defensive batch reporting
            failures += 1
            print(f"FAILED {url}: {exc}", file=sys.stderr)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url-list", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--logo-path", required=True)
    parser.add_argument("--logo-url", default=DEFAULT_LOGO_URL)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    url_list_path = Path(args.url_list)
    output_dir = Path(args.output_dir)
    assets_dir = Path(args.assets_dir)
    logo_path = Path(args.logo_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    if not logo_path.exists():
        ensure_download(args.logo_url, logo_path)

    urls = read_url_list(url_list_path)
    if not urls:
        print(f"No URLs found in {url_list_path}", file=sys.stderr)
        return 1

    failures = iter_results(urls, output_dir, assets_dir, logo_path, args.keep_temp)
    if not args.keep_temp:
        remove_file_if_exists(logo_path)
        remove_dir_if_empty(assets_dir)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
