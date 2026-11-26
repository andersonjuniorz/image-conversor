from datetime import datetime
from pathlib import Path

from .batch import JobResult
from .file_scanner import OUTPUT_DIR_NAME


# Builds the text of the report shown to the user and saved to relatorio.txt.
def build_report(results: list[JobResult], folder: Path, target_id: str,
                 started: datetime, finished: datetime) -> str:
    """Build the report text with totals, dates and the list of failed files."""
    # Split the results into successful and failed ones.
    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]

    # Header lines with the general information about the run.
    lines = [
        "Relatório de conversão",
        f"Pasta de origem: {folder}",
        f"Formato de destino: {target_id}",
        f"Início: {started:%d/%m/%Y %H:%M:%S}",
        f"Fim: {finished:%d/%m/%Y %H:%M:%S}",
        "",
        f"Total: {len(results)}",
        f"Convertidos: {len(ok)}",
        f"Falhas: {len(failed)}",
    ]
    # Add a section listing each failed file, only when there are failures.
    if failed:
        lines += ["", "Arquivos com falha:"]
        for r in failed:
            # Show the path relative to the chosen folder, plus the error message.
            rel = r.job.source.path.relative_to(folder)
            lines.append(f"- {rel}: {r.error}")
    # Join all lines into one text block.
    return "\n".join(lines)


# Saves the report text as relatorio.txt inside the output folder.
def save_report(text: str, folder: Path) -> Path:
    """Write the report to ImagesConverted/relatorio.txt and return its path."""
    # Full path of the report file.
    out = folder / OUTPUT_DIR_NAME / "relatorio.txt"
    # Create the output folder if it does not exist yet.
    out.parent.mkdir(parents=True, exist_ok=True)
    # Save the text using UTF-8 so accents are kept.
    out.write_text(text, encoding="utf-8")
    return out
