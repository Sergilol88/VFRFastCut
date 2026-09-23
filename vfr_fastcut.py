# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sergilol

from __future__ import annotations

import bisect
import ctypes
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QLocale, QObject, QEvent, QRectF, QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPainter, QPen, QTransform
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollBar,
    QSlider,
    QSizePolicy,
    QStatusBar,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "VFR FastCut"
APP_VERSION = "0.2.36"

SUPPORTED_VIDEO_SUFFIXES = frozenset({
    ".mp4",
    ".mov",
    ".m4v",
    ".mkv",
    ".webm",
    ".ts",
    ".mts",
    ".m2ts",
    ".avi",
    ".flv",
    ".mpg",
    ".mpeg",
    ".wmv",
})

VIDEO_OUTPUT_SUFFIXES = frozenset({
    ".mp4",
    ".mov",
    ".mkv",
})

# Short enough to make keyboard seeking feel responsive, while still giving
# Qt Multimedia a small quiet window to avoid the seek-related audio crackle.
SEEK_SETTLE_MS = 220

# Never manually seek QMediaPlayer to the exact EOF timestamp. On some
# Qt/Windows/VRR combinations that can transition the video output through
# EndOfMedia and briefly recreate/repaint the video surface.
SAFE_EOF_MARGIN_SECONDS = 0.100

# Preferred initial preview size. The window itself is calculated around the
# real Qt layout after it is shown, so controls/status bars are accounted for.
INITIAL_PREVIEW_WIDTH = 960
INITIAL_PREVIEW_HEIGHT = 540

PLAY_BUTTON_STYLE = """
QPushButton {
    background-color: #3f607a;
    color: white;
    font-weight: 500;
    padding: 6px 10px;
    border: 1px solid #36536a;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #4b718f;
}
QPushButton:pressed {
    background-color: #304b61;
}
QPushButton:disabled {
    background-color: #777777;
    color: #d0d0d0;
    border-color: #6a6a6a;
}
"""

EXPORT_BUTTON_STYLE = """
QPushButton {
    background-color: #2e7d32;
    color: white;
    font-weight: 600;
    padding: 6px 12px;
    border: 1px solid #256628;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #388e3c;
}
QPushButton:pressed {
    background-color: #1b5e20;
}
QPushButton:disabled {
    background-color: #777777;
    color: #d0d0d0;
    border-color: #6a6a6a;
}
"""

SPLIT_BUTTON_STYLE = """
QPushButton {
    background-color: #a66a00;
    color: white;
    font-weight: 600;
    padding: 6px 12px;
    border: 1px solid #8a5700;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #bf7a00;
}
QPushButton:pressed {
    background-color: #7d4f00;
}
QPushButton:disabled {
    background-color: #777777;
    color: #d0d0d0;
    border-color: #6a6a6a;
}
"""



SUPPORTED_LANGUAGES = ("en", "ru")

UI_TEXT = {
    "en": {
        "timeline_empty": "Open a video to show the timeline",
        "selection_none": "No segment selected",
        "open_video": "Open video [Ctrl+O]",
        "reset": "Reset [Ctrl+N]",
        "reset_tip": "Reset the current project",
        "play": "▶ Play [Space]",
        "pause": "❚❚ Pause [Space]",
        "prev_cut": "◀ Previous cut [Q]",
        "next_cut": "Next cut [E] ▶",
        "mute": "Mute [M]",
        "unmute": "Unmute [M]",
        "split": "Split [S]",
        "delete": "Delete [Delete]",
        "restore": "Restore",
        "undo": "Undo [Ctrl+Z]",
        "export_fragment": "Export segment",
        "export_fragment_tip": "Export only the selected segment without re-encoding",
        "export_video": "Export video",
        "export_video_tip": "On: keep the video stream. Off: export only selected audio streams.",
        "export_audio": "Export audio",
        "export_audio_tip": "On: keep all audio streams. Off: export video only.",
        "help": "Help [F1]",
        "help_tip": "Open help and keyboard shortcuts",
        "language_tip": "Interface language",
        "cancel_export": "Cancel export",
        "timeline": "Timeline",
        "volume": "Volume",
        "ready": "Ready.",
        "project_reset": "Project reset.",
        "cannot_reset_export": "The project cannot be reset while export is running.",
        "open_dialog": "Open video",
        "video_filter": "Video (*.mp4 *.mov *.m4v *.mkv *.webm *.ts *.mts *.m2ts *.avi *.flv *.mpg *.mpeg *.wmv);;All files (*.*)",
        "wait_export": "Wait for the export to finish or cancel it.",
        "file_not_found": "File not found.",
        "unsupported_type": "This file type is not supported yet.\n\nSupported: MP4, MOV, M4V, MKV, WebM, TS, MTS, M2TS, AVI, FLV, MPG/MPEG, WMV.",
        "already_open": "This file is already open: {name}",
        "opened": "Opened: {name}",
        "previous_cut_status": "Previous cut: {time}",
        "next_cut_status": "Next cut: {time}",
        "state_deleted": "DELETED",
        "state_kept": "kept",
        "segment_info": "Segment {number}: {start} → {end} ({duration}) • {state}",
        "playhead_boundary": "The playhead is already on a segment boundary.",
        "split_status": "Split: {time}",
        "marked_deleted": "Segment marked for deletion.",
        "restored": "Segment restored.",
        "help_title": "Help",
        "close": "Close",
        "tools_missing_both": "ffmpeg.exe and ffprobe.exe",
        "tools_missing_ffmpeg": "ffmpeg.exe",
        "tools_missing": "Could not find {missing}.\n\nPlace the files in:\n  ffmpeg\\bin\\ next to the app\nor use C:\\ffmpeg\\bin\\.",
        "cannot_overwrite_source": "The source file cannot be overwritten.",
        "file_filter_av": "MP4 (*.mp4);;MOV (*.mov);;MKV (*.mkv);;All files (*.*)",
        "export_selected_dialog": "Export selected segment",
        "stopping_export": "Stopping export…",
        "export_finished_status": "Lossless export finished.",
        "export_finished_title": "Lossless export finished.",
        "output_file": "File:\n{output}",
        "open_result_folder": "Open result folder",
        "folder_open_failed": "Could not open the result folder.",
        "export_cancelled": "Export cancelled.",
        "export_error_status": "Export error.",
        "export_failed": "Export failed.\n\n{error}",
        "export_no_streams": "No streams selected for export.",
        "scan_keyframes": "Scanning keyframes…",
        "ffprobe_scan_failed": "ffprobe could not scan keyframes.",
        "no_keyframes": "Could not find keyframes in the video stream.",
        "video_excluded": "Video: excluded from export.",
        "audio_excluded": "Audio: excluded from export.",
        "audio_preserved": "Audio: stream copy without re-encoding; source codec and parameters preserved.",
        "keyframe_shift": "Maximum boundary adjustment to a keyframe: {shift:.3f} s.",
        "audio_boundaries": "Audio boundaries: packet-based, without video keyframe snapping.",
        "copying_file": "Copying file without re-encoding…",
        "done": "Done.",
        "direct_remux_note": "Lossless stream copy finished.\nNo segments were deleted — direct remux completed without temporary parts.",
        "no_ranges": "There are no segments to export.",
        "full_range_note": "Lossless stream copy finished.\nThe selected full range was exported.",
        "no_ranges_after_snap": "No exportable segments remain after keyframe snapping.",
        "copying_range": "Copying segment: {start} → {end}",
        "copying_range_n": "Copying segment {index}/{count}: {start} → {end}",
        "single_range_note": "Lossless stream copy finished.\nSegments: 1\n",
        "joining_ranges": "Joining segments without re-encoding…",
        "multi_range_note": "Lossless stream copy finished.\nSegments: {count}\n",
        "language_changed": "Interface language changed to English.",
    },
    "ru": {
        "timeline_empty": "Открой видео, чтобы появился таймлайн",
        "selection_none": "Фрагмент не выбран",
        "open_video": "Открыть видео [Ctrl+O]",
        "reset": "Сброс [Ctrl+N]",
        "reset_tip": "Сбросить текущий проект",
        "play": "▶ Play [Space]",
        "pause": "❚❚ Pause [Space]",
        "prev_cut": "◀ Пред. разрез [Q]",
        "next_cut": "След. разрез [E] ▶",
        "mute": "Mute [M]",
        "unmute": "Unmute [M]",
        "split": "Разрезать [S]",
        "delete": "Удалить [Delete]",
        "restore": "Восстановить",
        "undo": "Undo [Ctrl+Z]",
        "export_fragment": "Экспорт фрагмента",
        "export_fragment_tip": "Экспортировать только выбранный фрагмент без перекодировки",
        "export_video": "Экспорт видео",
        "export_video_tip": "Включено: сохранить видеоряд. Выключено: экспортировать только выбранные аудиодорожки.",
        "export_audio": "Экспорт звука",
        "export_audio_tip": "Включено: сохранить все аудиодорожки. Выключено: экспортировать только видеоряд.",
        "help": "Справка [F1]",
        "help_tip": "Открыть справку и список горячих клавиш",
        "language_tip": "Язык интерфейса",
        "cancel_export": "Отмена экспорта",
        "timeline": "Таймлайн",
        "volume": "Громкость",
        "ready": "Готово.",
        "project_reset": "Проект сброшен.",
        "cannot_reset_export": "Нельзя сбросить проект во время экспорта.",
        "open_dialog": "Открыть видео",
        "video_filter": "Видео (*.mp4 *.mov *.m4v *.mkv *.webm *.ts *.mts *.m2ts *.avi *.flv *.mpg *.mpeg *.wmv);;Все файлы (*.*)",
        "wait_export": "Дождись окончания экспорта или отмени его.",
        "file_not_found": "Файл не найден.",
        "unsupported_type": "Этот тип файла пока не поддерживается.\n\nПоддерживаются: MP4, MOV, M4V, MKV, WebM, TS, MTS, M2TS, AVI, FLV, MPG/MPEG, WMV.",
        "already_open": "Этот файл уже открыт: {name}",
        "opened": "Открыт: {name}",
        "previous_cut_status": "Предыдущий разрез: {time}",
        "next_cut_status": "Следующий разрез: {time}",
        "state_deleted": "УДАЛЁН",
        "state_kept": "оставляем",
        "segment_info": "Фрагмент {number}: {start} → {end} ({duration}) • {state}",
        "playhead_boundary": "Playhead уже находится на границе фрагмента.",
        "split_status": "Разрез: {time}",
        "marked_deleted": "Фрагмент помечен на удаление.",
        "restored": "Фрагмент восстановлен.",
        "help_title": "Справка",
        "close": "Закрыть",
        "tools_missing_both": "ffmpeg.exe и ffprobe.exe",
        "tools_missing_ffmpeg": "ffmpeg.exe",
        "tools_missing": "Не найден(ы) {missing}.\n\nПоложи файлы в:\n  ffmpeg\\bin\\ рядом с программой\nили используй C:\\ffmpeg\\bin\\.",
        "cannot_overwrite_source": "Нельзя перезаписывать исходный файл.",
        "file_filter_av": "MP4 (*.mp4);;MOV (*.mov);;MKV (*.mkv);;Все файлы (*.*)",
        "export_selected_dialog": "Экспорт выбранного фрагмента",
        "stopping_export": "Останавливаю экспорт…",
        "export_finished_status": "Lossless export завершён.",
        "export_finished_title": "Lossless export завершён.",
        "output_file": "Файл:\n{output}",
        "open_result_folder": "Открыть папку с результатом",
        "folder_open_failed": "Не удалось открыть папку с результатом.",
        "export_cancelled": "Экспорт отменён.",
        "export_error_status": "Ошибка экспорта.",
        "export_failed": "Экспорт не удался.\n\n{error}",
        "export_no_streams": "Не выбран ни один поток для экспорта.",
        "scan_keyframes": "Сканирую keyframes…",
        "ffprobe_scan_failed": "ffprobe не смог просканировать keyframes.",
        "no_keyframes": "Не удалось найти keyframes в видеопотоке.",
        "video_excluded": "Видео: исключено из экспорта.",
        "audio_excluded": "Аудио: исключено из экспорта.",
        "audio_preserved": "Аудио: stream copy без перекодирования; исходный кодек и параметры сохранены.",
        "keyframe_shift": "Максимальная коррекция границы до keyframe: {shift:.3f} сек.",
        "audio_boundaries": "Границы аудио: по аудиопакетам, без keyframe-привязки.",
        "copying_file": "Копирую файл без перекодирования…",
        "done": "Готово.",
        "direct_remux_note": "Lossless stream copy завершён.\nФрагменты не удалялись — выполнена прямая перепаковка без временных частей.",
        "no_ranges": "Нет фрагментов для экспорта.",
        "full_range_note": "Lossless stream copy завершён.\nЭкспортирован выбранный полный диапазон.",
        "no_ranges_after_snap": "После привязки к keyframes не осталось экспортируемых фрагментов.",
        "copying_range": "Копирую фрагмент: {start} → {end}",
        "copying_range_n": "Копирую фрагмент {index}/{count}: {start} → {end}",
        "single_range_note": "Lossless stream copy завершён.\nФрагментов: 1\n",
        "joining_ranges": "Склеиваю фрагменты без перекодирования…",
        "multi_range_note": "Lossless stream copy завершён.\nФрагментов: {count}\n",
        "language_changed": "Язык интерфейса переключён на русский.",
    },
}

HELP_HTML = {
    "en": """
<h2>VFR FastCut — Help</h2>
<h3>Opening and project</h3>
<ul>
  <li><b>Open video [Ctrl+O]</b> — select a video file.</li>
  <li><b>Supported input containers:</b> MP4, MOV, M4V, MKV, WebM, TS/MTS/M2TS, AVI, FLV, MPG/MPEG, WMV.</li>
  <li><b>Drag & Drop</b> — drop a supported video almost anywhere in the window.</li>
  <li><b>Reset [Ctrl+N]</b> — clear the current project.</li>
  <li>Opening a different file automatically resets the current project.</li>
  <li>Opening the same file again preserves cuts and Undo history.</li>
  <li>The language selector in the top-right switches English / Russian and saves the choice for future launches.</li>
</ul>
<h3>Playback and navigation</h3>
<ul>
  <li><b>Play / Pause [Space]</b> — playback control.</li>
  <li><b>Mute [M]</b> — mute preview audio.</li>
  <li><b>← / →</b> — seek by one second.</li>
  <li><b>Q / E</b> — previous / next cut. Falls back to the start / end of the video.</li>
  <li>Click or drag the <b>upper time ruler</b> to seek / scrub.</li>
  <li>Click the <b>lower timeline track</b> to select a segment without moving the playhead.</li>
  <li>Mouse wheel over the timeline — horizontal scroll.</li>
  <li><b>Ctrl + wheel</b> — zoom around the cursor.</li>
</ul>
<h3>Editing</h3>
<ul>
  <li><b>Split [S]</b> — create a cut at the playhead.</li>
  <li><b>Delete [Delete]</b> — exclude the selected segment from the main export.</li>
  <li><b>Restore</b> — restore a deleted segment.</li>
  <li><b>Undo [Ctrl+Z]</b> / <b>Redo [Ctrl+Y]</b> — undo / redo an edit.</li>
</ul>
<h3>Export</h3>
<ul>
  <li><b>Lossless Export</b> — combine all kept segments into one file without re-encoding.</li>
  <li><b>Export segment</b> — save only the selected segment.</li>
  <li>The selected segment can be exported even if it is marked for deletion in the main edit.</li>
  <li><b>Export video</b> and <b>Export audio</b> are enabled by default.</li>
  <li>You can export video + audio, video only, or audio only.</li>
  <li><b>Video output containers:</b> MP4, MOV, MKV. Other input containers default to MKV.</li>
  <li>If both stream checkboxes are disabled, export buttons are disabled.</li>
  <li>Audio-only export uses <b>MKA</b> and preserves the source audio streams via stream copy.</li>
  <li>Export can be cancelled while it is running.</li>
  <li>After a successful export you can open the result folder.</li>
</ul>
<h3>Important lossless limitation</h3>
<p>VFR FastCut uses FFmpeg stream copy (<b>-c copy</b>). When video is exported, cut boundaries are snapped to keyframes and may differ slightly from the requested position. Audio-only export does not require video keyframe snapping and cuts on audio packet boundaries.</p>
<h3>Hotkeys</h3>
<table cellspacing="4" cellpadding="3">
<tr><td><b>Ctrl+O</b></td><td>Open video</td></tr>
<tr><td><b>Ctrl+N</b></td><td>Reset project</td></tr>
<tr><td><b>Space</b></td><td>Play / Pause</td></tr>
<tr><td><b>M</b></td><td>Mute preview</td></tr>
<tr><td><b>S</b></td><td>Split</td></tr>
<tr><td><b>Delete</b></td><td>Delete selected segment</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
<tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
<tr><td><b>Q</b></td><td>Previous cut</td></tr>
<tr><td><b>E</b></td><td>Next cut</td></tr>
<tr><td><b>← / →</b></td><td>Seek ±1 second</td></tr>
<tr><td><b>F1</b></td><td>Open this help</td></tr>
</table>
""",
    "ru": """
<h2>VFR FastCut — справка</h2>
<h3>Открытие и проект</h3>
<ul>
  <li><b>Открыть видео [Ctrl+O]</b> — выбрать видео через Проводник.</li>
  <li><b>Поддерживаемые входные контейнеры:</b> MP4, MOV, M4V, MKV, WebM, TS/MTS/M2TS, AVI, FLV, MPG/MPEG, WMV.</li>
  <li><b>Drag & Drop</b> — видео можно бросить почти в любую область окна.</li>
  <li><b>Сброс [Ctrl+N]</b> — очистить текущий проект и начать заново.</li>
  <li>Если открыть другой файл, текущий проект сбрасывается автоматически.</li>
  <li>Повторное открытие того же файла не уничтожает разрезы и Undo.</li>
  <li>Селектор языка справа сверху переключает русский / английский и сохраняет выбор для следующих запусков.</li>
</ul>
<h3>Просмотр и навигация</h3>
<ul>
  <li><b>Play / Pause [Space]</b> — воспроизведение и пауза.</li>
  <li><b>Mute [M]</b> — выключить звук preview.</li>
  <li><b>← / →</b> — переход на 1 секунду назад / вперёд.</li>
  <li><b>Q / E</b> — предыдущий / следующий разрез. Если разреза нет — начало / конец видео.</li>
  <li>Клик или drag по <b>верхней шкале времени</b> — seek / scrub.</li>
  <li>Клик по <b>нижнему таймлайну</b> — выбрать фрагмент, не меняя позицию воспроизведения.</li>
  <li>Колесо мыши над таймлайном — горизонтальный скролл.</li>
  <li><b>Ctrl + колесо</b> — zoom вокруг курсора.</li>
</ul>
<h3>Монтаж</h3>
<ul>
  <li><b>Разрезать [S]</b> — создать разрез в позиции красной линии.</li>
  <li><b>Удалить [Delete]</b> — исключить выбранный фрагмент из общего экспорта.</li>
  <li><b>Восстановить</b> — вернуть удалённый фрагмент.</li>
  <li><b>Undo [Ctrl+Z]</b> / <b>Redo [Ctrl+Y]</b> — отменить / вернуть изменение.</li>
</ul>
<h3>Экспорт</h3>
<ul>
  <li><b>Lossless Export</b> — экспортировать все неудалённые фрагменты в один файл без перекодирования.</li>
  <li><b>Экспорт фрагмента</b> — сохранить только текущий выбранный фрагмент в отдельный файл.</li>
  <li>Экспорт выбранного фрагмента работает независимо от того, отмечен он на удаление или нет.</li>
  <li><b>Экспорт видео</b> и <b>Экспорт звука</b> включены по умолчанию.</li>
  <li>Можно экспортировать видео со звуком, только видео или только звук.</li>
  <li><b>Контейнеры для вывода видео:</b> MP4, MOV, MKV. Для остальных входных контейнеров по умолчанию предлагается MKV.</li>
  <li>Если снять обе галочки, кнопки экспорта становятся недоступны.</li>
  <li>При экспорте только звука используется контейнер <b>MKA</b>; аудиопотоки копируются без перекодирования.</li>
  <li>Во время экспорта можно нажать <b>Отмена экспорта</b>.</li>
  <li>После завершения доступна кнопка <b>Открыть папку с результатом</b>.</li>
</ul>
<h3>Важно о Lossless</h3>
<p>VFR FastCut использует FFmpeg stream copy (<b>-c copy</b>) и не перекодирует потоки. Если экспортируется видео, границы привязываются к keyframes и могут немного отличаться от выбранной позиции. При экспорте только звука keyframe-привязка не нужна: границы идут по аудиопакетам.</p>
<h3>Горячие клавиши</h3>
<table cellspacing="4" cellpadding="3">
<tr><td><b>Ctrl+O</b></td><td>Открыть видео</td></tr>
<tr><td><b>Ctrl+N</b></td><td>Сбросить проект</td></tr>
<tr><td><b>Space</b></td><td>Play / Pause</td></tr>
<tr><td><b>M</b></td><td>Mute preview</td></tr>
<tr><td><b>S</b></td><td>Разрезать</td></tr>
<tr><td><b>Delete</b></td><td>Удалить выбранный фрагмент</td></tr>
<tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
<tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
<tr><td><b>Q</b></td><td>Предыдущий разрез</td></tr>
<tr><td><b>E</b></td><td>Следующий разрез</td></tr>
<tr><td><b>← / →</b></td><td>Seek ±1 секунда</td></tr>
<tr><td><b>F1</b></td><td>Открыть эту справку</td></tr>
</table>
""",
}


def ui_text(language: str, key: str, **kwargs) -> str:
    table = UI_TEXT.get(language, UI_TEXT["en"])
    template = table.get(key, UI_TEXT["en"].get(key, key))
    return template.format(**kwargs)



def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_tool(exe_name: str) -> str:
    base = app_base_dir()
    candidates = [
        base / exe_name,
        base / "ffmpeg" / "bin" / exe_name,
        base / "tools" / "ffmpeg-minimal" / "runtime" / exe_name,
        Path(r"C:\ffmpeg\bin") / exe_name,
    ]

    from_path = shutil.which(Path(exe_name).stem)
    if from_path:
        candidates.append(Path(from_path))

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return ""


def find_app_icon() -> str:
    candidates = [
        app_base_dir() / "VFRFastCut.ico",
        Path(__file__).resolve().parent / "VFRFastCut.ico",
    ]

    # PyInstaller onefile/onedir may expose bundled data through _MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "VFRFastCut.ico")

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return ""


class WindowsTaskbarProgress:
    """Minimal Windows 7+ taskbar progress wrapper using ITaskbarList3.

    No pywin32/comtypes dependency is required.
    On non-Windows platforms every method is a harmless no-op.
    """

    TBPF_NOPROGRESS = 0x0
    TBPF_NORMAL = 0x2

    def __init__(self, hwnd: int):
        self.hwnd = int(hwnd)
        self._ptr = None
        self._ole32 = None
        self._com_initialized = False

        if sys.platform != "win32" or not self.hwnd:
            return

        try:
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", ctypes.c_ubyte * 8),
                ]

                @classmethod
                def from_string(cls, value: str):
                    import uuid
                    u = uuid.UUID(value)
                    b = u.bytes_le
                    return cls(
                        int.from_bytes(b[0:4], "little"),
                        int.from_bytes(b[4:6], "little"),
                        int.from_bytes(b[6:8], "little"),
                        (ctypes.c_ubyte * 8)(*b[8:16]),
                    )

            self._ole32 = ctypes.OleDLL("ole32")

            # Only S_OK (0) and S_FALSE (1) require a matching CoUninitialize.
            # RPC_E_CHANGED_MODE means COM is already initialized differently;
            # CoCreateInstance can still be attempted, but we must not uninitialize it.
            coinit_hr = self._ole32.CoInitialize(None)
            self._com_initialized = coinit_hr in (0, 1)

            CLSID_TaskbarList = GUID.from_string(
                "56FDF344-FD6D-11D0-958A-006097C9A090"
            )
            IID_ITaskbarList3 = GUID.from_string(
                "EA1AFB91-9E28-4B86-90E9-9E9F8A5EEA84"
            )

            ptr = ctypes.c_void_p()
            CLSCTX_INPROC_SERVER = 0x1

            hr = self._ole32.CoCreateInstance(
                ctypes.byref(CLSID_TaskbarList),
                None,
                CLSCTX_INPROC_SERVER,
                ctypes.byref(IID_ITaskbarList3),
                ctypes.byref(ptr),
            )
            if hr != 0 or not ptr.value:
                return

            self._ptr = ptr
            self._call_void(3)  # HrInit
        except Exception:
            self._ptr = None

    def _method(self, index: int, restype, *argtypes):
        if not self._ptr:
            return None

        vtable_ptr = ctypes.cast(
            self._ptr,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)),
        )
        fn_addr = vtable_ptr.contents[index]
        if not fn_addr:
            return None

        prototype = ctypes.WINFUNCTYPE(
            restype,
            ctypes.c_void_p,
            *argtypes,
        )
        return prototype(fn_addr)

    def _call_void(self, index: int):
        try:
            fn = self._method(index, ctypes.c_long)
            if fn:
                fn(self._ptr)
        except Exception:
            pass

    def set_state(self, state: int):
        if not self._ptr:
            return
        try:
            from ctypes import wintypes
            fn = self._method(
                10,  # ITaskbarList3::SetProgressState
                ctypes.c_long,
                wintypes.HWND,
                ctypes.c_uint,
            )
            if fn:
                fn(self._ptr, self.hwnd, int(state))
        except Exception:
            pass

    def set_value(self, value: int, total: int = 100):
        if not self._ptr:
            return
        try:
            from ctypes import wintypes
            fn = self._method(
                9,  # ITaskbarList3::SetProgressValue
                ctypes.c_long,
                wintypes.HWND,
                ctypes.c_ulonglong,
                ctypes.c_ulonglong,
            )
            if fn:
                fn(
                    self._ptr,
                    self.hwnd,
                    max(0, int(value)),
                    max(1, int(total)),
                )
        except Exception:
            pass

    def start(self):
        self.set_state(self.TBPF_NORMAL)
        self.set_value(0, 100)

    def update(self, percent: int):
        self.set_value(max(0, min(100, int(percent))), 100)

    def clear(self):
        self.set_state(self.TBPF_NOPROGRESS)

    def close(self):
        try:
            self.clear()
        except Exception:
            pass

        if self._ptr:
            try:
                # IUnknown::Release = vtable index 2.
                fn = self._method(2, ctypes.c_ulong)
                if fn:
                    fn(self._ptr)
            except Exception:
                pass
            self._ptr = None

        if self._com_initialized and self._ole32:
            try:
                self._ole32.CoUninitialize()
            except Exception:
                pass
            self._com_initialized = False


def fmt_time(seconds: float, show_ms: bool = True) -> str:
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    ms = int(round((seconds - whole) * 1000))
    if ms == 1000:
        whole += 1
        ms = 0
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)

    if h > 0:
        base = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        base = f"{m:02d}:{s:02d}"

    if show_ms:
        return f"{base}.{ms:03d}"
    return base


@dataclass
class Segment:
    start: float
    end: float
    deleted: bool = False

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def clone_segments(segments: list[Segment]) -> list[Segment]:
    """Fast value-copy for undo/redo/export snapshots."""
    return [
        Segment(seg.start, seg.end, seg.deleted)
        for seg in segments
    ]



class SafePreviewWidget(QWidget):
    """Raster preview that avoids QVideoWidget/native video surfaces.

    QMediaPlayer keeps its normal Qt Multimedia decode path. Decoded frames are
    received through QVideoSink, converted to QImage and painted through the
    regular QWidget backing store. This deliberately avoids the dedicated
    native/video-surface presentation path that can interact badly with
    VRR/G-SYNC/MPO on some Windows/NVIDIA configurations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = QImage()

        self.video_sink = QVideoSink(self)
        self.video_sink.videoFrameChanged.connect(self._on_video_frame)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

    def clear_frame(self):
        if self._image.isNull():
            return
        self._image = QImage()
        self.update()

    def _on_video_frame(self, frame):
        if not frame.isValid():
            self.clear_frame()
            return

        image = frame.toImage()
        if image.isNull():
            return

        rotation = getattr(frame.rotation(), "value", 0)
        if rotation:
            transform = QTransform()
            transform.rotate(float(rotation))
            image = image.transformed(
                transform,
                Qt.TransformationMode.FastTransformation,
            )

        if frame.mirrored():
            image = image.mirrored(True, False)

        self._image = image
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        if self._image.isNull() or self.width() <= 0 or self.height() <= 0:
            return

        image_size = self._image.size()
        target_size = image_size.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

        x = (self.width() - target_size.width()) / 2.0
        y = (self.height() - target_size.height()) / 2.0
        target = QRectF(
            x,
            y,
            target_size.width(),
            target_size.height(),
        )

        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform,
            False,
        )
        painter.drawImage(target, self._image)


class TimelineWidget(QWidget):
    seekRequested = Signal(float)
    segmentSelected = Signal(int)
    viewChanged = Signal(float, float)  # offset, visible duration

    RULER_H = 50
    TRACK_Y = 58
    TRACK_H = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 0.0
        self.position = 0.0
        self.segments: list[Segment] = []
        self.selected_index = -1

        self.zoom = 1.0
        self.max_zoom = 500.0
        self.offset = 0.0

        # Mouse interaction is intentionally split:
        # ruler = seek/scrub, video track = segment selection only.
        self._dragging_ruler = False
        self.empty_text = UI_TEXT["en"]["timeline_empty"]

        self.setMinimumHeight(114)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

    # ---------- timeline view ----------

    def set_empty_text(self, text: str):
        if self.empty_text == text:
            return
        self.empty_text = text
        if self.duration <= 0:
            self.update()

    @property
    def visible_duration(self) -> float:
        if self.duration <= 0:
            return 0.0
        return max(0.05, self.duration / self.zoom)

    @property
    def max_offset(self) -> float:
        return max(0.0, self.duration - self.visible_duration)

    def set_state(
        self,
        duration: float,
        segments: list[Segment],
        position: float,
        selected_index: int,
    ):
        old_duration = self.duration
        old_offset = self.offset
        old_visible = self.visible_duration

        self.duration = max(0.0, duration)
        self.segments = segments
        self.position = position
        self.selected_index = selected_index

        if old_duration <= 0 < self.duration:
            self.zoom = 1.0
            self.offset = 0.0

        self.offset = max(0.0, min(self.offset, self.max_offset))
        self.update()

        # Selection/editing changes do not require a scrollbar rebuild.
        # Emit only when the actual viewport geometry changed.
        if (
            abs(self.duration - old_duration) > 1e-9
            or abs(self.offset - old_offset) > 1e-9
            or abs(self.visible_duration - old_visible) > 1e-9
        ):
            self._emit_view()

    def set_position(self, position: float):
        self.position = max(0.0, min(self.duration, position))
        self.update()

    def set_offset(self, seconds: float, emit: bool = False):
        self.offset = max(0.0, min(float(seconds), self.max_offset))
        self.update()
        if emit:
            self._emit_view()

    def set_zoom(self, new_zoom: float, anchor_time: Optional[float] = None):
        if self.duration <= 0:
            return

        new_zoom = max(1.0, min(self.max_zoom, float(new_zoom)))
        if abs(new_zoom - self.zoom) < 1e-9:
            return

        if anchor_time is None:
            anchor_time = self.offset + self.visible_duration / 2.0

        old_visible = self.visible_duration
        anchor_ratio = 0.5
        if old_visible > 0:
            anchor_ratio = (anchor_time - self.offset) / old_visible
            anchor_ratio = max(0.0, min(1.0, anchor_ratio))

        self.zoom = new_zoom
        new_visible = self.visible_duration
        self.offset = anchor_time - anchor_ratio * new_visible
        self.offset = max(0.0, min(self.offset, self.max_offset))

        self.update()
        self._emit_view()

    def zoom_in(self):
        self.set_zoom(self.zoom * 1.6, self.position if self.duration else None)

    def zoom_out(self):
        self.set_zoom(self.zoom / 1.6, self.position if self.duration else None)

    def zoom_reset(self):
        if self.duration <= 0:
            return

        if abs(self.zoom - 1.0) < 1e-9 and abs(self.offset) < 1e-9:
            return

        self.zoom = 1.0
        self.offset = 0.0
        self.update()
        self._emit_view()

    def scroll_by(self, seconds: float):
        self.set_offset(self.offset + seconds, emit=True)

    def ensure_time_visible(self, t: float, margin_ratio: float = 0.08):
        if self.duration <= 0 or self.zoom <= 1.0:
            return
        vis = self.visible_duration
        left_margin = self.offset + vis * margin_ratio
        right_margin = self.offset + vis * (1.0 - margin_ratio)
        if t < left_margin:
            self.set_offset(t - vis * margin_ratio, emit=True)
        elif t > right_margin:
            self.set_offset(t - vis * (1.0 - margin_ratio), emit=True)

    def _emit_view(self):
        self.viewChanged.emit(self.offset, self.visible_duration)

    # ---------- coordinate helpers ----------

    def _time_from_x(self, x: float) -> float:
        if self.duration <= 0 or self.width() <= 1:
            return 0.0
        ratio = max(0.0, min(1.0, x / self.width()))
        return max(
            0.0,
            min(self.duration, self.offset + ratio * self.visible_duration),
        )

    def _x_from_time(self, t: float) -> float:
        if self.visible_duration <= 0:
            return 0.0
        return ((t - self.offset) / self.visible_duration) * self.width()

    def _segment_at(self, t: float) -> int:
        last_index = len(self.segments) - 1
        for i, seg in enumerate(self.segments):
            if seg.start > t:
                break
            if seg.start <= t < seg.end or (
                i == last_index and abs(t - seg.end) < 1e-6
            ):
                return i
        return -1

    # ---------- mouse / wheel ----------

    def mousePressEvent(self, event):
        if self.duration <= 0:
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        x = event.position().x()
        y = event.position().y()
        t = self._time_from_x(x)

        # Upper time ruler: move/scrub the playback playhead.
        if 0 <= y <= self.RULER_H:
            self._dragging_ruler = True
            self.seekRequested.emit(t)
            event.accept()
            return

        # Lower video track: select the segment only.
        # Do NOT move the playback playhead.
        if self.TRACK_Y <= y <= self.TRACK_Y + self.TRACK_H:
            idx = self._segment_at(t)
            if idx >= 0:
                self.segmentSelected.emit(idx)
            event.accept()
            return

        event.ignore()

    def mouseMoveEvent(self, event):
        # Dragging on the ruler scrubs the playback position.
        if (
            self._dragging_ruler
            and event.buttons() & Qt.MouseButton.LeftButton
            and self.duration > 0
        ):
            t = self._time_from_x(event.position().x())
            self.seekRequested.emit(t)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging_ruler = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self.duration <= 0:
            event.ignore()
            return

        delta = event.angleDelta()

        # Native horizontal wheel (e.g. Keychron M5 thumb wheel) = horizontal pan.
        if delta.x() != 0:
            direction = -1 if delta.x() > 0 else 1
            step = max(0.25, self.visible_duration * 0.12)
            self.scroll_by(direction * step)
            event.accept()
            return

        if delta.y() != 0:
            # Ctrl + vertical wheel = zoom around the mouse cursor.
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                anchor = self._time_from_x(event.position().x())
                factor = 1.35 if delta.y() > 0 else 1 / 1.35
                self.set_zoom(self.zoom * factor, anchor)
            else:
                # Regular vertical wheel = horizontal timeline pan.
                direction = -1 if delta.y() > 0 else 1
                step = max(0.25, self.visible_duration * 0.12)
                self.scroll_by(direction * step)

            event.accept()
            return

        event.ignore()

    # ---------- drawing ----------

    @staticmethod
    def _nice_tick_step(visible_duration: float, width: int) -> float:
        if width <= 0:
            return 1.0
        target_ticks = max(4, min(14, width // 100))
        raw = visible_duration / max(1, target_ticks)

        nice = [
            0.05, 0.1, 0.2, 0.5,
            1, 2, 5, 10, 15, 30,
            60, 120, 300, 600, 900, 1800, 3600
        ]
        for step in nice:
            if step >= raw:
                return step
        return nice[-1]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        bg = self.palette().window().color().darker(108)
        painter.fillRect(self.rect(), bg)

        if self.duration <= 0:
            painter.setPen(self.palette().text().color())
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                self.empty_text,
            )
            return

        width = max(1, self.width())
        vis_start = self.offset
        vis_end = min(self.duration, self.offset + self.visible_duration)

        # ---- time ruler ----
        painter.fillRect(
            QRectF(0, 0, width, self.RULER_H),
            self.palette().base().color().darker(112),
        )

        major = self._nice_tick_step(self.visible_duration, width)
        minor = major / 5.0
        first_minor = math.floor(vis_start / minor) * minor

        tick = first_minor
        while tick <= vis_end + minor:
            x = self._x_from_time(tick)
            if -2 <= x <= width + 2:
                is_major = abs((tick / major) - round(tick / major)) < 1e-6
                if is_major:
                    painter.setPen(QPen(QColor(185, 185, 185), 1))
                    painter.drawLine(
                        int(x),
                        self.RULER_H - 24,
                        int(x),
                        self.RULER_H,
                    )
                    label = fmt_time(tick, show_ms=(major < 1.0))
                    painter.drawText(int(x) + 3, 16, label)
                else:
                    painter.setPen(QPen(QColor(105, 105, 105), 1))
                    painter.drawLine(
                        int(x),
                        self.RULER_H - 12,
                        int(x),
                        self.RULER_H,
                    )
            tick += minor

        # ---- video track ----
        track_rect = QRectF(0, self.TRACK_Y, width, self.TRACK_H)
        painter.fillRect(track_rect, self.palette().base().color().darker(105))

        for i, seg in enumerate(self.segments):
            if seg.end <= vis_start:
                continue
            if seg.start >= vis_end:
                break

            draw_start = max(seg.start, vis_start)
            draw_end = min(seg.end, vis_end)
            if draw_end <= draw_start:
                continue

            x1 = self._x_from_time(draw_start)
            x2 = self._x_from_time(draw_end)
            rect = QRectF(x1, self.TRACK_Y, max(1.0, x2 - x1), self.TRACK_H)

            fill = QColor(78, 130, 194) if not seg.deleted else QColor(78, 78, 78)
            painter.fillRect(rect, fill)

            border = (
                QColor(255, 214, 64)
                if i == self.selected_index
                else QColor(35, 35, 35)
            )
            painter.setPen(QPen(border, 2 if i == self.selected_index else 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))

            # visible cut marker at actual requested boundary
            if seg.start > vis_start and seg.start < vis_end:
                bx = self._x_from_time(seg.start)
                painter.setPen(QPen(QColor(25, 25, 25), 1))
                painter.drawLine(int(bx), self.TRACK_Y, int(bx), self.TRACK_Y + self.TRACK_H)

        # ---- playhead ----
        if vis_start <= self.position <= vis_end:
            x = self._x_from_time(self.position)
            painter.setPen(QPen(QColor(235, 65, 65), 2))
            painter.drawLine(int(x), 0, int(x), self.TRACK_Y + self.TRACK_H + 10)


class ExportCancelledError(RuntimeError):
    pass


class ExportSignals(QObject):
    progress = Signal(int, str)
    finished = Signal(str, str)
    failed = Signal(str)
    cancelled = Signal()


class LosslessExporter:
    def __init__(
        self,
        ffmpeg: str,
        ffprobe: str,
        input_path: str,
        output_path: str,
        duration: float,
        segments: list[Segment],
        signals: ExportSignals,
        export_video: bool = True,
        export_audio: bool = True,
        ranges_override: Optional[list[tuple[float, float]]] = None,
        language: str = "en",
    ):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.input_path = input_path
        self.output_path = output_path
        self.duration = duration
        self.segments = segments
        self.signals = signals
        self.export_video = bool(export_video)
        self.export_audio = bool(export_audio)
        self.language = language if language in SUPPORTED_LANGUAGES else "en"
        self.ranges_override = (
            list(ranges_override)
            if ranges_override is not None
            else None
        )

        self._cancel_event = threading.Event()
        self._process_lock = threading.Lock()
        self._active_process: Optional[subprocess.Popen] = None

    def _t(self, key: str, **kwargs) -> str:
        return ui_text(self.language, key, **kwargs)

    def _set_active_process(self, proc: Optional[subprocess.Popen]):
        with self._process_lock:
            self._active_process = proc

    @staticmethod
    def _terminate_and_reap(
        proc: subprocess.Popen,
        timeout: float = 1.0,
    ):
        """Best-effort cleanup for a child process after an unexpected error.

        The UI cancellation path stays non-blocking; this helper is used from
        the worker thread when an exception interrupts normal communicate/wait.
        """
        if proc.poll() is not None:
            return

        try:
            proc.terminate()
            proc.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        try:
            proc.kill()
        except Exception:
            pass

        try:
            proc.wait(timeout=timeout)
        except Exception:
            pass

    @staticmethod
    def _kill_after_grace(
        proc: subprocess.Popen,
        grace_seconds: float = 1.0,
    ):
        try:
            proc.wait(timeout=grace_seconds)
            return
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            return

        if proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

        try:
            proc.wait(timeout=1.0)
        except Exception:
            pass

    def cancel(self):
        self._cancel_event.set()

        with self._process_lock:
            proc = self._active_process

        if not proc or proc.poll() is not None:
            return

        try:
            proc.terminate()
        except Exception:
            pass

        # Never block the Qt GUI while waiting for a child process to die.
        threading.Thread(
            target=self._kill_after_grace,
            args=(proc,),
            daemon=True,
            name="VFRFastCutCancelWatchdog",
        ).start()

    def force_kill(self):
        with self._process_lock:
            proc = self._active_process
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    def _check_cancelled(self):
        if self._cancel_event.is_set():
            raise ExportCancelledError()

    def _run(self, cmd: list[str]) -> None:
        self._check_cancelled()

        # The minimal FFmpeg build intentionally keeps format support small.
        # Do not depend on output-extension auto-detection: select the muxer
        # explicitly for every container VFR FastCut currently exports.
        if cmd:
            output_suffix = Path(str(cmd[-1])).suffix.lower()
            output_format = {
                ".mp4": "mp4",
                ".mov": "mov",
                ".mkv": "matroska",
                ".mka": "matroska",
            }.get(output_suffix)

            if output_format:
                cmd = [
                    *cmd[:-1],
                    "-f", output_format,
                    cmd[-1],
                ]

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        self._set_active_process(proc)

        try:
            _, stderr = proc.communicate()
        except BaseException:
            self._terminate_and_reap(proc)
            raise
        finally:
            self._set_active_process(None)

        if self._cancel_event.is_set():
            raise ExportCancelledError()

        if proc.returncode != 0:
            tail = (stderr or "").strip()[-4000:]
            raise RuntimeError(tail or f"FFmpeg error code {proc.returncode}")

    def _keep_ranges(self) -> list[tuple[float, float]]:
        ranges: list[tuple[float, float]] = []
        for seg in self.segments:
            if seg.deleted or seg.duration <= 0.001:
                continue
            if ranges and abs(ranges[-1][1] - seg.start) < 0.002:
                ranges[-1] = (ranges[-1][0], seg.end)
            else:
                ranges.append((seg.start, seg.end))
        return ranges

    def _scan_keyframes(self, interval: Optional[tuple[float, float]] = None) -> list[float]:
        self._check_cancelled()
        self.signals.progress.emit(3, self._t("scan_keyframes"))

        cmd = [
            self.ffprobe,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_packets",
            "-show_entries", "packet=pts_time,flags",
            "-of", "csv=p=0",
        ]

        if interval is not None:
            start, end = interval
            start = max(0.0, float(start))
            end = min(self.duration, max(start, float(end)))
            cmd += ["-read_intervals", f"{start:.6f}%{end:.6f}"]

        cmd += [self.input_path]

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            bufsize=1,
        )
        self._set_active_process(proc)

        keyframes: list[float] = []
        diagnostic_lines: list[str] = []

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                if self._cancel_event.is_set():
                    break

                stripped = line.strip()
                parts = stripped.split(",")
                if len(parts) < 2:
                    if stripped:
                        diagnostic_lines.append(stripped)
                        diagnostic_lines = diagnostic_lines[-20:]
                    continue

                try:
                    pts = float(parts[0])
                except ValueError:
                    if stripped:
                        diagnostic_lines.append(stripped)
                        diagnostic_lines = diagnostic_lines[-20:]
                    continue

                flags = parts[-1]
                if "K" in flags:
                    keyframes.append(pts)

            if self._cancel_event.is_set():
                try:
                    rc = proc.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    self._terminate_and_reap(proc)
                    rc = proc.returncode if proc.returncode is not None else -1
            else:
                rc = proc.wait()
        except BaseException:
            self._terminate_and_reap(proc)
            raise
        finally:
            self._set_active_process(None)

        self._check_cancelled()

        if rc != 0:
            details = "\n".join(diagnostic_lines[-20:]).strip()
            raise RuntimeError(details or self._t("ffprobe_scan_failed"))

        if not keyframes:
            raise RuntimeError(self._t("no_keyframes"))

        keyframes = sorted(set(k for k in keyframes if k >= 0))
        if interval is None and keyframes[0] > 0.01:
            keyframes.insert(0, 0.0)
        return keyframes

    def _snap_range(
        self, start: float, end: float, keyframes: list[float]
    ) -> Optional[tuple[float, float]]:
        if start <= 0.001:
            snapped_start = 0.0
        else:
            i = bisect.bisect_left(keyframes, start - 1e-6)
            if i >= len(keyframes):
                return None
            snapped_start = keyframes[i]

        if end >= self.duration - 0.001:
            snapped_end = self.duration
        else:
            i = bisect.bisect_right(keyframes, end + 1e-6) - 1
            if i < 0:
                return None
            snapped_end = keyframes[i]

        if snapped_end - snapped_start <= 0.005:
            return None
        return snapped_start, snapped_end

    def _make_staging_output(self, final_output: Path) -> Path:
        suffix = final_output.suffix or Path(self.input_path).suffix or ".mkv"
        temp_file = tempfile.NamedTemporaryFile(
            prefix=".vfr_fastcut_out_",
            suffix=suffix,
            dir=str(final_output.parent),
            delete=False,
        )
        temp_name = temp_file.name
        temp_file.close()

        # Let ffmpeg create the file itself.
        staging = Path(temp_name)
        staging.unlink(missing_ok=True)
        return staging

    @staticmethod
    def _commit_staging_output(staging: Path, final_output: Path):
        staging.replace(final_output)

    def _stream_map_args(self) -> list[str]:
        args: list[str] = []
        if self.export_video:
            args += ["-map", "0:v:0"]
        if self.export_audio:
            args += ["-map", "0:a?"]
        return args

    def _stream_result_note(self) -> str:
        notes: list[str] = []
        if not self.export_video:
            notes.append(self._t("video_excluded"))
        if not self.export_audio:
            notes.append(self._t("audio_excluded"))
        elif not self.export_video:
            notes.append(self._t("audio_preserved"))
        return "" if not notes else "\n" + "\n".join(notes)

    def _boundary_result_note(self, max_shift: float) -> str:
        if self.export_video:
            return self._t("keyframe_shift", shift=max_shift)
        return self._t("audio_boundaries")

    def _build_copy_command(
        self,
        output: Path,
        start: Optional[float] = None,
        end: Optional[float] = None,
    ) -> list[str]:
        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
        ]

        if start is not None and start > 0.001:
            cmd += ["-ss", f"{start:.6f}"]

        cmd += ["-i", self.input_path]

        if start is not None and end is not None:
            cmd += ["-t", f"{max(0.0, end - start):.6f}"]

        cmd += self._stream_map_args()
        cmd += [
            "-map_metadata", "0",
            "-c", "copy",
        ]

        if start is not None and start > 0.001:
            cmd += ["-avoid_negative_ts", "make_zero"]

        if output.suffix.lower() == ".mp4":
            cmd += ["-movflags", "+faststart"]

        cmd += [str(output)]
        return cmd

    def run(self):
        out = Path(self.output_path)
        staging: Optional[Path] = None

        try:
            self._check_cancelled()
            if not self.export_video and not self.export_audio:
                raise RuntimeError(self._t("export_no_streams"))

            out.parent.mkdir(parents=True, exist_ok=True)
            staging = self._make_staging_output(out)

            # Fast path #1: main export with no excluded fragments.
            # No keyframe scan and no temporary segment copies are needed.
            if (
                self.ranges_override is None
                and not any(seg.deleted for seg in self.segments)
            ):
                self.signals.progress.emit(10, self._t("copying_file"))
                self._run(self._build_copy_command(staging))
                self._commit_staging_output(staging, out)
                staging = None

                self.signals.progress.emit(100, self._t("done"))
                self.signals.finished.emit(
                    str(out),
                    self._t("direct_remux_note")
                    + self._stream_result_note(),
                )
                return

            keep = (
                list(self.ranges_override)
                if self.ranges_override is not None
                else self._keep_ranges()
            )
            if not keep:
                raise RuntimeError(self._t("no_ranges"))

            # Explicit full-file range can also skip keyframe scanning.
            if (
                len(keep) == 1
                and keep[0][0] <= 0.001
                and keep[0][1] >= self.duration - 0.001
            ):
                self.signals.progress.emit(10, self._t("copying_file"))
                self._run(self._build_copy_command(staging))
                self._commit_staging_output(staging, out)
                staging = None

                self.signals.progress.emit(100, self._t("done"))
                self.signals.finished.emit(
                    str(out),
                    self._t("full_range_note")
                    + self._stream_result_note(),
                )
                return

            max_shift = 0.0

            if self.export_video:
                scan_interval = (
                    keep[0]
                    if self.ranges_override is not None and len(keep) == 1
                    else None
                )
                keyframes = self._scan_keyframes(scan_interval)
                export_ranges: list[tuple[float, float]] = []

                for range_start, range_end in keep:
                    self._check_cancelled()
                    item = self._snap_range(range_start, range_end, keyframes)
                    if item is None:
                        continue

                    snapped_start, snapped_end = item
                    max_shift = max(
                        max_shift,
                        abs(snapped_start - range_start),
                        abs(snapped_end - range_end),
                    )

                    if (
                        export_ranges
                        and abs(export_ranges[-1][1] - snapped_start) < 0.002
                    ):
                        export_ranges[-1] = (
                            export_ranges[-1][0],
                            snapped_end,
                        )
                    else:
                        export_ranges.append((snapped_start, snapped_end))

                if not export_ranges:
                    raise RuntimeError(self._t("no_ranges_after_snap"))
            else:
                # Audio-only stream copy does not depend on video keyframes.
                export_ranges = list(keep)

            # Fast path #2: one kept range can be written directly to the
            # staged final file. No concat pass is needed.
            if len(export_ranges) == 1:
                range_start, range_end = export_ranges[0]
                self.signals.progress.emit(
                    15,
                    self._t("copying_range", start=fmt_time(range_start), end=fmt_time(range_end)),
                )
                self._run(
                    self._build_copy_command(
                        staging,
                        range_start,
                        range_end,
                    )
                )
                self._commit_staging_output(staging, out)
                staging = None

                self.signals.progress.emit(100, self._t("done"))
                self.signals.finished.emit(
                    str(out),
                    self._t("single_range_note")
                    + self._boundary_result_note(max_shift)
                    + self._stream_result_note(),
                )
                return

            # Multi-range export needs temporary segment files for robust
            # stream-copy concat. Keep them on the same drive as the result.
            with tempfile.TemporaryDirectory(
                prefix=".vfr_fastcut_",
                dir=str(out.parent),
            ) as tmp_str:
                tmp = Path(tmp_str)
                part_paths: list[Path] = []
                count = len(export_ranges)

                for index, (range_start, range_end) in enumerate(export_ranges, start=1):
                    self._check_cancelled()

                    pct = 8 + int((index - 1) / count * 82)
                    self.signals.progress.emit(
                        pct,
                        self._t("copying_range_n", index=index, count=count, start=fmt_time(range_start), end=fmt_time(range_end)),
                    )

                    part = tmp / f"part_{index:04d}{'.mkv' if self.export_video else '.mka'}"
                    part_paths.append(part)

                    cmd = [
                        self.ffmpeg,
                        "-hide_banner",
                        "-loglevel", "error",
                        "-y",
                        "-ss", f"{range_start:.6f}",
                        "-i", self.input_path,
                        "-t", f"{(range_end - range_start):.6f}",
                    ]
                    cmd += self._stream_map_args()
                    cmd += [
                        "-map_metadata", "0",
                        "-c", "copy",
                        "-avoid_negative_ts", "make_zero",
                        str(part),
                    ]
                    self._run(cmd)

                self._check_cancelled()
                self.signals.progress.emit(
                    92,
                    self._t("joining_ranges"),
                )

                concat_file = tmp / "concat.txt"
                lines: list[str] = []
                for part in part_paths:
                    escaped = part.as_posix().replace("'", r"'\''")
                    lines.append(f"file '{escaped}'")

                # Real line breaks are required by FFmpeg concat demuxer.
                concat_file.write_text("\n".join(lines), encoding="utf-8")

                cmd = [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel", "error",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                ]
                cmd += self._stream_map_args()
                cmd += [
                    "-c", "copy",
                ]

                if staging.suffix.lower() == ".mp4":
                    cmd += ["-movflags", "+faststart"]

                cmd += [str(staging)]
                self._run(cmd)

            self._commit_staging_output(staging, out)
            staging = None

            self.signals.progress.emit(100, self._t("done"))
            self.signals.finished.emit(
                str(out),
                self._t("multi_range_note", count=len(export_ranges))
                + self._boundary_result_note(max_shift)
                + self._stream_result_note(),
            )

        except ExportCancelledError:
            if staging is not None:
                try:
                    staging.unlink(missing_ok=True)
                except OSError:
                    pass
            self.signals.cancelled.emit()

        except Exception as exc:
            if staging is not None:
                try:
                    staging.unlink(missing_ok=True)
                except OSError:
                    pass

            self.signals.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.settings = QSettings("Sergilol", "VFRFastCut")
        saved_language = str(self.settings.value("ui/language", "")).lower()
        if saved_language not in SUPPORTED_LANGUAGES:
            saved_language = (
                "ru"
                if QLocale.system().name().lower().startswith("ru")
                else "en"
            )
        self.language = saved_language

        self.resize(980, 800)
        self.setAcceptDrops(True)

        icon_path = find_app_icon()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        # Created after the native HWND exists (singleShot below).
        self.taskbar_progress: Optional[WindowsTaskbarProgress] = None

        self.input_path = ""
        self.duration = 0.0
        self.segments: list[Segment] = []
        self.selected_index = -1
        self.undo_stack: list[list[Segment]] = []
        self.redo_stack: list[list[Segment]] = []

        self._export_busy = False
        self.export_thread: Optional[threading.Thread] = None
        self.exporter: Optional[LosslessExporter] = None

        self.export_signals = ExportSignals(self)
        self.export_signals.progress.connect(self.on_export_progress)
        self.export_signals.finished.connect(self.on_export_finished)
        self.export_signals.failed.connect(self.on_export_failed)
        self.export_signals.cancelled.connect(self.on_export_cancelled)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(1.0)
        self.player.setAudioOutput(self.audio)

        self.preview_muted = False
        self._seek_temp_muted = False

        # Seek debounce: prevents repeated arrow/scrub seeks from crackling the audio buffer.
        self._seek_timer = QTimer(self)
        self._seek_timer.setSingleShot(True)
        self._seek_timer.setInterval(SEEK_SETTLE_MS)
        self._seek_timer.timeout.connect(self._finish_smooth_seek)
        self._resume_after_seek = False
        self._seek_session_active = False

        # Used to force the first frame to appear immediately after opening media.
        # Both timers are members so a source change/reset can cancel every
        # pending preview-prime callback deterministically.
        self._preview_prime_pending = False
        self._preview_priming = False

        self._prime_start_timer = QTimer(self)
        self._prime_start_timer.setSingleShot(True)
        self._prime_start_timer.setInterval(0)
        self._prime_start_timer.timeout.connect(self._prime_first_frame)

        self._prime_timer = QTimer(self)
        self._prime_timer.setSingleShot(True)
        self._prime_timer.setInterval(90)
        self._prime_timer.timeout.connect(self._finish_prime_first_frame)

        self.video = SafePreviewWidget()
        self.player.setVideoSink(self.video.video_sink)

        self.timeline = TimelineWidget()
        self.timeline.seekRequested.connect(self.seek_seconds_smooth)
        self.timeline.segmentSelected.connect(self.select_segment)
        self.timeline.viewChanged.connect(self.on_timeline_view_changed)

        self.timeline_scroll = QScrollBar(Qt.Orientation.Horizontal)
        self.timeline_scroll.setMinimum(0)
        self.timeline_scroll.setMaximum(0)
        self.timeline_scroll.setEnabled(False)
        self.timeline_scroll.valueChanged.connect(self.on_scrollbar_changed)

        self.time_label = QLabel("00:00.000 / 00:00.000")
        self.selection_label = QLabel(self._t("selection_none"))
        self.zoom_label = QLabel("Zoom 1.0×")

        self.open_btn = QPushButton(self._t("open_video"))
        self.open_btn.clicked.connect(self.open_video)

        self.reset_btn = QPushButton(self._t("reset"))
        self.reset_btn.setToolTip(self._t("reset_tip"))
        self.reset_btn.clicked.connect(self.reset_project)

        self.play_btn = QPushButton(self._t("play"))
        self.play_btn.setFixedWidth(135)
        self.play_btn.setStyleSheet(PLAY_BUTTON_STYLE)
        self.play_btn.clicked.connect(self.toggle_play)

        self.prev_cut_btn = QPushButton(self._t("prev_cut"))
        self.prev_cut_btn.clicked.connect(self.seek_previous_cut)

        self.next_cut_btn = QPushButton(self._t("next_cut"))
        self.next_cut_btn.clicked.connect(self.seek_next_cut)

        self.mute_btn = QPushButton(self._t("mute"))
        self.mute_btn.setCheckable(True)
        self.mute_btn.clicked.connect(self.toggle_mute)

        self.volume_label = QLabel("100%")
        self.volume_label.setMinimumWidth(42)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setSingleStep(5)
        self.volume_slider.setPageStep(10)
        self.volume_slider.setFixedWidth(140)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)

        self.split_btn = QPushButton(self._t("split"))
        self.split_btn.setFixedWidth(135)
        self.split_btn.setStyleSheet(SPLIT_BUTTON_STYLE)
        self.split_btn.clicked.connect(self.split_at_playhead)

        self.delete_btn = QPushButton(self._t("delete"))
        self.delete_btn.clicked.connect(self.delete_selected)

        self.restore_btn = QPushButton(self._t("restore"))
        self.restore_btn.clicked.connect(self.restore_selected)

        self.undo_btn = QPushButton(self._t("undo"))
        self.undo_btn.clicked.connect(self.undo)

        self.export_fragment_btn = QPushButton(self._t("export_fragment"))
        self.export_fragment_btn.setFixedWidth(160)
        self.export_fragment_btn.setToolTip(
            self._t("export_fragment_tip")
        )
        self.export_fragment_btn.clicked.connect(self.export_selected_fragment)

        self.export_video_check = QCheckBox(self._t("export_video"))
        self.export_video_check.setChecked(True)
        self.export_video_check.setToolTip(
            self._t("export_video_tip")
        )
        self.export_video_check.toggled.connect(
            lambda _checked: self._update_ui_state()
        )

        self.export_audio_check = QCheckBox(self._t("export_audio"))
        self.export_audio_check.setChecked(True)
        self.export_audio_check.setToolTip(
            self._t("export_audio_tip")
        )
        self.export_audio_check.toggled.connect(
            lambda _checked: self._update_ui_state()
        )

        self.help_btn = QPushButton(self._t("help"))
        self.help_btn.setFixedWidth(105)
        self.help_btn.clicked.connect(self.show_help)

        self.language_combo = QComboBox()
        self.language_combo.setFixedWidth(96)
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Русский", "ru")
        language_index = self.language_combo.findData(self.language)
        if language_index >= 0:
            self.language_combo.setCurrentIndex(language_index)
        self.language_combo.setToolTip(self._t("language_tip"))
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)

        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedWidth(34)
        self.zoom_out_btn.clicked.connect(self.timeline.zoom_out)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedWidth(34)
        self.zoom_in_btn.clicked.connect(self.timeline.zoom_in)

        self.zoom_reset_btn = QPushButton("1:1")
        self.zoom_reset_btn.setFixedWidth(42)
        self.zoom_reset_btn.clicked.connect(self.timeline.zoom_reset)

        self.export_btn = QPushButton("Lossless Export")
        self.export_btn.setFixedWidth(140)
        self.export_btn.setStyleSheet(EXPORT_BUTTON_STYLE)
        self.export_btn.clicked.connect(self.export_lossless)

        self.cancel_export_btn = QPushButton(self._t("cancel_export"))
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

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.video, stretch=1)

        timeline_header = QHBoxLayout()
        self.timeline_title_label = QLabel(self._t("timeline"))
        timeline_header.addWidget(self.timeline_title_label)
        timeline_header.addStretch(1)
        timeline_header.addWidget(self.zoom_label)
        timeline_header.addWidget(self.zoom_out_btn)
        timeline_header.addWidget(self.zoom_reset_btn)
        timeline_header.addWidget(self.zoom_in_btn)
        timeline_header.addSpacing(8)
        timeline_header.addWidget(self.language_combo)
        timeline_header.addWidget(self.help_btn)
        layout.addLayout(timeline_header)

        layout.addWidget(self.timeline)
        layout.addWidget(self.timeline_scroll)
        layout.addWidget(self.time_label)

        # Row 1: file / playback controls.
        media_controls = QHBoxLayout()
        media_controls.addWidget(self.open_btn)
        media_controls.addWidget(self.prev_cut_btn)
        media_controls.addWidget(self.play_btn)
        media_controls.addWidget(self.next_cut_btn)
        media_controls.addWidget(self.mute_btn)
        self.volume_title_label = QLabel(self._t("volume"))
        media_controls.addWidget(self.volume_title_label)
        media_controls.addWidget(self.volume_slider)
        media_controls.addWidget(self.volume_label)
        media_controls.addStretch(1)
        layout.addLayout(media_controls)

        # Row 2: editing controls + one fixed Export/Cancel slot.
        edit_controls = QHBoxLayout()
        edit_controls.addWidget(self.reset_btn)
        edit_controls.addWidget(self.split_btn)
        edit_controls.addWidget(self.delete_btn)
        edit_controls.addWidget(self.restore_btn)
        edit_controls.addWidget(self.undo_btn)
        edit_controls.addStretch(1)
        edit_controls.addWidget(self.export_fragment_btn)
        edit_controls.addWidget(self.export_stack)
        layout.addLayout(edit_controls)

        # Keep export options visually grouped with the export buttons above.
        # Reuse the existing selection-info row so moving the checkbox does not
        # add another line or increase the initial window height.
        selection_export_row = QHBoxLayout()
        selection_export_row.addWidget(self.selection_label)
        selection_export_row.addStretch(1)
        selection_export_row.addWidget(self.export_video_check)
        selection_export_row.addWidget(self.export_audio_check)
        layout.addLayout(selection_export_row)

        footer = QHBoxLayout()
        footer.addStretch(1)
        author_label = QLabel("by Sergilol")
        author_label.setStyleSheet("color: #777; font-size: 10px;")
        footer.addWidget(author_label)
        layout.addLayout(footer)

        layout.addWidget(self.progress)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(self._t("ready"))

        # Make almost the whole application workspace a drop target.
        # Child widgets can otherwise swallow
        # drag/drop events before MainWindow sees them.
        self._install_drop_targets()

        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

        self._create_actions()
        self._apply_language()

        # winId()/widget sizes are reliable only after Qt has created and
        # laid out the native window.
        QTimer.singleShot(0, self._init_taskbar_progress)
        QTimer.singleShot(0, self._fit_initial_window_to_16_9_preview)

    # ---------- drag & drop ----------

    def _drop_video_path(
        self,
        mime_data,
        require_existing_file: bool = False,
    ) -> Optional[str]:
        if not mime_data.hasUrls():
            return None

        for url in mime_data.urls():
            if not url.isLocalFile():
                continue

            path = Path(url.toLocalFile())
            if path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
                continue

            if require_existing_file and not path.is_file():
                continue

            return str(path)

        return None

    def _install_drop_targets(self):
        # MainWindow already handles its own drag/drop events.
        # Child widgets need the event filter because some
        # controls otherwise consume drag events before they reach MainWindow.

        # Central workspace and all QWidget descendants:
        # preview, timeline, scrollbar, controls, labels, etc.
        root = self.centralWidget()
        if root is not None:
            root.setAcceptDrops(True)
            root.installEventFilter(self)

            for widget in root.findChildren(QWidget):
                widget.setAcceptDrops(True)
                widget.installEventFilter(self)

        # Status bar too, so practically the entire visible app accepts drops.
        if self.statusBar() is not None:
            self.statusBar().setAcceptDrops(True)
            self.statusBar().installEventFilter(self)

    def eventFilter(self, watched, event):
        etype = event.type()

        if self._export_busy:
            return super().eventFilter(watched, event)

        if etype == QEvent.Type.DragEnter:
            if self._drop_video_path(event.mimeData(), require_existing_file=False):
                event.acceptProposedAction()
                return True

        elif etype == QEvent.Type.DragMove:
            if self._drop_video_path(event.mimeData(), require_existing_file=False):
                event.acceptProposedAction()
                return True

        elif etype == QEvent.Type.Drop:
            path = self._drop_video_path(event.mimeData(), require_existing_file=True)
            if path:
                self.load_video(path)
                QTimer.singleShot(75, self._activate_after_drop)
                event.acceptProposedAction()
                return True

        return super().eventFilter(watched, event)

    def _fit_initial_window_to_16_9_preview(self):
        """Size the initial window around a 16:9 preview area.

        Qt has already performed its first layout pass when this runs, so the
        difference between the full window and QVideoWidget represents the
        actual controls, timeline, margins, status bar, etc.
        """
        if self.video.width() <= 0 or self.video.height() <= 0:
            return

        extra_width = max(0, self.width() - self.video.width())
        extra_height = max(0, self.height() - self.video.height())

        preview_width = INITIAL_PREVIEW_WIDTH
        preview_height = INITIAL_PREVIEW_HEIGHT

        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()

            max_preview_width = max(320, available.width() - extra_width - 20)
            max_preview_height = max(180, available.height() - extra_height - 20)

            scale = min(
                1.0,
                max_preview_width / INITIAL_PREVIEW_WIDTH,
                max_preview_height / INITIAL_PREVIEW_HEIGHT,
            )

            preview_width = max(320, int(INITIAL_PREVIEW_WIDTH * scale))
            preview_height = max(180, round(preview_width * 9 / 16))

            # Height can be the limiting dimension; re-check after rounding.
            if preview_height > max_preview_height:
                preview_height = max(180, int(max_preview_height))
                preview_width = max(320, round(preview_height * 16 / 9))

        self.resize(
            preview_width + extra_width,
            preview_height + extra_height,
        )

    def _init_taskbar_progress(self):
        if sys.platform == "win32":
            try:
                self.taskbar_progress = WindowsTaskbarProgress(int(self.winId()))
            except Exception:
                self.taskbar_progress = None

    # ---------- keyboard ----------

    # ---------- localization ----------

    def _t(self, key: str, **kwargs) -> str:
        return ui_text(self.language, key, **kwargs)

    def on_language_changed(self, index: int):
        language = self.language_combo.itemData(index)
        if language not in SUPPORTED_LANGUAGES or language == self.language:
            return

        self.language = language
        self.settings.setValue("ui/language", language)
        self._apply_language()
        self.statusBar().showMessage(self._t("language_changed"), 3000)

    def _refresh_selection_label(self):
        if not (0 <= self.selected_index < len(self.segments)):
            self.selection_label.setText(self._t("selection_none"))
            return

        seg = self.segments[self.selected_index]
        state = self._t("state_deleted") if seg.deleted else self._t("state_kept")
        self.selection_label.setText(
            self._t(
                "segment_info",
                number=self.selected_index + 1,
                start=fmt_time(seg.start),
                end=fmt_time(seg.end),
                duration=fmt_time(seg.duration),
                state=state,
            )
        )

    def _apply_language(self):
        self.timeline.set_empty_text(self._t("timeline_empty"))
        self.timeline_title_label.setText(self._t("timeline"))
        self.volume_title_label.setText(self._t("volume"))
        self.open_btn.setText(self._t("open_video"))
        self.reset_btn.setText(self._t("reset"))
        self.reset_btn.setToolTip(self._t("reset_tip"))
        self.prev_cut_btn.setText(self._t("prev_cut"))
        self.next_cut_btn.setText(self._t("next_cut"))
        self.split_btn.setText(self._t("split"))
        self.delete_btn.setText(self._t("delete"))
        self.restore_btn.setText(self._t("restore"))
        self.undo_btn.setText(self._t("undo"))
        self.export_fragment_btn.setText(self._t("export_fragment"))
        self.export_fragment_btn.setToolTip(self._t("export_fragment_tip"))
        self.export_video_check.setText(self._t("export_video"))
        self.export_video_check.setToolTip(self._t("export_video_tip"))
        self.export_audio_check.setText(self._t("export_audio"))
        self.export_audio_check.setToolTip(self._t("export_audio_tip"))
        self.help_btn.setText(self._t("help"))
        self.help_btn.setToolTip(self._t("help_tip"))
        self.language_combo.setToolTip(self._t("language_tip"))
        self.cancel_export_btn.setText(self._t("cancel_export"))
        self.mute_btn.setText(
            self._t("unmute") if self.preview_muted else self._t("mute")
        )
        self._sync_play_button()
        self._refresh_selection_label()
        self._update_ui_state()

    def _create_actions(self):
        act_open = QAction(self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self.open_video)
        self.addAction(act_open)

        act_reset = QAction(self)
        act_reset.setShortcut(QKeySequence("Ctrl+N"))
        act_reset.triggered.connect(self.reset_project)
        self.addAction(act_reset)

        act_help = QAction(self)
        act_help.setShortcut(QKeySequence("F1"))
        act_help.triggered.connect(self.show_help)
        self.addAction(act_help)

        act_space = QAction(self)
        act_space.setShortcut(QKeySequence(Qt.Key.Key_Space))
        act_space.triggered.connect(self.toggle_play)
        self.addAction(act_space)

        act_mute = QAction(self)
        act_mute.setShortcut(QKeySequence("M"))
        act_mute.triggered.connect(self.toggle_mute)
        self.addAction(act_mute)

        act_split = QAction(self)
        act_split.setShortcut(QKeySequence("S"))
        act_split.triggered.connect(self.split_at_playhead)
        self.addAction(act_split)

        act_prev_cut = QAction(self)
        act_prev_cut.setShortcut(QKeySequence("Q"))
        act_prev_cut.triggered.connect(self.seek_previous_cut)
        self.addAction(act_prev_cut)

        act_next_cut = QAction(self)
        act_next_cut.setShortcut(QKeySequence("E"))
        act_next_cut.triggered.connect(self.seek_next_cut)
        self.addAction(act_next_cut)

        act_delete = QAction(self)
        act_delete.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        act_delete.triggered.connect(self.delete_selected)
        self.addAction(act_delete)

        act_undo = QAction(self)
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_undo.triggered.connect(self.undo)
        self.addAction(act_undo)

        act_redo = QAction(self)
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        act_redo.triggered.connect(self.redo)
        self.addAction(act_redo)

        act_left = QAction(self)
        act_left.setShortcut(QKeySequence(Qt.Key.Key_Left))
        act_left.triggered.connect(
            lambda: self.seek_seconds_smooth(max(0.0, self.current_seconds() - 1.0))
        )
        self.addAction(act_left)

        act_right = QAction(self)
        act_right.setShortcut(QKeySequence(Qt.Key.Key_Right))
        act_right.triggered.connect(
            lambda: self.seek_seconds_smooth(
                min(self.duration, self.current_seconds() + 1.0)
            )
        )
        self.addAction(act_right)

    # ---------- media ----------

    def current_seconds(self) -> float:
        return self.player.position() / 1000.0

    @staticmethod
    def _normalized_file_path(path: str) -> str:
        """Stable Windows-friendly identity for a local source file."""
        try:
            resolved = Path(path).resolve(strict=False)
        except OSError:
            resolved = Path(path).absolute()
        return str(resolved).casefold()

    def _is_same_source(self, path: str) -> bool:
        return bool(
            self.input_path
            and self._normalized_file_path(path)
            == self._normalized_file_path(self.input_path)
        )

    def _cancel_preview_prime(self):
        """Cancel every pending/running first-frame prime callback."""
        self._prime_start_timer.stop()
        self._prime_timer.stop()
        self._preview_prime_pending = False
        self._preview_priming = False

    def _clear_project_state(self):
        """Clear project state while preserving volume/mute preferences."""
        self._seek_timer.stop()
        self._cancel_preview_prime()
        self._seek_session_active = False
        self._resume_after_seek = False
        self._seek_temp_muted = False
        self._apply_audio_mute_state()

        self.player.stop()
        self.player.setSource(QUrl())
        self.video.clear_frame()

        self.input_path = ""
        self.duration = 0.0
        self.segments.clear()
        self.selected_index = -1
        self.undo_stack.clear()
        self.redo_stack.clear()

        self.timeline.zoom = 1.0
        self.timeline.offset = 0.0
        self.timeline.set_state(0.0, self.segments, 0.0, -1)

        self.time_label.setText("00:00.000 / 00:00.000")
        self.selection_label.setText(self._t("selection_none"))
        self.progress.setValue(0)

        self._sync_play_button()
        self._update_ui_state()

    def reset_project(self):
        if self._export_busy:
            self.statusBar().showMessage(
                self._t("cannot_reset_export"),
                3000,
            )
            return

        if not self.input_path:
            return

        self._clear_project_state()
        self.statusBar().showMessage(self._t("project_reset"), 3000)

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("open_dialog"),
            "",
            self._t("video_filter"),
        )
        if path:
            self.load_video(path)

    def load_video(self, path: str):
        if self._export_busy:
            self.statusBar().showMessage(
                self._t("wait_export"),
                3000,
            )
            return

        video_path = Path(path)

        if not video_path.is_file():
            QMessageBox.warning(self, APP_NAME, self._t("file_not_found"))
            return

        if video_path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
            QMessageBox.warning(
                self,
                APP_NAME,
                self._t("unsupported_type"),
            )
            return

        # Re-opening/dropping the exact same source is a no-op so an
        # accidental duplicate action cannot destroy cuts or Undo history.
        # A same-named file in another folder has a different full path and
        # therefore starts a new project.
        if self._is_same_source(str(video_path)):
            self.statusBar().showMessage(
                self._t("already_open", name=video_path.name),
                3000,
            )
            return

        if self.input_path:
            self._clear_project_state()

        self.input_path = str(video_path)
        self.duration = 0.0
        self.segments.clear()
        self.selected_index = -1
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.timeline.zoom = 1.0
        self.timeline.offset = 0.0

        self._preview_prime_pending = True
        self.video.clear_frame()
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))

        self.statusBar().showMessage(self._t("opened", name=video_path.name))
        self._update_timeline()
        self._update_ui_state()

    def _activate_after_drop(self):
        """Request foreground and keyboard focus after a successful file drop."""
        self.raise_()
        self.activateWindow()
        QApplication.setActiveWindow(self)

        if sys.platform == "win32":
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            SW_RESTORE = 9

            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)

        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def dragEnterEvent(self, event):
        if not self._export_busy and self._drop_video_path(
            event.mimeData(),
            require_existing_file=False,
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self._export_busy and self._drop_video_path(
            event.mimeData(),
            require_existing_file=False,
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if self._export_busy:
            event.ignore()
            return

        path = self._drop_video_path(
            event.mimeData(),
            require_existing_file=True,
        )
        if path:
            self.load_video(path)
            QTimer.singleShot(75, self._activate_after_drop)
            event.acceptProposedAction()
        else:
            event.ignore()

    def on_media_status(self, status):
        # QMediaPlayer sometimes does not paint the first frame until playback
        # starts at least once. Prime it silently as soon as the media is loaded.
        if (
            self._preview_prime_pending
            and status in (
                QMediaPlayer.MediaStatus.LoadedMedia,
                QMediaPlayer.MediaStatus.BufferedMedia,
            )
        ):
            self._preview_prime_pending = False
            self._prime_start_timer.start()

        self._update_ui_state()

    def _prime_first_frame(self):
        if not self.input_path:
            return

        # Seek a tiny amount into the file so a decodable frame is requested.
        # Keep audio muted during the one-shot playback prime.
        self._preview_priming = True
        self._seek_temp_muted = True
        self._apply_audio_mute_state()

        self.player.pause()
        self.player.setPosition(1)
        self.player.play()

        # A very short playback burst is enough for Qt/FFmpeg to paint frame 1.
        self._prime_timer.start()

    def _finish_prime_first_frame(self):
        self.player.pause()
        self.player.setPosition(1)
        self._preview_priming = False
        self._seek_temp_muted = False
        self._apply_audio_mute_state()
        self._sync_play_button()

    def on_duration_changed(self, ms: int):
        if ms <= 0:
            return
        self.duration = ms / 1000.0
        if not self.segments:
            self.segments = [Segment(0.0, self.duration, False)]
            self.selected_index = 0
        else:
            self.segments[-1].end = self.duration
        self._update_timeline()
        self._update_ui_state()

    def on_position_changed(self, ms: int):
        pos = ms / 1000.0
        self.timeline.set_position(pos)
        self.time_label.setText(
            f"{fmt_time(pos)} / {fmt_time(self.duration)}"
        )

    def on_playback_state_changed(self, state):
        # Preview priming and smooth seeking temporarily change the real
        # QMediaPlayer state for technical reasons. Those transitions must not
        # make the user-facing Play/Pause button flicker.
        if self._preview_priming or self._seek_session_active:
            return
        self._sync_play_button(state)

    def _set_play_button_playing(self, playing: bool):
        self.play_btn.setText(
            self._t("pause") if playing else self._t("play")
        )

    def _sync_play_button(self, state=None):
        if state is None:
            state = self.player.playbackState()

        self._set_play_button_playing(
            state == QMediaPlayer.PlaybackState.PlayingState
        )

    # ---------- smooth seek / audio crackle protection ----------

    def _safe_preview_end(self) -> float:
        if self.duration <= 0:
            return 0.0

        # For normal media keep a 100 ms gap. Tiny test clips still keep a
        # proportional non-zero playable range instead of collapsing to 0.
        margin = min(
            SAFE_EOF_MARGIN_SECONDS,
            max(0.001, self.duration * 0.10),
        )
        return max(0.0, self.duration - margin)

    def seek_seconds_smooth(self, seconds: float):
        if self.duration <= 0:
            return

        seconds = max(
            0.0,
            min(self._safe_preview_end(), float(seconds)),
        )

        # Start one continuous seek session. While the user keeps pressing
        # arrows / scrubbing, keep playback paused and audio muted so the
        # audio backend is not repeatedly stopped/started on every seek.
        if not self._seek_session_active:
            self._seek_session_active = True
            self._resume_after_seek = (
                self.player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
            )

            # Keep the button representing the user's logical playback mode,
            # not the temporary internal pause used to suppress audio crackle.
            self._set_play_button_playing(self._resume_after_seek)

            if self._resume_after_seek:
                self.player.pause()

            self._seek_temp_muted = True
            self._apply_audio_mute_state()

        self.player.setPosition(int(seconds * 1000))
        self.timeline.ensure_time_visible(seconds)

        # Every new seek restarts the quiet period. Audio is restored only
        # after the user has stopped seeking for a while.
        self._seek_timer.start()

    def _finish_smooth_seek(self):
        resume_playback = self._resume_after_seek
        self._resume_after_seek = False

        self._seek_temp_muted = False
        self._apply_audio_mute_state()

        if resume_playback:
            # Keep seek-session UI suppression active while play() restores the
            # real player state. The button already shows Pause and must stay so.
            self.player.play()
            self._set_play_button_playing(True)
            self._seek_session_active = False
        else:
            self._seek_session_active = False
            self._sync_play_button()

    def _apply_audio_mute_state(self):
        self.audio.setMuted(self.preview_muted or self._seek_temp_muted)

    def toggle_mute(self):
        self.preview_muted = not self.preview_muted
        self.mute_btn.blockSignals(True)
        self.mute_btn.setChecked(self.preview_muted)
        self.mute_btn.setText(self._t("unmute") if self.preview_muted else self._t("mute"))
        self.mute_btn.blockSignals(False)
        self._apply_audio_mute_state()

    def on_volume_changed(self, value: int):
        value = max(0, min(100, int(value)))
        self.audio.setVolume(value / 100.0)
        self.volume_label.setText(f"{value}%")

    def toggle_play(self):
        if not self.input_path:
            return
        if self._seek_timer.isActive():
            self._seek_timer.stop()
            self._seek_session_active = False
            self._seek_temp_muted = False
            self._apply_audio_mute_state()
            self._resume_after_seek = False

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    # ---------- timeline / selection ----------

    def _cut_positions(self) -> list[float]:
        # Segments are always chronological; every segment after the first
        # starts at an actual user-created cut.
        return [seg.start for seg in self.segments[1:]]

    def seek_previous_cut(self):
        if self.duration <= 0:
            return

        cuts = self._cut_positions()
        current = self.current_seconds()
        index = bisect.bisect_left(cuts, current) - 1
        target = cuts[index] if index >= 0 else 0.0

        self.seek_seconds_smooth(target)
        self.statusBar().showMessage(
            self._t("previous_cut_status", time=fmt_time(target)),
            1200,
        )

    def seek_next_cut(self):
        if self.duration <= 0:
            return

        cuts = self._cut_positions()
        current = self.current_seconds()
        index = bisect.bisect_right(cuts, current)
        target = (
            cuts[index]
            if index < len(cuts)
            else self._safe_preview_end()
        )

        self.seek_seconds_smooth(target)
        self.statusBar().showMessage(
            self._t("next_cut_status", time=fmt_time(target)),
            1200,
        )

    def select_segment(self, index: int):
        if 0 <= index < len(self.segments):
            self.selected_index = index
            self._refresh_selection_label()
            self._update_timeline()
            self._update_ui_state()

    def on_timeline_view_changed(self, offset: float, visible_duration: float):
        self.zoom_label.setText(f"Zoom {self.timeline.zoom:.1f}×")

        max_offset = max(0.0, self.duration - visible_duration)
        maximum_ms = int(round(max_offset * 1000))
        page_ms = max(1, int(round(visible_duration * 1000)))
        value_ms = int(round(offset * 1000))

        self.timeline_scroll.blockSignals(True)
        self.timeline_scroll.setRange(0, maximum_ms)
        self.timeline_scroll.setPageStep(page_ms)
        self.timeline_scroll.setSingleStep(max(1, page_ms // 20))
        self.timeline_scroll.setValue(min(value_ms, maximum_ms))
        self.timeline_scroll.blockSignals(False)

        # Keep the scrollbar in the layout at all times. At 1x it is simply
        # disabled with a zero range, so zooming never shifts the UI.
        self.timeline_scroll.setEnabled(self.timeline.zoom > 1.0001)

    def on_scrollbar_changed(self, value: int):
        self.timeline.set_offset(value / 1000.0, emit=False)

    def _snapshot(self):
        self.undo_stack.append(clone_segments(self.segments))
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def split_at_playhead(self):
        if self._export_busy:
            return
        if not self.segments or self.duration <= 0:
            return
        t = self.current_seconds()

        idx = -1
        for i, seg in enumerate(self.segments):
            if seg.start + 0.002 < t < seg.end - 0.002:
                idx = i
                break
        if idx < 0:
            self.statusBar().showMessage(
                self._t("playhead_boundary"), 3000
            )
            return

        self._snapshot()
        seg = self.segments[idx]
        left = Segment(seg.start, t, seg.deleted)
        right = Segment(t, seg.end, seg.deleted)
        self.segments[idx:idx + 1] = [left, right]
        self.selected_index = idx + 1
        self.select_segment(self.selected_index)
        self.statusBar().showMessage(self._t("split_status", time=fmt_time(t)), 2500)

    def delete_selected(self):
        if self._export_busy:
            return
        if not (0 <= self.selected_index < len(self.segments)):
            return
        seg = self.segments[self.selected_index]
        if seg.deleted:
            return
        self._snapshot()
        seg.deleted = True
        self.select_segment(self.selected_index)
        self.statusBar().showMessage(self._t("marked_deleted"), 2500)

    def restore_selected(self):
        if self._export_busy:
            return
        if not (0 <= self.selected_index < len(self.segments)):
            return
        seg = self.segments[self.selected_index]
        if not seg.deleted:
            return
        self._snapshot()
        seg.deleted = False
        self.select_segment(self.selected_index)
        self.statusBar().showMessage(self._t("restored"), 2500)

    def undo(self):
        if self._export_busy:
            return
        if not self.undo_stack:
            return
        self.redo_stack.append(clone_segments(self.segments))
        self.segments = self.undo_stack.pop()
        self.selected_index = min(self.selected_index, len(self.segments) - 1)
        self._update_timeline()
        self._update_ui_state()
        self.statusBar().showMessage("Undo", 1500)

    def redo(self):
        if self._export_busy:
            return
        if not self.redo_stack:
            return
        self.undo_stack.append(clone_segments(self.segments))
        self.segments = self.redo_stack.pop()
        self.selected_index = min(self.selected_index, len(self.segments) - 1)
        self._update_timeline()
        self._update_ui_state()
        self.statusBar().showMessage("Redo", 1500)

    def _update_timeline(self):
        self.timeline.set_state(
            self.duration,
            self.segments,
            self.current_seconds(),
            self.selected_index,
        )

    def _update_ui_state(self):
        ready = bool(self.input_path and self.duration > 0)
        editable = ready and not self._export_busy

        self.open_btn.setEnabled(not self._export_busy)
        self.reset_btn.setEnabled(bool(self.input_path) and not self._export_busy)

        # Preview/navigation remain usable while exporting.
        self.play_btn.setEnabled(ready)
        self.prev_cut_btn.setEnabled(ready)
        self.next_cut_btn.setEnabled(ready)
        self.mute_btn.setEnabled(ready)
        self.volume_slider.setEnabled(ready)

        # Timeline navigation remains usable; editing is locked.
        self.zoom_in_btn.setEnabled(ready)
        self.zoom_out_btn.setEnabled(ready)
        self.zoom_reset_btn.setEnabled(ready)

        self.split_btn.setEnabled(editable)
        self.undo_btn.setEnabled(editable and bool(self.undo_stack))
        self.delete_btn.setEnabled(
            editable
            and 0 <= self.selected_index < len(self.segments)
            and not self.segments[self.selected_index].deleted
        )
        self.restore_btn.setEnabled(
            editable
            and 0 <= self.selected_index < len(self.segments)
            and self.segments[self.selected_index].deleted
        )

        selected_valid = (
            ready
            and 0 <= self.selected_index < len(self.segments)
            and self.segments[self.selected_index].duration > 0.001
        )

        streams_selected = (
            self.export_video_check.isChecked()
            or self.export_audio_check.isChecked()
        )

        self.export_btn.setEnabled(editable and streams_selected)
        self.export_fragment_btn.setEnabled(
            editable and selected_valid and streams_selected
        )
        self.export_video_check.setEnabled(not self._export_busy)
        self.export_audio_check.setEnabled(not self._export_busy)
        self.language_combo.setEnabled(not self._export_busy)

        self.cancel_export_btn.setEnabled(self._export_busy)
        self.export_stack.setCurrentWidget(
            self.cancel_export_btn if self._export_busy else self.export_btn
        )

        if not self._preview_priming and not self._seek_session_active:
            self._sync_play_button()

    # ---------- help ----------

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{APP_NAME} {APP_VERSION} — {self._t('help_title')}")
        dialog.resize(760, 620)

        layout = QVBoxLayout(dialog)

        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(False)
        browser.setHtml(HELP_HTML[self.language])
        layout.addWidget(browser)

        close_btn = QPushButton(self._t("close"))
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(dialog.accept)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        dialog.exec()

    # ---------- export ----------

    def _get_export_tools(
        self,
        require_ffprobe: bool = True,
    ) -> Optional[tuple[str, str]]:
        ffmpeg = find_tool("ffmpeg.exe")
        ffprobe = find_tool("ffprobe.exe") if require_ffprobe else ""

        if ffmpeg and (ffprobe or not require_ffprobe):
            return ffmpeg, ffprobe

        missing = (
            self._t("tools_missing_both")
            if require_ffprobe
            else self._t("tools_missing_ffmpeg")
        )
        QMessageBox.critical(
            self,
            APP_NAME,
            self._t("tools_missing", missing=missing),
        )
        return None

    def _start_export(
        self,
        output: str,
        segments: list[Segment],
        ranges_override: Optional[list[tuple[float, float]]] = None,
    ):
        export_video = self.export_video_check.isChecked()
        export_audio = self.export_audio_check.isChecked()
        if not export_video and not export_audio:
            return

        tools = self._get_export_tools(require_ffprobe=export_video)
        if tools is None:
            return

        src = Path(self.input_path)
        if Path(output).resolve() == src.resolve():
            QMessageBox.warning(
                self,
                APP_NAME,
                self._t("cannot_overwrite_source"),
            )
            return

        ffmpeg, ffprobe = tools
        self.set_export_busy(True)

        self.exporter = LosslessExporter(
            ffmpeg,
            ffprobe,
            self.input_path,
            output,
            self.duration,
            segments,
            self.export_signals,
            export_video=export_video,
            export_audio=export_audio,
            ranges_override=ranges_override,
            language=self.language,
        )

        self.export_thread = threading.Thread(
            target=self.exporter.run,
            daemon=True,
            name="VFRFastCutExport",
        )
        self.export_thread.start()

    def _audio_only_export(self) -> bool:
        return (
            self.export_audio_check.isChecked()
            and not self.export_video_check.isChecked()
        )

    def _default_video_output_suffix(self) -> str:
        """Keep safe native outputs; remux other input containers to MKV."""
        source_suffix = Path(self.input_path).suffix.lower()
        if source_suffix in VIDEO_OUTPUT_SUFFIXES:
            return source_suffix
        return ".mkv"

    def _prepare_export_dialog(
        self,
        name_suffix: str,
    ) -> tuple[str, str]:
        src = Path(self.input_path)

        if self._audio_only_export():
            default = src.with_name(src.stem + name_suffix + ".mka")
            return (
                str(default),
                "Matroska Audio (*.mka)",
            )

        output_suffix = self._default_video_output_suffix()
        default = src.with_name(src.stem + name_suffix + output_suffix)
        return (
            str(default),
            self._t("file_filter_av"),
        )

    def _normalize_export_output(self, output: str) -> str:
        path = Path(output)

        if self._audio_only_export():
            if path.suffix.lower() != ".mka":
                path = path.with_suffix(".mka")
            return str(path)

        if path.suffix.lower() not in VIDEO_OUTPUT_SUFFIXES:
            path = path.with_suffix(self._default_video_output_suffix())
        return str(path)

    def export_lossless(self):
        if not self.input_path or self.duration <= 0:
            return

        default, file_filter = self._prepare_export_dialog("_FASTCUT")
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Lossless Export",
            default,
            file_filter,
        )
        if not output:
            return

        output = self._normalize_export_output(output)

        self._start_export(
            output,
            clone_segments(self.segments),
        )

    def export_selected_fragment(self):
        if (
            not self.input_path
            or self.duration <= 0
            or not (0 <= self.selected_index < len(self.segments))
        ):
            return

        seg = self.segments[self.selected_index]
        if seg.duration <= 0.001:
            return

        fragment_number = self.selected_index + 1
        default, file_filter = self._prepare_export_dialog(
            f"_FRAGMENT_{fragment_number:02d}"
        )

        output, _ = QFileDialog.getSaveFileName(
            self,
            self._t("export_selected_dialog"),
            default,
            file_filter,
        )
        if not output:
            return

        output = self._normalize_export_output(output)

        self._start_export(
            output,
            [],
            ranges_override=[(seg.start, seg.end)],
        )

    def _set_progress_visible(self, visible: bool):
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

    def cancel_export(self):
        if not self._export_busy or not self.exporter:
            return

        self.cancel_export_btn.setEnabled(False)
        self.statusBar().showMessage(self._t("stopping_export"))
        self.exporter.cancel()

    def _clear_export_refs(self):
        self.exporter = None
        self.export_thread = None

    def on_export_progress(self, pct: int, text: str):
        self.progress.setValue(pct)
        if self.taskbar_progress:
            self.taskbar_progress.update(pct)
        self.statusBar().showMessage(text)

    def on_export_finished(self, output: str, note: str):
        self.set_export_busy(False)
        self._clear_export_refs()
        self.statusBar().showMessage(self._t("export_finished_status"), 5000)

        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(self._t("export_finished_title"))
        box.setInformativeText(f"{note}\n\n{self._t('output_file', output=output)}")

        open_folder_btn = box.addButton(
            self._t("open_result_folder"),
            QMessageBox.ButtonRole.ActionRole,
        )
        box.addButton(QMessageBox.StandardButton.Ok)

        box.exec()

        if box.clickedButton() is open_folder_btn:
            folder = Path(output).resolve().parent
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            if not opened:
                self.statusBar().showMessage(
                    self._t("folder_open_failed"),
                    5000,
                )

    def on_export_cancelled(self):
        self.set_export_busy(False)
        self._clear_export_refs()
        self.statusBar().showMessage(self._t("export_cancelled"), 5000)

    def on_export_failed(self, error: str):
        self.set_export_busy(False)
        self._clear_export_refs()
        self.statusBar().showMessage(self._t("export_error_status"), 5000)
        QMessageBox.critical(
            self,
            APP_NAME,
            self._t("export_failed", error=error),
        )

    def closeEvent(self, event):
        self._seek_timer.stop()
        self._cancel_preview_prime()
        self.player.stop()
        self.player.setVideoSink(None)
        self.video.clear_frame()

        exporter = self.exporter
        thread = self.export_thread

        if exporter and thread and thread.is_alive():
            exporter.cancel()
            thread.join(timeout=1.5)

            if thread.is_alive():
                exporter.force_kill()
                thread.join(timeout=1.0)

        if self.taskbar_progress:
            self.taskbar_progress.close()
            self.taskbar_progress = None

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Sergilol")

    icon_path = find_app_icon()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
