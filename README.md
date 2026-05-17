# 24kitchen Recipe Scraper

Download recipes from [24kitchen.nl](https://www.24kitchen.nl/) and render them
as nicely formatted A4 PDFs.

The scraper reads the recipe's embedded JSON-LD plus a few HTML fragments
(summary, ingredient sections, equipment, preparation steps) and lays everything
out with [ReportLab](https://www.reportlab.com/): hero image, orange meta bar
(porties / voorbereiden / oventijd / wachttijd), boxed ingredient cards and
numbered preparation steps per section.

## Requirements

- **Windows** with **PowerShell 5.1+** (the wrapper script is `.ps1`).
- **Python 3.12+** with the following packages available on `sys.path`:
  - `reportlab`
  - `beautifulsoup4` (transitive: `soupsieve`)
  - `pillow`
  - `charset-normalizer`
  - `typing_extensions`

  Install with `pip`:

  ```powershell
  pip install reportlab beautifulsoup4 pillow charset-normalizer typing_extensions
  ```

  Alternatively you can vendor the dependencies into `data/pydeps/` (that path
  is gitignored) and point Python at it, e.g. by setting `PYTHONPATH`.

## Usage

1. Put one recipe URL per line in `recipe-urls.txt` (lines starting with `#`
   and blank lines are ignored). An example file is included.
2. Run the wrapper script from the repository root:

   ```powershell
   .\build-recipe-pdfs.ps1
   ```

   PDFs are written to `.\reports\` as `24kitchen-<slug>.pdf`.

### Parameters

`build-recipe-pdfs.ps1` accepts:

| Parameter          | Default                                  | Description                                  |
| ------------------ | ---------------------------------------- | -------------------------------------------- |
| `-UrlListPath`     | `.\recipe-urls.txt`                      | Text file with one recipe URL per line.      |
| `-OutputDirectory` | `.\reports`                              | Where generated PDFs are written.            |
| `-AssetsDirectory` | `<OutputDirectory>\24kitchen-assets`     | Scratch directory for downloaded images.     |
| `-PythonPath`      | auto-detected (`python` on `PATH`)       | Explicit Python executable to use.           |
| `-KeepTemp`        | off                                      | Keep downloaded HTML, hero images and logo.  |

By default the script cleans up the per-recipe HTML source, hero image and the
24Kitchen logo after each PDF is built; pass `-KeepTemp` to retain them for
debugging.

### Calling the Python directly

The PowerShell wrapper just orchestrates the Python batch. You can call it
yourself:

```powershell
python .\data\build_recipe_pdfs.py `
  --url-list .\recipe-urls.txt `
  --output-dir .\reports `
  --assets-dir .\reports\24kitchen-assets `
  --logo-path .\reports\24kitchen-assets\logo.png
```

To render a single recipe from an already-downloaded HTML file, use
`data\render_recipe_pdf.py` directly:

```powershell
python .\data\render_recipe_pdf.py `
  --html .\source.html `
  --hero .\hero.jpg `
  --logo .\logo.png `
  --output .\recipe.pdf
```

## Project layout

```
build-recipe-pdfs.ps1       PowerShell wrapper / entry point
recipe-urls.txt             Input list of recipe URLs
data/build_recipe_pdfs.py   Batch driver: downloads HTML + hero images
data/render_recipe_pdf.py   HTML/JSON-LD parser + ReportLab PDF layout
reports/                    Generated PDFs (gitignored)
```

## Notes & disclaimer

- The HTML parser relies on the current 24Kitchen page structure (specific CSS
  class names, JSON-LD `@graph` shape). If the site changes its markup, the
  regexes in `render_recipe_pdf.py` will need to be updated.
- Recipes, images and the 24Kitchen logo are © 24Kitchen and the respective
  recipe authors. This tool is intended for personal, offline use of recipes
  you would otherwise read on the site; do not redistribute the generated PDFs.

## License

[MIT](./LICENSE)
