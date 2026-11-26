from dataclasses import dataclass
from pathlib import Path

# Name of the output folder. It is skipped during the scan.
OUTPUT_DIR_NAME = "ImagesConverted"


# One image found in the user's folder.
@dataclass(frozen=True)
class SourceFile:
    path: Path          # full path to the file
    relative_dir: Path  # folder relative to the root; Path(".") if at the root


# Walks the folder and all subfolders, keeping only supported images.
def scan(root: Path, known_extensions: set[str]) -> list[SourceFile]:
    """Recursively scan root, skipping ImagesConverted/ at the top level."""
    files: list[SourceFile] = []
    # Check every entry under root, including subfolders.
    for p in root.rglob("*"):
        # Ignore folders and anything that is not a regular file.
        if not p.is_file():
            continue
        # Path relative to the chosen root folder.
        rel = p.relative_to(root)
        # Skip the output folder so converted files are not read again.
        if rel.parts[0] == OUTPUT_DIR_NAME:
            continue
        # Normalize the extension: lowercase, no dot.
        ext = p.suffix.lower().lstrip(".")
        # Skip files whose format is not registered.
        if ext not in known_extensions:
            continue
        # Keep the file and the folder it lives in.
        files.append(SourceFile(p, rel.parent))
    return files
