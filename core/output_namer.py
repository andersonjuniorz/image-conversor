from pathlib import Path


# Builds output file names and avoids collisions inside the same folder.
class OutputNamer:
    """
    foto.jpg -> foto_jpg.webp
    collision in the same folder -> foto_jpg(1).webp, foto_jpg(2).webp
    The counter only lasts for the current run.
    """

    # Start with an empty record of used names for each folder.
    def __init__(self):
        self._used: dict[str, set[str]] = {}

    # Returns a unique output name for one source file.
    def next_name(self, relative_dir: Path, source_name: str, target_ext: str) -> str:
        # Split the source name into its parts.
        src = Path(source_name)
        # Build the base name, keeping the original extension: foto_jpg.
        base = f"{src.stem.lower()}_{src.suffix.lstrip('.').lower()}"
        # Normalize the target extension to lowercase.
        ext = target_ext.lower()

        # Get the set of names already used in this folder.
        used = self._used.setdefault(str(relative_dir).lower(), set())
        # Try the plain name first.
        candidate = f"{base}.{ext}"
        n = 1
        # If the name is taken, add a number: (1), (2), and so on.
        while candidate in used:
            candidate = f"{base}({n}).{ext}"
            n += 1

        # Remember the chosen name so it is not reused.
        used.add(candidate)
        return candidate
