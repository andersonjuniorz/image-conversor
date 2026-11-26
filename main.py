import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices

from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from core.batch import BatchWorker, Job, JobResult
from core.file_scanner import OUTPUT_DIR_NAME, SourceFile, scan
from core.output_namer import OutputNamer
from core.report import build_report, save_report
from formats.registry import REGISTRY
from ui.theme import STYLESHEET
from ui.widgets import FormatButton, ReportDialog, StatBox, make_card, muted, section

# Colors used for success and error lines in the log and summary.
COLOR_OK = QColor("#34d399")
COLOR_ERR = QColor("#f87171")


# Removes all widgets from a layout.
def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()


# Main window: builds the screen and controls the conversion flow.
class MainWindow(QMainWindow):
    # Set up the window, the state variables and the cards.
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Converter")
        self.resize(780, 900)

        # App state: chosen folder, found files, output folder, etc.
        self.root: Path | None = None
        self.files: list[SourceFile] = []
        self.output_dir: Path | None = None
        self.worker: BatchWorker | None = None
        self.target_id = ""
        self.selected_target = None      # format picked by the user, not yet confirmed
        self.started_at = datetime.now()
        self.last_report = ""
        self._busy = False               # True while a conversion is running

        # Scroll area so the page works on small screens.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        page.setObjectName("page")
        scroll.setWidget(page)
        self.setCentralWidget(scroll)

        # Vertical layout that holds all the cards, in order.
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(18)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_folder_card())
        layout.addWidget(self._build_formats_card())
        layout.addWidget(self._build_confirm_card())
        layout.addWidget(self._build_progress_card())
        layout.addWidget(self._build_log_card())
        layout.addWidget(self._build_summary_card())
        layout.addStretch()

        # Set buttons to their correct enabled state at startup.
        self._refresh_state()

    # ---------- screen building ----------

    # Builds the title, the short description and the format badge.
    def _build_header(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Image Converter")
        title.setObjectName("title")

        subtitle = QLabel(
            "Converta imagens em lote entre os formatos disponíveis. "
            "Escolha uma pasta e o formato de destino; os arquivos serão "
            f"gerados em {OUTPUT_DIR_NAME}."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        # Shows the formats that are actually available, e.g. "JPEG · PNG · WEBP".
        badge = QLabel("  ·  ".join(f.id.upper() for f in REGISTRY.all()))
        badge.setObjectName("badge")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(badge, 0, Qt.AlignLeft)
        return box

    # Step 1: folder button, selected path, and file count chips.
    def _build_folder_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("1. Pasta de imagens"))
        layout.addWidget(
            muted("As imagens dentro da pasta, inclusive em subpastas, serão convertidas.")
        )

        # Button that opens the folder picker.
        self.btn_pick = QPushButton("Buscar pasta")
        self.btn_pick.setObjectName("primary")
        self.btn_pick.setCursor(Qt.PointingHandCursor)
        self.btn_pick.clicked.connect(self.pick_folder)
        layout.addWidget(self.btn_pick, 0, Qt.AlignLeft)

        # Shows the full path of the chosen folder.
        self.lbl_path = QLabel("Nenhuma pasta selecionada")
        self.lbl_path.setObjectName("path")
        self.lbl_path.setWordWrap(True)
        layout.addWidget(self.lbl_path)

        # Row of chips, one per file type found (e.g. "PNG 14").
        self.chips_box = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_box)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(8)
        layout.addWidget(self.chips_box)

        # Total count of images found.
        self.lbl_count = muted("")
        layout.addWidget(self.lbl_count)
        return frame

    # Step 2: one button for each available format.
    def _build_formats_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("2. Formato de destino"))

        # Hint text that changes with the current state.
        self.lbl_question = muted("Escolha uma pasta para liberar as opções.")
        layout.addWidget(self.lbl_question)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.format_buttons: list[FormatButton] = []

        # Create one button per registered format.
        for fmt in REGISTRY.all():
            btn = FormatButton(fmt.id.upper())
            # Pass both the format and its button when clicked.
            btn.clicked.connect(
                lambda _=False, f=fmt, b=btn: self.on_format_selected(f, b)
            )
            row.addWidget(btn)
            self.format_buttons.append(btn)

        row.addStretch()
        layout.addLayout(row)
        return frame

    # Step 3: shows the chosen format and the Confirmar button.
    def _build_confirm_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("3. Confirmação"))

        # Text that asks the user to confirm the chosen format.
        self.lbl_confirm = muted("Deseja converter para este formato?")
        layout.addWidget(self.lbl_confirm)

        row = QHBoxLayout()
        row.setSpacing(10)
        # Starts disabled until a format is selected.
        self.btn_confirm = FormatButton("Confirmar")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self.confirm_conversion)
        row.addWidget(self.btn_confirm)
        row.addStretch()
        layout.addLayout(row)
        return frame

    # Step 4: progress bar and status line.
    def _build_progress_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("4. Conversão"))

        # Bar that fills as files are converted.
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Short text describing the current step.
        self.lbl_status = muted("Aguardando pasta.")
        layout.addWidget(self.lbl_status)
        return frame

    # Per-file log list, one line for each converted or failed file.
    def _build_log_card(self) -> QFrame:
        frame, layout = make_card()
        layout.addWidget(section("Progresso por arquivo"))

        self.log = QListWidget()
        self.log.setMinimumHeight(220)
        # Read-only list: no selection and no keyboard focus.
        self.log.setSelectionMode(QListWidget.NoSelection)
        self.log.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.log)
        return frame

    # Final summary: stat boxes and buttons. Hidden until a run finishes.
    def _build_summary_card(self) -> QFrame:
        self.summary = QFrame()
        self.summary.setObjectName("card")
        layout = QVBoxLayout(self.summary)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        layout.addWidget(section("Resultado"))

        # Three boxes: converted, errors and elapsed time.
        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.st_ok = StatBox("Convertidos")
        self.st_err = StatBox("Erros")
        self.st_time = StatBox("Tempo")
        for box in (self.st_ok, self.st_err, self.st_time):
            stats.addWidget(box)
        layout.addLayout(stats)

        # Line with the target format and output folder.
        self.lbl_totals = muted("")
        layout.addWidget(self.lbl_totals)

        # Buttons to open the report and the output folder.
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.btn_report = QPushButton("Ver relatório")
        self.btn_report.setObjectName("secondary")
        self.btn_report.setCursor(Qt.PointingHandCursor)
        self.btn_report.clicked.connect(self.show_report)
        self.btn_open = QPushButton("Abrir pasta de resultados")
        self.btn_open.setObjectName("secondary")
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_output)
        buttons.addWidget(self.btn_report)
        buttons.addWidget(self.btn_open)
        buttons.addStretch()
        layout.addLayout(buttons)

        # Hidden until the conversion finishes.
        self.summary.hide()
        return self.summary

    # ---------- state ----------

    # Enables or disables the buttons based on the current state.
    def _refresh_state(self):
        busy = self._busy
        has_files = bool(self.files)
        # The folder and format buttons are locked while converting.
        self.btn_pick.setEnabled(not busy)
        for btn in self.format_buttons:
            btn.setEnabled(not busy)
        # Confirmar needs files, a selected format, and no running job.
        self.btn_confirm.setEnabled(
            not busy and has_files and self.selected_target is not None
        )

    # Rebuilds the chips row with one chip per file type and its count.
    def _set_chips(self, counts: Counter):
        clear_layout(self.chips_layout)
        for ext, n in sorted(counts.items()):
            chip = QLabel(f"{ext}  {n}")
            chip.setObjectName("chip")
            self.chips_layout.addWidget(chip)
        self.chips_layout.addStretch()

    # ---------- selection ----------

    # Runs when a format button is clicked. Only selects it; does not convert.
    def on_format_selected(self, target, button: FormatButton):
        # If no folder was chosen yet, ask for one first.
        if not self.files:
            self.lbl_status.setText("Primeiro escolha uma pasta com imagens.")
            self.pick_folder()
            # Still no files after the dialog: undo the selection.
            if not self.files:
                self._clear_selection()
                return

        # Exclusive selection by hand: only the clicked button stays checked.
        for btn in self.format_buttons:
            btn.setChecked(btn is button)

        # Remember the choice and update the confirmation text.
        self.selected_target = target
        self.lbl_confirm.setText(
            f"Formato escolhido: {target.id.upper()}. Deseja converter para este formato?"
        )
        self._refresh_state()

    # Removes the current format choice and resets the confirmation text.
    def _clear_selection(self):
        self.selected_target = None
        for btn in self.format_buttons:
            btn.setChecked(False)
        self.lbl_confirm.setText("Deseja converter para este formato?")
        self._refresh_state()

    # Runs when Confirmar is clicked. Starts the conversion with the selected format.
    def confirm_conversion(self):
        if self.selected_target is not None:
            self.start(self.selected_target)

    # ---------- actions ----------

    # Opens the folder picker, scans the folder and updates the screen.
    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta com as imagens", str(Path.home())
        )
        # User cancelled the dialog.
        if not folder:
            return

        # Store the chosen folder and its output folder.
        self.root = Path(folder)
        self.output_dir = self.root / OUTPUT_DIR_NAME
        # Find all supported images, including subfolders.
        self.files = scan(self.root, REGISTRY.extensions())
        # Reset the screen for the new folder.
        self.lbl_path.setText(str(self.root))
        self.log.clear()
        self.summary.hide()
        self.progress.setValue(0)
        self._clear_selection()

        # Count files per type and show the chips.
        counts = Counter(f.path.suffix.lstrip(".").upper() for f in self.files)
        self._set_chips(counts)

        # Update the texts depending on whether files were found.
        if not self.files:
            self.lbl_count.setText("Nenhuma imagem compatível encontrada.")
            self.lbl_question.setText("Escolha outra pasta.")
            self.lbl_status.setText("Escolha outra pasta.")
        else:
            self.lbl_count.setText(f"{len(self.files)} imagens encontradas.")
            self.lbl_question.setText("Escolha o formato de destino e depois clique em Confirmar.")
            self.lbl_status.setText("Pronto. Escolha o formato de destino.")

        self._refresh_state()

    # Creates one job per file and starts the background worker.
    def start(self, target):
        # Do nothing if already busy or missing a folder or files.
        if self._busy or not self.files or self.root is None:
            return

        # Make sure the output folder exists.
        self.output_dir.mkdir(exist_ok=True)
        # Namer that avoids duplicate names in the same folder.
        namer = OutputNamer()
        jobs: list[Job] = []
        for src in self.files:
            # Find the decoder for this file's extension.
            source_fmt = REGISTRY.by_extension(src.path.suffix.lstrip(".").lower())
            # Build the output name and full destination path.
            name = namer.next_name(src.relative_dir, src.path.name, target.extensions[0])
            dst = self.output_dir / src.relative_dir / name
            jobs.append(Job(src, source_fmt, target, dst))

        # Save run info and reset the progress UI.
        self.target_id = target.id
        self.started_at = datetime.now()
        self.log.clear()
        self.summary.hide()
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.lbl_status.setText(f"Convertendo para {target.id.upper()}...")

        # Lock the UI and start the worker thread.
        self._busy = True
        self._refresh_state()

        self.worker = BatchWorker(jobs)
        self.worker.progress.connect(self._on_progress)
        self.worker.item_done.connect(self._on_item)
        self.worker.finished_batch.connect(self._on_finished)
        self.worker.start()

    # Updates the progress bar and status text after each file.
    def _on_progress(self, done: int, total: int):
        self.progress.setValue(done)
        self.lbl_status.setText(f"Processando {done} de {total}...")

    # Adds one line to the log for a finished file (success or error).
    def _on_item(self, res: JobResult):
        # Show the path relative to the chosen folder.
        src_rel = res.job.source.path.relative_to(self.root)
        if res.ok:
            text = f"✔  {src_rel}   →   {res.job.dst.name}"
            color = COLOR_OK
        else:
            text = f"✖  {src_rel}   {res.error}"
            color = COLOR_ERR

        item = QListWidgetItem(text)
        item.setForeground(color)
        self.log.addItem(item)
        self.log.scrollToBottom()

    # Runs when the whole batch ends: shows stats, saves the report and alerts the user.
    def _on_finished(self, results: list[JobResult]):
        # Unlock the UI.
        self._busy = False
        self._refresh_state()
        finished_at = datetime.now()

        # Split the results into successes and errors.
        ok = [r for r in results if r.ok]
        errors = [r for r in results if not r.ok]
        elapsed = (finished_at - self.started_at).total_seconds()

        # Fill the stat boxes.
        self.st_ok.set_value(str(len(ok)), COLOR_OK.name())
        self.st_err.set_value(str(len(errors)), COLOR_ERR.name() if errors else None)
        self.st_time.set_value(f"{elapsed:.1f}s")
        self.lbl_totals.setText(
            f"Formato de destino: {self.target_id.upper()}  ·  "
            f"pasta de saída: {OUTPUT_DIR_NAME}/"
        )

        # Build the report text and try to save it to a file.
        self.last_report = build_report(
            results, self.root, self.target_id, self.started_at, finished_at
        )
        try:
            save_report(self.last_report, self.root)
            note = f"Relatório salvo em {OUTPUT_DIR_NAME}/relatorio.txt."
        except OSError as exc:
            note = f"Não foi possível salvar o relatório: {exc}"

        self.lbl_status.setText(f"Concluído em {elapsed:.1f}s. {note}")
        self.summary.show()

        # Alert the user, then show the report.
        QMessageBox.information(self, "Conversão", "Conversão finalizada!")
        self.show_report()

    # Opens the report dialog if a report exists.
    def show_report(self):
        if self.last_report:
            ReportDialog(self.last_report, self).exec()

    # Opens the output folder in the system file manager.
    def open_output(self):
        if self.output_dir and self.output_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    # Blocks closing the window while a conversion is still running.
    def closeEvent(self, event):
        if self._busy:
            QMessageBox.information(self, "Aguarde", "A conversão ainda está em andamento.")
            event.ignore()
            return
        event.accept()


# Creates the app, applies the theme, shows the window and starts the event loop.
def main():
    app = QApplication(sys.argv)
    # Fusion is a cross-platform style that accepts our custom QSS.
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


# Run main() only when this file is executed directly.
if __name__ == "__main__":
    main()
