# Image Converter

A desktop app to convert images in batch between common formats. It has a simple graphical interface, works on Linux and Windows, and is easy to extend with new formats.

## Features

- Batch conversion of all supported images in a folder, including subfolders.
- Supported formats: JPEG, PNG, WebP, AVIF and JPEG XL (when the plugin is installed).
- Transparency is kept when the target format supports it. For formats without transparency, the background becomes white.
- EXIF rotation is applied to the pixels, so photos from phones stay upright.
- Color profiles are converted to sRGB.
- Converted files are saved in an `ImagesConverted/` folder, keeping the original subfolder structure.
- Name collisions in the same folder are handled with numbers: `photo_jpg.webp`, `photo_jpg(1).webp`, and so on.
- A file with an error does not stop the batch. All errors are listed in a report.
- The report is also saved as `ImagesConverted/relatorio.txt`.

Metadata is not preserved. Compression is not part of this app.

## Requirements

- Python 3.14
- Linux or Windows

## Installation

```bash
git clone <repository-url>
cd image-converter
make install
```

Without `make`, use the manual steps:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Start the app:

```bash
make run
```

Or, without `make`:

```bash
python main.py
```

Then:

1. Click **Buscar pasta** and choose the folder with your images.
2. Check the file count shown for each type.
3. Click a format button (for example, **WEBP**). It becomes selected.
4. Click **Confirmar** to start the conversion.
5. When it finishes, you get a summary, the report, and the **Abrir pasta de resultados** button.

Running the conversion again replaces the files in `ImagesConverted/` with the same names.

## Development

| Command | What it does |
|---|---|
| `make install` | Creates `.venv` and installs the app dependencies |
| `make run` | Installs if needed and starts the app |
| `make test` | Installs the dev tools and runs the build test |
| `make local-build` | Builds the executable the same way as CI |
| `make clean` | Removes caches, build folders and `.venv` |

Run `make test` and `make local-build` before every push.

## Branches

- `main`: stable code. Tags `v*` on this branch publish a release.
- `develop`: integration branch. Features are merged here first.
- `feature/*`: new work, branched from `develop`.

Open a pull request from `feature/*` into `develop`, and from `develop` into `main` when preparing a release.

## Project structure

```
image-converter/
├── main.py                  # Main window and conversion flow
├── Makefile                 # Development commands
├── requirements.txt         # App dependencies
├── requirements-dev.txt     # Dev tools (pytest)
├── core/
│   ├── batch.py             # Parallel conversion and worker thread
│   ├── file_scanner.py      # Folder scan
│   ├── output_namer.py      # Output file names and collisions
│   ├── pipeline.py          # Pixel preparation (rotation, alpha, color)
│   └── report.py            # Report text and file
├── formats/
│   ├── base.py              # Format interface
│   ├── pillow_formats.py    # Format implementations
│   └── registry.py          # Available formats
├── ui/
│   ├── theme.py             # Visual style (Qt stylesheet)
│   └── widgets.py           # Reusable widgets
├── tests/
│   └── test_build.py        # Builds the executable and checks that it starts
└── .github/workflows/
    └── build.yml            # CI: builds Linux and Windows executables
```

## Adding a new format

1. Create a class in `formats/pillow_formats.py` (or a new file) that follows the `ImageFormat` interface in `formats/base.py`.
2. Add it to `ALL_FORMATS` in the same file.
3. Run `make test`.

The format only appears in the interface if the codec is available on the system. The registry checks this at startup.

## CI and releases

The workflow in `.github/workflows/build.yml` runs on pushes to `main`, on pull requests, and on version tags.

- Each run builds one executable for Linux and one for Windows, and uploads them as artifacts.
- A tag like `v0.1.0` on `main` also creates a GitHub release with both files attached.

```bash
git checkout main
git pull
git tag v0.1.0
git push origin v0.1.0
```

## Notes

- On Linux, the executable may need `chmod +x image-converter` after download.
- If the Qt window does not open on Linux, install the missing library with `sudo apt install libxcb-cursor0`.
- The Linux build runs on systems equal to or newer than Ubuntu 22.04.
