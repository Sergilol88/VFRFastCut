# SPDX-License-Identifier: MIT
"""Integrate the 0.5.x task progress dialog into vfr_fastcut.py.

Run this helper on a locally integrated feature/0.5.0 working tree. It is
idempotent and intentionally patches stable UI/export/keyframe anchors so it
can be applied after the edited-preview development helper.
"""

from __future__ import annotations

from pathlib import Path


MARKER = "class TaskProgressDialog(QDialog):"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "vfr_fastcut.py"
    if not target.is_file():
        raise RuntimeError(f"vfr_fastcut.py not found at {target}")

    text = target.read_text(encoding="utf-8")
    if MARKER in text:
        print("Task progress dialog is already integrated; nothing to do.")
        return 0

    # ---- localized task-dialog text ----
    text = replace_once(
        text,
        '        "cancel_export": "Cancel export",\n',
        '        "cancel_export": "Cancel export",\n'
        '        "task_export_title": "Lossless Export",\n'
        '        "task_export_preparing": "Preparing export…",\n'
        '        "task_keyframe_title": "Analyzing video",\n'
        '        "task_keyframe_hint": "You can continue editing while keyframes are analyzed.",\n',
        "English task progress text",
    )
    text = replace_once(
        text,
        '        "cancel_export": "Отмена экспорта",\n',
        '        "cancel_export": "Отмена экспорта",\n'
        '        "task_export_title": "Lossless Export",\n'
        '        "task_export_preparing": "Подготавливаю экспорт…",\n'
        '        "task_keyframe_title": "Анализ видео",\n'
        '        "task_keyframe_hint": "Можно продолжать монтаж, пока анализируются keyframes.",\n',
        "Russian task progress text",
    )

    # ---- reusable dialog component ----
    dialog_class = r'''class TaskProgressDialog(QDialog):
    """Compact modeless progress window shared by long-running tasks."""

    cancelRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(520)

        self._active = False
        self._cancellable = False
        self._allow_hide = True
        self._user_hidden = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        self.title_label = QLabel()
        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPointSize(max(title_font.pointSize(), 11))
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.step_label = QLabel()
        self.step_label.setWordWrap(True)
        self.step_label.setMinimumHeight(36)
        layout.addWidget(self.step_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(24)
        layout.addWidget(self.progress_bar)

        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #777;")
        layout.addWidget(self.hint_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self._request_cancel)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

    def begin(
        self,
        *,
        window_title: str,
        title: str,
        text: str,
        percent: int | None = 0,
        hint: str = "",
        cancel_text: str = "Cancel",
        cancellable: bool = False,
        allow_hide: bool = True,
        focus: bool = False,
    ):
        self._active = True
        self._cancellable = bool(cancellable)
        self._allow_hide = bool(allow_hide)
        self._user_hidden = False

        self.setWindowTitle(window_title)
        self.title_label.setText(title)
        self.step_label.setText(text)
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))
        self.cancel_btn.setText(cancel_text)
        self.cancel_btn.setVisible(bool(cancellable))
        self.cancel_btn.setEnabled(bool(cancellable))
        self.set_progress(percent)

        self.adjustSize()
        self.show()
        if focus:
            self.raise_()
            self.activateWindow()
            if self.cancel_btn.isVisible():
                self.cancel_btn.setFocus(Qt.FocusReason.OtherFocusReason)

    def set_progress(self, percent: int | None):
        if percent is None:
            self.progress_bar.setRange(0, 0)
            return
        if self.progress_bar.minimum() == 0 and self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(max(0, min(100, int(percent))))

    def update_task(
        self,
        *,
        percent: int | None = None,
        text: str | None = None,
        hint: str | None = None,
    ):
        if not self._active:
            return
        if percent is not None:
            self.set_progress(percent)
        if text is not None:
            self.step_label.setText(text)
        if hint is not None:
            self.hint_label.setText(hint)
            self.hint_label.setVisible(bool(hint))

    def set_cancel_enabled(self, enabled: bool):
        if not self._active:
            return
        self._cancellable = bool(enabled)
        self.cancel_btn.setEnabled(bool(enabled))

    def finish(self):
        self._active = False
        self._cancellable = False
        self._user_hidden = False
        self.hide()

    def _request_cancel(self):
        if not self._active or not self._cancellable:
            return
        self._cancellable = False
        self.cancel_btn.setEnabled(False)
        self.cancelRequested.emit()

    def closeEvent(self, event):
        if not self._active:
            event.accept()
            return

        if self._cancellable:
            self._request_cancel()
            event.ignore()
            return

        if self._allow_hide:
            self._user_hidden = True
            self.hide()
            event.ignore()
            return

        # Export cancellation may take a moment; keep the task visible until
        # the worker reports cancelled/finished/failed.
        event.ignore()


'''
    text = replace_once(
        text,
        "class MainWindow(QMainWindow):\n",
        dialog_class + "class MainWindow(QMainWindow):\n",
        "TaskProgressDialog insertion",
    )

    # ---- MainWindow task-progress state ----
    text = replace_once(
        text,
        "        # Created after the native HWND exists (singleShot below).\n"
        "        self.taskbar_progress: Optional[WindowsTaskbarProgress] = None\n\n",
        "        # Created after the native HWND exists (singleShot below).\n"
        "        self.taskbar_progress: Optional[WindowsTaskbarProgress] = None\n\n"
        "        self.task_progress_dialog = TaskProgressDialog(self)\n"
        "        self.task_progress_dialog.cancelRequested.connect(self.cancel_export)\n"
        "        self._task_progress_owner = \"\"\n"
        "        self._keyframe_scan_percent = 0\n"
        "        self._keyframe_progress_show_timer = QTimer(self)\n"
        "        self._keyframe_progress_show_timer.setSingleShot(True)\n"
        "        self._keyframe_progress_show_timer.setInterval(300)\n"
        "        self._keyframe_progress_show_timer.timeout.connect(\n"
        "            self._show_keyframe_progress_dialog\n"
        "        )\n\n",
        "MainWindow task progress state",
    )

    # Dedicated dialog owns cancellation; the main window keeps one stable
    # export button rather than swapping it with a second Cancel button.
    old_export_widgets = '''        self.cancel_export_btn = QPushButton(self._t("cancel_export"))
        self.cancel_export_btn.setFixedWidth(140)
        self.cancel_export_btn.clicked.connect(self.cancel_export)

        # Export/Cancel occupy exactly the same fixed-width slot.
        # Switching between them cannot move neighbouring controls.
        self.export_stack = QStackedWidget()
        self.export_stack.setFixedWidth(140)
        self.export_stack.addWidget(self.export_btn)
        self.export_stack.addWidget(self.cancel_export_btn)
        self.export_stack.setCurrentWidget(self.export_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(18)

        # Keep the progress bar in the layout at all times so starting/stopping
        # an export never changes the geometry of preview, timeline or controls.
        self._set_progress_visible(False)

'''
    text = replace_once(
        text,
        old_export_widgets,
        "",
        "remove permanent progress/cancel widgets",
    )

    # Move the byline into the final export row so the actual controls occupy
    # the bottom edge of the main window after the progress row is removed.
    old_bottom = '''        export_row = QHBoxLayout()
        export_row.addStretch(1)
        export_row.addWidget(self.export_video_check)
        export_row.addWidget(self.export_audio_check)
        export_row.addWidget(self.export_stack)
        bottom_layout.addLayout(export_row)

        footer = QHBoxLayout()
        footer.addStretch(1)
        author_label = QLabel("by Sergilol")
        author_label.setStyleSheet("color: #777; font-size: 10px;")
        footer.addWidget(author_label)
        bottom_layout.addLayout(footer)
        bottom_layout.addWidget(self.progress)
'''
    new_bottom = '''        export_row = QHBoxLayout()
        author_label = QLabel("by Sergilol")
        author_label.setStyleSheet("color: #777; font-size: 10px;")
        export_row.addWidget(author_label)
        export_row.addStretch(1)
        export_row.addWidget(self.export_video_check)
        export_row.addWidget(self.export_audio_check)
        export_row.addWidget(self.export_btn)
        bottom_layout.addLayout(export_row)
'''
    text = replace_once(text, old_bottom, new_bottom, "bottom controls reflow")

    # No old bar state remains to clear during reset.
    text = replace_once(
        text,
        "        self.progress.setValue(0)\n",
        "",
        "remove reset progress value",
    )

    # UI state no longer manages an in-window Cancel/Export stack.
    old_stack_state = '''        self.cancel_export_btn.setEnabled(self._export_busy)
        self.export_stack.setCurrentWidget(
            self.cancel_export_btn if self._export_busy else self.export_btn
        )

'''
    text = replace_once(text, old_stack_state, "", "remove export stack state")

    # ---- keyframe scan progress ----
    text = replace_once(
        text,
        "    def _cancel_keyframe_scan(self):\n"
        "        cancel_event = self._keyframe_scan_cancel_event\n",
        "    def _cancel_keyframe_scan(self):\n"
        "        self._keyframe_progress_show_timer.stop()\n"
        "        self._hide_task_progress(\"keyframes\")\n"
        "        cancel_event = self._keyframe_scan_cancel_event\n",
        "cancel keyframe progress UI",
    )

    text = replace_once(
        text,
        "        self.statusBar().showMessage(self._t(\"keyframe_scan_started\"))\n",
        "        self._keyframe_scan_percent = 0\n"
        "        self.statusBar().showMessage(self._t(\"keyframe_scan_started\"))\n",
        "keyframe initial percent",
    )

    text = replace_once(
        text,
        "        self.keyframe_scan_thread = thread\n"
        "        thread.start()\n",
        "        self.keyframe_scan_thread = thread\n"
        "        thread.start()\n"
        "        self._keyframe_progress_show_timer.start()\n",
        "delayed keyframe dialog",
    )

    text = replace_once(
        text,
        "    def on_keyframe_scan_progress(self, generation: int, percent: int):\n"
        "        if generation != self._keyframe_scan_generation:\n"
        "            return\n"
        "        if not self._export_busy:\n",
        "    def on_keyframe_scan_progress(self, generation: int, percent: int):\n"
        "        if generation != self._keyframe_scan_generation:\n"
        "            return\n"
        "        self._keyframe_scan_percent = max(0, min(100, int(percent)))\n"
        "        if self._task_progress_owner == \"keyframes\":\n"
        "            self._update_task_progress(\n"
        "                \"keyframes\",\n"
        "                percent=self._keyframe_scan_percent,\n"
        "                text=self._t(\n"
        "                    \"keyframe_scan_progress\",\n"
        "                    percent=self._keyframe_scan_percent,\n"
        "                ),\n"
        "            )\n"
        "        if not self._export_busy:\n",
        "keyframe dialog progress",
    )

    # Insert cleanup immediately after the stale-generation guard in both
    # finished and failed callbacks without replacing any edited-preview code.
    text = replace_once(
        text,
        "    def on_keyframe_scan_finished(self, generation: int, keyframes):\n"
        "        if generation != self._keyframe_scan_generation:\n"
        "            return\n\n",
        "    def on_keyframe_scan_finished(self, generation: int, keyframes):\n"
        "        if generation != self._keyframe_scan_generation:\n"
        "            return\n\n"
        "        self._keyframe_progress_show_timer.stop()\n"
        "        self._hide_task_progress(\"keyframes\")\n",
        "finish keyframe dialog",
    )
    text = replace_once(
        text,
        "    def on_keyframe_scan_failed(self, generation: int, error: str):\n"
        "        if generation != self._keyframe_scan_generation:\n"
        "            return\n\n",
        "    def on_keyframe_scan_failed(self, generation: int, error: str):\n"
        "        if generation != self._keyframe_scan_generation:\n"
        "            return\n\n"
        "        self._keyframe_progress_show_timer.stop()\n"
        "        self._hide_task_progress(\"keyframes\")\n",
        "fail keyframe dialog",
    )

    # Ensure the exporter exists before the focused dialog exposes Cancel.
    text = replace_once(
        text,
        "        ffmpeg, ffprobe = tools\n"
        "        self.set_export_busy(True)\n\n"
        "        self.exporter = LosslessExporter(\n",
        "        ffmpeg, ffprobe = tools\n\n"
        "        self.exporter = LosslessExporter(\n",
        "move export busy after exporter construction part 1",
    )
    text = replace_once(
        text,
        "            language=self.language,\n"
        "        )\n\n"
        "        self.export_thread = threading.Thread(\n",
        "            language=self.language,\n"
        "        )\n\n"
        "        self.set_export_busy(True)\n"
        "        self.export_thread = threading.Thread(\n",
        "move export busy after exporter construction part 2",
    )

    # ---- shared progress controller + export mode ----
    old_progress_methods = '''    def _set_progress_visible(self, visible: bool):
        # Do not call QWidget.setVisible(): that would remove the progress bar
        # from the layout and make the whole window jump vertically.
        if visible:
            self.progress.setStyleSheet("")
        else:
            self.progress.setStyleSheet(
                """
                QProgressBar {
                    background: transparent;
                    border: 1px solid transparent;
                    color: transparent;
                }
                QProgressBar::chunk {
                    background: transparent;
                }
                """
            )

    def set_export_busy(self, busy: bool):
        self._export_busy = bool(busy)
        self._set_progress_visible(self._export_busy)

        if self._export_busy:
            self.progress.setValue(0)
            if self.taskbar_progress:
                self.taskbar_progress.start()
        else:
            if self.taskbar_progress:
                self.taskbar_progress.clear()

        self._update_ui_state()

'''
    new_progress_methods = '''    def _show_task_progress(
        self,
        owner: str,
        *,
        title: str,
        text: str,
        percent: int | None = 0,
        hint: str = "",
        cancellable: bool = False,
        allow_hide: bool = True,
        focus: bool = False,
    ):
        self._task_progress_owner = owner
        self.task_progress_dialog.begin(
            window_title=f"{APP_NAME} — {title}",
            title=title,
            text=text,
            percent=percent,
            hint=hint,
            cancel_text=self._t("cancel_export"),
            cancellable=cancellable,
            allow_hide=allow_hide,
            focus=focus,
        )

    def _update_task_progress(
        self,
        owner: str,
        *,
        percent: int | None = None,
        text: str | None = None,
    ):
        if self._task_progress_owner != owner:
            return
        self.task_progress_dialog.update_task(percent=percent, text=text)

    def _hide_task_progress(self, owner: str):
        if self._task_progress_owner != owner:
            return
        self.task_progress_dialog.finish()
        self._task_progress_owner = ""

    def _show_keyframe_progress_dialog(self):
        thread = self.keyframe_scan_thread
        if (
            self._export_busy
            or not self.input_path
            or thread is None
            or not thread.is_alive()
        ):
            return
        self._show_task_progress(
            "keyframes",
            title=self._t("task_keyframe_title"),
            text=self._t(
                "keyframe_scan_progress",
                percent=self._keyframe_scan_percent,
            ),
            percent=self._keyframe_scan_percent,
            hint=self._t("task_keyframe_hint"),
            cancellable=False,
            allow_hide=True,
            focus=False,
        )

    def set_export_busy(self, busy: bool):
        self._export_busy = bool(busy)

        if self._export_busy:
            self._keyframe_progress_show_timer.stop()
            self._show_task_progress(
                "export",
                title=self._t("task_export_title"),
                text=self._t("task_export_preparing"),
                percent=0,
                cancellable=True,
                allow_hide=False,
                focus=True,
            )
            if self.taskbar_progress:
                self.taskbar_progress.start()
        else:
            self._hide_task_progress("export")
            if self.taskbar_progress:
                self.taskbar_progress.clear()

        self._update_ui_state()

        # Export takes visual priority if both workers overlap. Once it ends,
        # resume the non-blocking scan dialog if the background scan is alive.
        if not self._export_busy:
            self._show_keyframe_progress_dialog()

'''
    text = replace_once(
        text,
        old_progress_methods,
        new_progress_methods,
        "task progress controller",
    )

    text = replace_once(
        text,
        "        self.cancel_export_btn.setEnabled(False)\n"
        "        self.statusBar().showMessage(self._t(\"stopping_export\"))\n"
        "        self.exporter.cancel()\n",
        "        self.task_progress_dialog.set_cancel_enabled(False)\n"
        "        self._update_task_progress(\n"
        "            \"export\",\n"
        "            text=self._t(\"stopping_export\"),\n"
        "        )\n"
        "        self.statusBar().showMessage(self._t(\"stopping_export\"))\n"
        "        self.exporter.cancel()\n",
        "dialog export cancellation",
    )

    text = replace_once(
        text,
        "    def on_export_progress(self, pct: int, text: str):\n"
        "        self.progress.setValue(pct)\n"
        "        if self.taskbar_progress:\n",
        "    def on_export_progress(self, pct: int, text: str):\n"
        "        self._update_task_progress(\n"
        "            \"export\",\n"
        "            percent=pct,\n"
        "            text=text,\n"
        "        )\n"
        "        if self.taskbar_progress:\n",
        "export dialog progress",
    )

    # Make sure a still-visible modeless dialog does not survive application close.
    text = replace_once(
        text,
        "        if self.taskbar_progress:\n"
        "            self.taskbar_progress.close()\n"
        "            self.taskbar_progress = None\n\n"
        "        event.accept()\n",
        "        self._keyframe_progress_show_timer.stop()\n"
        "        self.task_progress_dialog.finish()\n"
        "        self._task_progress_owner = \"\"\n\n"
        "        if self.taskbar_progress:\n"
        "            self.taskbar_progress.close()\n"
        "            self.taskbar_progress = None\n\n"
        "        event.accept()\n",
        "close task progress dialog",
    )

    target.write_text(text, encoding="utf-8")
    print("Integrated 0.5.x Task Progress Dialog into vfr_fastcut.py")
    print("Next: python -m py_compile .\\vfr_fastcut.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
