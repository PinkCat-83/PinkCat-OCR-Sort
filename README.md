# 🗂️ PinkCat OCR Sort

Desktop tool for renaming and organizing images by creation date, with automatic name detection via OCR and a manual batch review mode.

---

## What is this?

When generating large numbers of AI images with a tool like [Auto-Prompting](../Auto-Prompting/README.md), output files accumulate quickly and become hard to manage. PinkCat OCR Sort reads the text visible in each image (a name in a corner, a label, etc.), matches it against a predefined list of character names, and automatically sorts each file into the correct folder — renaming it by creation date in the process.

Files where no name is detected are organized by date hierarchy. Files where text is detected but doesn't match any known name go to `_Sin clasificar` for manual review.

---

## Requirements

- Python 3.11+
- Windows 10/11

```bash
pip install -r requirements.txt
```

> The first run downloads EasyOCR models (~300 MB). This is normal and only happens once.

---

## Installation

1. Unzip the project into any folder.
2. Install dependencies: `pip install -r requirements.txt`
3. Double-click `organizar.pyw` to open the app.

---

## Usage

### 01 — Folders

- **Source folder** — contains the images to organize. Only root-level files are processed (no subfolders).
- **Destination folder** — where organized files will be saved.
- **Organize in same folder** — uses source as destination.

Session is saved automatically on close and restored on next launch. **First run only:** you'll be asked to choose an existing session file or create a new one — this lets you keep it in a cloud-synced folder (Google Drive, Dropbox…) so it follows you between computers. See the [Technical README](./README_TECH.md#7-session-persistence--configurable-location) for details.

### 02 — OCR and Name Detection

The app reads text visible in each image and compares it against a list of known names to decide which folder to move it to.

**Name list (`nombres.txt`)** — one name per line. Lines starting with `#` are comments. **First run only:** you'll be asked to choose an existing names file or create a new one with example names — same as the session file, this can live in a synced folder so it follows you between computers. See the [Technical README](./README_TECH.md#7-configurable-file-locations-session--names-list) for details.

```
# Characters
Ana
Carlos

# Other
Vacaciones
```

Use **↺ CARGAR** to reload after editing, or **+ CREAR EJEMPLO** to generate a sample file.

**Similarity threshold**
- **Low (40–60%)** — more permissive, accepts larger variations (useful when OCR reads poorly)
- **High (80–100%)** — stricter, only accepts near-exact matches

**Detection results**

| Case | Destination |
|---|---|
| OCR matches a name | `Destination/DetectedName/file` |
| OCR detects text but no match | `Destination/_Sin clasificar/file` |
| No text detected | `Destination/Year/MM Month/DD/file` |

**GPU (CUDA)** — if you have a compatible NVIDIA GPU, enable this for significantly faster OCR.

### 03 — Action

- **Review mode** — before moving each batch of 8 images, opens a window with thumbnail and dropdown to confirm or change each destination.
- **▶ INICIAR ORGANIZACIÓN** — starts processing.
- **⛔ CANCELAR** — stops after the current file.

---

## Renaming Scheme

All files are renamed by creation date:

```
Format:    dd-MM-yyyy ; HH.mm.ss.ffff
Structure: Destination / Year / MM MonthName / DD / file

Example:   Destination / 2024 / 03 marzo / 15 / 15-03-2024 ; 14.32.11.0000.jpg
```

If the filename already exists at destination, microseconds are added until a free name is found.

---

## Troubleshooting

**OCR detects text but no match** → lower the similarity threshold. Use `test_ocr.py` to see exactly what the OCR reads:
```bash
python test_ocr.py "path\to\image.jfif"
```

**First run is very slow** → EasyOCR downloads its models (~300 MB) once. Subsequent runs are instant.

**`.jfif` files not detected** → PIL handles `.jfif` correctly before passing to EasyOCR — if this happens, check the file isn't corrupted.

---

## Technical Documentation

→ [Technical README](./README_TECH.md)
