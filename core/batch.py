import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from formats.base import ImageFormat
from .file_scanner import SourceFile
from .pipeline import prepare_image


# One conversion task: where the file comes from and where it goes.
@dataclass(frozen=True)
class Job:
    source: SourceFile          # original file and its relative folder
    source_format: ImageFormat  # decoder used to read the source
    target: ImageFormat         # encoder used to write the output
    dst: Path                   # full output path


# Outcome of one job: success flag and an error message if it failed.
@dataclass(frozen=True)
class JobResult:
    job: Job
    ok: bool
    error: str = ""


# Converts a single file. Runs in a worker thread.
def run_job(job: Job) -> JobResult:
    try:
        # Make sure the output subfolder exists.
        job.dst.parent.mkdir(parents=True, exist_ok=True)
        # Read the source file into a Pillow image.
        img = job.source_format.decode(str(job.source.path))
        # Apply rotation, alpha handling and color profile fixes.
        img = prepare_image(img, job.target.capabilities.supports_alpha)
        # Write the image in the target format.
        job.target.encode(img, str(job.dst))
        return JobResult(job, True)
    except Exception as exc:  # one failed file does not stop the batch
        return JobResult(job, False, f"{type(exc).__name__}: {exc}")


# Qt thread that runs all jobs in parallel and reports progress to the GUI.
class BatchWorker(QThread):
    progress = Signal(int, int)       # done, total
    item_done = Signal(object)        # JobResult, one per file
    finished_batch = Signal(list)     # list of all JobResult

    # Store the jobs to run.
    def __init__(self, jobs: list[Job], parent=None):
        super().__init__(parent)
        self._jobs = jobs

    # Runs in the background thread. Leaves one CPU core free.
    def run(self):
        # Number of workers: all cores minus one, at least one.
        workers = max(1, (os.cpu_count() or 2) - 1)
        results: list[JobResult] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Submit every job to the pool.
            futures = [pool.submit(run_job, j) for j in self._jobs]
            # Handle each result as soon as it finishes.
            for done, fut in enumerate(as_completed(futures), 1):
                res = fut.result()
                results.append(res)
                self.item_done.emit(res)
                self.progress.emit(done, len(futures))
        # Send the full list when the batch is complete.
        self.finished_batch.emit(results)
