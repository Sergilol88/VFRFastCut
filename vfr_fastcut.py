# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sergilol

from __future__ import annotations

import bisect
import ctypes
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from vfr_keyframes import (
    KeyframeScanCancelled,
    KeyframeScanError,
    scan_video_keyframes,
    resolve_preview_playback_position,
    snap_range_to_keyframes,
    snap_ranges_to_keyframes,
)

# Qt Multimedia hardware texture conversion can produce corrupted/green preview
# frames on some Windows GPU/driver combinations. Keep hardware video decoding
# available, but prefer the more compatible texture-conversion path. Advanced
# users can still override the Qt setting before launching the application.
os.environ.setdefault("QT_DISABLE_HW_TEXTURES_CONVERSION", "1")
from PySide6.QtCore import QLocale, QObject, QEvent, QRectF, QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPainter, QPen, QTransform
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QScrollBar,
    QSlider,
    QSizePolicy,
    QFrame,
    QStatusBar,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "VFR FastCut"
APP_VERSION = "0.5.0-dev"

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
        "remove_cut": "Remove cut [Shift+S]",
        "remove_cut_tip": "Merge the two segments at the cut under the playhead. Q/E can jump exactly to a cut.",
        "delete": "Delete [Delete]",
        "restore": "Restore",
        "undo": "Undo [Ctrl+Z]",
        "export_fragment": "Export segment",
        "export_fragment_tip": "Export only the selected segment without re-encoding",
        "export_video": "Export video",
        "export_video_tip": "On: keep the video stream. Off: export only selected audio streams.",
        "export_audio": "Export audio",
        "export_audio_tip": "On: keep the selected audio tracks. Off: export video only.",
        "audio_tracks": "Audio tracks…",
        "audio_tracks_count": "Audio tracks {selected}/{total}…",
        "audio_tracks_tip": "Choose audio tracks for export ({selected}/{total} selected).",
        "audio_tracks_no_file_tip": "Open a video before managing audio tracks.",
        "audio_tracks_none_tip": "No embedded tracks found. You can add external audio.",
        "audio_tracks_unavailable_tip": "Embedded audio metadata is unavailable. You can still add external audio.",
        "audio_tracks_title": "Audio tracks",
        "audio_tracks_intro": "Choose which audio tracks are available on the project timeline and included in audio export. Use the Play flag beside each visible timeline row to include or exclude that track from live preview and Main Mix. External audio management, Main Mix/stems, Volume and Fade settings live in the main Audio menu.",
        "audio_track_number": "Track {number}",
        "audio_track_channels": "{count} ch",
        "audio_track_default": "default",
        "audio_track_external": "External: {name}",
        "audio_track_external_stream": "stream {number}",
        "audio_track_volume": "Volume:",
        "audio_track_volume_tip": "Per-track volume for preview and export. 100% keeps this track unchanged; lower values re-encode only this track to AAC while video and unchanged audio remain stream-copied.",
        "audio_track_fade_in": "Fade In:",
        "audio_track_fade_out": "Fade Out:",
        "audio_track_fade_tip": "Fade duration in seconds. 0 disables it. Fade is applied to each exported kept range; processed tracks are encoded to AAC while video and unchanged audio remain stream-copied.",
        "audio_tracks_add_external": "Add external audio…",
        "audio_tracks_remove_external_tip": "Remove this external audio track from the project",
        "audio_file_dialog": "Add external audio",
        "audio_file_filter": "Audio/media (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.mka *.mp4 *.mov *.mkv *.webm);;All files (*.*)",
        "external_audio_no_streams": "The selected file contains no audio streams.",
        "external_audio_probe_failed": "Could not read audio streams from the selected file.\n\n{error}",
        "external_audio_duplicate": "This audio file is already in the project. Use Create copy on its timeline clip if you need the same sound again.",
        "external_audio_is_source": "This is the current video source. Use its embedded audio tracks instead.",
        "audio_tracks_select_all": "Select all",
        "audio_tracks_select_none": "Select none",
        "audio_tracks_apply": "Apply",
        "audio_tracks_cancel": "Cancel",
        "audio_tracks_selected": "Selected: {selected}/{total}",
        "audio_tracks_status": "Audio tracks selected for export: {selected}/{total}",
        "audio_main_mix": "Create Main Mix from Play-enabled tracks",
        "audio_main_mix_tip": "Create a ready-to-play AAC Main Mix as the first/default audio stream. Only visible tracks with an active Play flag are mixed, using their timeline position, trim, volume and fade settings.",
        "audio_keep_stems": "Keep separate tracks (stems)",
        "audio_keep_stems_tip": "Keep the selected tracks as separate audio streams after Main Mix. Untouched stems remain stream-copied; processed stems remain AAC.",
        "audio_timeline": "Audio Tracks",
        "audio_timeline_empty": "No selected audio tracks to display",
        "audio_timeline_drag_tip": "Click the Play flag on the left to include/exclude a track from live preview and Main Mix. Drag an external audio block to position it; drag its left or right edge to trim the beginning or end.",
        "audio_track_setting_status": "{setting} updated for {track}.",
        "audio_track_processing_reset_status": "Volume and fades reset for {track}.",
        "audio_timeline_offset_status": "External audio position updated.",
        "audio_timeline_trim_status": "External audio duration updated.",
        "menu_file": "File",
        "menu_edit": "Edit",
        "menu_playback": "Playback",
        "menu_audio": "Audio",
        "menu_view": "View",
        "menu_help": "Help",
        "menu_open_video": "Open video…",
        "menu_reset_project": "Reset project",
        "menu_export": "Lossless Export…",
        "menu_export_fragment": "Export selected segment…",
        "menu_exit": "Exit",
        "menu_undo": "Undo",
        "menu_redo": "Redo",
        "menu_split": "Split",
        "menu_remove_cut": "Remove cut",
        "menu_delete": "Delete segment",
        "menu_restore": "Restore segment",
        "menu_play": "Play",
        "menu_pause": "Pause",
        "menu_prev_cut": "Previous cut",
        "menu_next_cut": "Next cut",
        "menu_mute": "Mute",
        "menu_audio_tracks": "Available audio tracks…",
        "menu_add_external_audio": "Add external audio",
        "menu_choose_external_audio": "Choose file…",
        "menu_no_recent_external_audio": "No recent audio files",
        "menu_duplicate_external_audio": "Create copy",
        "menu_delete_external_audio_copy": "Delete copy",
        "external_audio_duplicated_status": "Copy created: {track}",
        "external_audio_copy_deleted_status": "Copy deleted: {track}",
        "menu_remove_external_audio": "Remove external audio",
        "menu_no_external_audio": "No external audio",
        "menu_no_active_audio_tracks": "No selected audio tracks",
        "audio_mix_track_enabled_status": "Added to mix: {track}",
        "audio_mix_track_disabled_status": "Removed from mix: {track}",
        "menu_track_volume": "Volume…",
        "menu_track_fade_in": "Fade In…",
        "menu_track_fade_out": "Fade Out…",
        "menu_track_reset_processing": "Reset Volume/Fades",
        "audio_track_value_dialog": "{setting} — {track}",
        "menu_zoom_in": "Zoom in",
        "menu_zoom_out": "Zoom out",
        "menu_zoom_reset": "Reset zoom",
        "menu_show_audio_tracks": "Show audio tracks",
        "menu_language": "Language",
        "menu_language_en": "English",
        "menu_language_ru": "Русский",
        "menu_help_contents": "Help and shortcuts",
        "help": "Help [F1]",
        "help_tip": "Open help and keyboard shortcuts",
        "language_tip": "Interface language",
        "cancel_export": "Cancel export",
        "task_export_title": "Lossless Export",
        "task_export_preparing": "Preparing export…",
        "task_keyframe_title": "Analyzing video",
        "task_keyframe_hint": "You can continue editing while keyframes are analyzed.",
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
        "opened_with_audio": "Opened: {name} • audio tracks: {count}",
        "opened_audio_probe_failed": "Opened: {name} • audio metadata unavailable",
        "previous_cut_status": "Previous cut: {time}",
        "next_cut_status": "Next cut: {time}",
        "state_deleted": "DELETED",
        "state_kept": "kept",
        "segment_info": "Segment {number}: {start} → {end} ({duration}) • {state}",
        "playhead_boundary": "The playhead is already on a segment boundary.",
        "split_status": "Split: {time}",
        "no_cut_at_playhead": "There is no cut at the playhead. Use Q/E to jump exactly to a cut.",
        "cut_state_mismatch": "This cut separates kept and deleted segments. Restore or delete both sides before removing the cut.",
        "cut_removed_status": "Cut removed: {time}",
        "marked_deleted": "Segment marked for deletion.",
        "restored": "Segment restored.",
        "preview_nothing_to_play": "All video segments are deleted; there is nothing to play.",
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
        "show_details": "Details...",
        "hide_details": "Hide details",
        "open_result_folder": "Open result folder",
        "folder_open_failed": "Could not open the result folder.",
        "export_cancelled": "Export cancelled.",
        "export_error_status": "Export error.",
        "export_failed": "Export failed.\n\n{error}",
        "export_no_streams": "No streams selected for export.",
        "scan_keyframes": "Scanning keyframes…",
        "keyframe_scan_started": "Analyzing keyframes…",
        "keyframe_scan_progress": "Analyzing keyframes… {percent}%",
        "keyframe_scan_finished": "Keyframes ready: {count}",
        "keyframe_scan_failed_status": "Keyframe analysis unavailable.",
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
        "external_offset_note": "External audio timeline position/trim applied with packet-boundary precision for stream-copied stems.",
        "audio_processing_note": "Tracks with adjusted volume or fades were re-encoded to AAC. Video and unchanged audio tracks were copied without re-encoding.",
        "main_mix_note": "Main Mix was created from Play-enabled tracks as AAC stereo/48 kHz and set as the first/default audio stream.",
        "main_mix_stream_copy_note": "Main Mix uses direct stream copy of the single unchanged AAC track; source codec and parameters are preserved.",
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
        "remove_cut": "Убрать разрез [Shift+S]",
        "remove_cut_tip": "Объединить два фрагмента по разрезу под playhead. Q/E позволяют точно перейти на разрез.",
        "delete": "Удалить [Delete]",
        "restore": "Восстановить",
        "undo": "Undo [Ctrl+Z]",
        "export_fragment": "Экспорт фрагмента",
        "export_fragment_tip": "Экспортировать только выбранный фрагмент без перекодировки",
        "export_video": "Экспорт видео",
        "export_video_tip": "Включено: сохранить видеоряд. Выключено: экспортировать только выбранные аудиодорожки.",
        "export_audio": "Экспорт звука",
        "export_audio_tip": "Включено: сохранить выбранные аудиодорожки. Выключено: экспортировать только видеоряд.",
        "audio_tracks": "Аудиодорожки…",
        "audio_tracks_count": "Аудиодорожки {selected}/{total}…",
        "audio_tracks_tip": "Выбрать аудиодорожки для экспорта ({selected}/{total}).",
        "audio_tracks_no_file_tip": "Открой видео перед настройкой аудиодорожек.",
        "audio_tracks_none_tip": "Встроенных дорожек нет. Можно добавить внешнее аудио.",
        "audio_tracks_unavailable_tip": "Метаданные встроенного аудио недоступны. Внешнее аудио всё равно можно добавить.",
        "audio_tracks_title": "Аудиодорожки",
        "audio_tracks_intro": "Выбери, какие аудиодорожки доступны на таймлайне проекта и участвуют в экспорте звука. Флаг Play слева от каждой видимой дорожки включает или исключает её из live preview и Main Mix. Внешнее аудио, Main Mix/stems, громкость и Fade находятся в верхнем меню «Аудио».",
        "audio_track_number": "Дорожка {number}",
        "audio_track_channels": "{count} кан.",
        "audio_track_default": "по умолчанию",
        "audio_track_external": "Внешняя: {name}",
        "audio_track_external_stream": "поток {number}",
        "audio_track_volume": "Громкость:",
        "audio_track_volume_tip": "Громкость отдельной дорожки в превью и экспорте. 100% оставляет дорожку без изменений; меньшее значение перекодирует только эту дорожку в AAC, а видео и неизменённые аудиодорожки остаются stream-copy.",
        "audio_track_fade_in": "Fade In:",
        "audio_track_fade_out": "Fade Out:",
        "audio_track_fade_tip": "Длительность плавного появления или затухания в секундах. 0 отключает эффект. Fade применяется к каждому экспортируемому сохранённому диапазону; обработанная дорожка кодируется в AAC, а видео и неизменённые аудиодорожки остаются stream-copy.",
        "audio_tracks_add_external": "Добавить внешнее аудио…",
        "audio_tracks_remove_external_tip": "Убрать эту внешнюю аудиодорожку из проекта",
        "audio_file_dialog": "Добавить внешнее аудио",
        "audio_file_filter": "Аудио/медиа (*.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.mka *.mp4 *.mov *.mkv *.webm);;Все файлы (*.*)",
        "external_audio_no_streams": "В выбранном файле нет аудиопотоков.",
        "external_audio_probe_failed": "Не удалось прочитать аудиопотоки выбранного файла.\n\n{error}",
        "external_audio_duplicate": "Этот аудиофайл уже добавлен в проект. Если звук нужен ещё раз, используй «Создать копию» у его блока на таймлайне.",
        "external_audio_is_source": "Это текущий исходный видеофайл. Используй его встроенные аудиодорожки.",
        "audio_tracks_select_all": "Выбрать все",
        "audio_tracks_select_none": "Снять все",
        "audio_tracks_apply": "Применить",
        "audio_tracks_cancel": "Отмена",
        "audio_tracks_selected": "Выбрано: {selected}/{total}",
        "audio_tracks_status": "Для экспорта выбрано аудиодорожек: {selected}/{total}",
        "audio_main_mix": "Создавать Main Mix из дорожек с активным Play",
        "audio_main_mix_tip": "Создать готовый AAC Main Mix первым аудиопотоком и сделать его дорожкой по умолчанию. В микс входят только видимые дорожки с активным флагом Play с учётом положения на таймлайне, обрезки, громкости и Fade.",
        "audio_keep_stems": "Сохранять отдельные дорожки (stems)",
        "audio_keep_stems_tip": "Сохранить выбранные дорожки отдельными аудиопотоками после Main Mix. Неизменённые stems остаются stream-copy, обработанные — AAC.",
        "audio_timeline": "Аудиодорожки",
        "audio_timeline_empty": "Нет выбранных аудиодорожек для отображения",
        "audio_timeline_drag_tip": "Нажми флаг Play слева, чтобы включить или исключить дорожку из live preview и Main Mix. Перетаскивай внешний аудиоблок для изменения положения; тяни его левый или правый край для обрезки.",
        "audio_track_setting_status": "{setting} изменён для {track}.",
        "audio_track_processing_reset_status": "Громкость и Fade сброшены для {track}.",
        "audio_timeline_offset_status": "Положение внешнего аудио изменено.",
        "audio_timeline_trim_status": "Длительность внешнего аудио изменена.",
        "menu_file": "Файл",
        "menu_edit": "Правка",
        "menu_playback": "Воспроизведение",
        "menu_audio": "Аудио",
        "menu_view": "Вид",
        "menu_help": "Справка",
        "menu_open_video": "Открыть видео…",
        "menu_reset_project": "Сбросить проект",
        "menu_export": "Lossless Export…",
        "menu_export_fragment": "Экспорт выбранного фрагмента…",
        "menu_exit": "Выход",
        "menu_undo": "Undo",
        "menu_redo": "Redo",
        "menu_split": "Разрезать",
        "menu_remove_cut": "Убрать разрез",
        "menu_delete": "Удалить фрагмент",
        "menu_restore": "Восстановить фрагмент",
        "menu_play": "Play",
        "menu_pause": "Pause",
        "menu_prev_cut": "Предыдущий разрез",
        "menu_next_cut": "Следующий разрез",
        "menu_mute": "Mute",
        "menu_audio_tracks": "Доступные аудиодорожки…",
        "menu_add_external_audio": "Добавить внешнее аудио",
        "menu_choose_external_audio": "Выбрать файл…",
        "menu_no_recent_external_audio": "Нет недавних аудиофайлов",
        "menu_duplicate_external_audio": "Создать копию",
        "menu_delete_external_audio_copy": "Удалить копию",
        "external_audio_duplicated_status": "Создана копия: {track}",
        "external_audio_copy_deleted_status": "Копия удалена: {track}",
        "menu_remove_external_audio": "Удалить внешнее аудио",
        "menu_no_external_audio": "Нет внешнего аудио",
        "menu_no_active_audio_tracks": "Нет выбранных аудиодорожек",
        "audio_mix_track_enabled_status": "Добавлено в микс: {track}",
        "audio_mix_track_disabled_status": "Убрано из микса: {track}",
        "menu_track_volume": "Громкость…",
        "menu_track_fade_in": "Fade In…",
        "menu_track_fade_out": "Fade Out…",
        "menu_track_reset_processing": "Сбросить громкость/Fade",
        "audio_track_value_dialog": "{setting} — {track}",
        "menu_zoom_in": "Приблизить",
        "menu_zoom_out": "Отдалить",
        "menu_zoom_reset": "Сбросить масштаб",
        "menu_show_audio_tracks": "Показывать аудиодорожки",
        "menu_language": "Язык",
        "menu_language_en": "English",
        "menu_language_ru": "Русский",
        "menu_help_contents": "Справка и горячие клавиши",
        "help": "Справка [F1]",
        "help_tip": "Открыть справку и список горячих клавиш",
        "language_tip": "Язык интерфейса",
        "cancel_export": "Отмена экспорта",
        "task_export_title": "Lossless Export",
        "task_export_preparing": "Подготавливаю экспорт…",
        "task_keyframe_title": "Анализ видео",
        "task_keyframe_hint": "Можно продолжать монтаж, пока анализируются keyframes.",
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
        "opened_with_audio": "Открыт: {name} • аудиодорожек: {count}",
        "opened_audio_probe_failed": "Открыт: {name} • метаданные аудио недоступны",
        "previous_cut_status": "Предыдущий разрез: {time}",
        "next_cut_status": "Следующий разрез: {time}",
        "state_deleted": "УДАЛЁН",
        "state_kept": "оставляем",
        "segment_info": "Фрагмент {number}: {start} → {end} ({duration}) • {state}",
        "playhead_boundary": "Playhead уже находится на границе фрагмента.",
        "split_status": "Разрез: {time}",
        "no_cut_at_playhead": "Под playhead нет разреза. Используй Q/E, чтобы точно перейти на разрез.",
        "cut_state_mismatch": "Этот разрез разделяет оставляемый и удалённый фрагменты. Сначала восстанови или удали обе стороны одинаково.",
        "cut_removed_status": "Разрез убран: {time}",
        "marked_deleted": "Фрагмент помечен на удаление.",
        "restored": "Фрагмент восстановлен.",
        "preview_nothing_to_play": "Все видеофрагменты удалены — воспроизводить нечего.",
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
        "show_details": "Подробнее...",
        "hide_details": "Скрыть подробности",
        "open_result_folder": "Открыть папку с результатом",
        "folder_open_failed": "Не удалось открыть папку с результатом.",
        "export_cancelled": "Экспорт отменён.",
        "export_error_status": "Ошибка экспорта.",
        "export_failed": "Экспорт не удался.\n\n{error}",
        "export_no_streams": "Не выбран ни один поток для экспорта.",
        "scan_keyframes": "Сканирую keyframes…",
        "keyframe_scan_started": "Анализирую keyframes…",
        "keyframe_scan_progress": "Анализирую keyframes… {percent}%",
        "keyframe_scan_finished": "Keyframes готовы: {count}",
        "keyframe_scan_failed_status": "Анализ keyframes недоступен.",
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
        "external_offset_note": "Положение/обрезка внешнего аудио применены с точностью по границам аудиопакетов для stream-copy stems.",
        "audio_processing_note": "Дорожки с изменённой громкостью или Fade перекодированы в AAC. Видео и неизменённые аудиодорожки скопированы без перекодирования.",
        "main_mix_note": "Main Mix создан из дорожек с активным флагом Play как AAC stereo/48 kHz и установлен первым аудиопотоком/дорожкой по умолчанию.",
        "main_mix_stream_copy_note": "Main Mix использует прямой stream copy единственной неизменённой AAC-дорожки; исходный кодек и параметры сохранены.",
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
  <li>Less-frequent commands are grouped in the top <b>File / Edit / Playback / Audio / View / Help</b> menus.</li>
  <li><b>View → Language</b> switches English / Russian and saves the choice for future launches.</li>
</ul>
<h3>Playback and navigation</h3>
<ul>
  <li><b>Play / Pause [Space]</b> — plays the edited result: deleted gaps are skipped using the same effective keyframe boundaries as lossless export. Manual seeking can still inspect deleted source frames while paused.</li>
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
  <li><b>Remove cut [Shift+S]</b> — merge the two adjacent segments when the playhead is exactly on a cut. Q/E can be used to jump to a cut.</li>
  <li><b>Delete [Delete]</b> — exclude the selected segment from the main export.</li>
  <li><b>Restore</b> — restore a deleted segment.</li>
  <li><b>Undo [Ctrl+Z]</b> / <b>Redo [Ctrl+Y]</b> — undo / redo an edit.</li>
</ul>
<h3>Export</h3>
<ul>
  <li><b>Lossless Export</b> — export all kept segments; video remains stream-copied while Main Mix and other processed audio are encoded only when required.</li>
  <li><b>Export segment</b> — save only the selected segment.</li>
  <li>The selected segment can be exported even if it is marked for deletion in the main edit.</li>
  <li><b>Export video</b> and <b>Export audio</b> are enabled by default.</li>
  <li><b>Audio → Available audio tracks…</b> controls which embedded/external tracks are visible on the project timeline and available for audio export. Every visible track is listed directly in the <b>Audio</b> menu with its own Volume/Fade submenu. External clips can be duplicated from their submenu or by right-clicking the clip on the timeline. A duplicated clip can also be removed with <b>Delete copy</b> from its right-click menu.</li>
  <li><b>Audio → Add external audio</b> contains <b>Choose file…</b> plus up to 10 most recently added audio files, persisted between app sessions.</li>
  <li>The <b>Play flag</b> at the left of each visible audio row controls mix membership: ▶ is included in live preview and Main Mix, ▷ is excluded. A newly opened video starts with only its first embedded audio track in the mix; newly added external audio is included by default. Stems remain independently available when enabled.</li>
  <li>External tracks are positioned and trimmed directly on the timeline: drag the block to move it earlier/later, or drag its left/right edge to trim the beginning/end.</li>
  <li>The <b>Audio Tracks</b> area visualizes embedded and external tracks on the same zoomed project-time scale as the video timeline. It keeps a stable viewport height and scrolls vertically when many selected tracks are present, so changing audio configuration does not resize the video preview. Unselected tracks are hidden.</li>
  <li><b>Create Main Mix</b> makes a ready-to-play AAC mix as the first/default audio stream and is enabled by default. <b>Keep separate tracks (stems)</b> is an optional advanced mode that preserves the selected tracks after it. Either option can be used on its own.</li>
  <li>You can export video + audio, video only, or audio only.</li>
  <li><b>Video output containers:</b> MP4, MOV, MKV. Other input containers default to MKV.</li>
  <li>If both stream checkboxes are disabled, export buttons are disabled.</li>
  <li>Audio-only export uses <b>MKA</b>. Tracks at 100% with no fades remain stream-copied; tracks with volume or fade processing are encoded to AAC.</li>
  <li>Export can be cancelled while it is running.</li>
  <li>After a successful export you can open the result folder.</li>
</ul>
<h3>Important lossless limitation</h3>
<p>VFR FastCut keeps video and unchanged separate audio streams in FFmpeg stream-copy mode (<b>-c copy</b>). Main Mix is encoded once to AAC and placed as the first/default audio stream; selected stems can optionally be kept after it. A stem whose volume differs from 100% or whose Fade In/Fade Out is non-zero is also filtered and encoded to AAC. Fade is applied independently to each exported kept range. When video is exported, cut boundaries are snapped to keyframes and may differ slightly from the requested position. Audio-only export does not require video keyframe snapping and cuts on audio packet boundaries.</p>
<h3>Hotkeys</h3>
<table cellspacing="4" cellpadding="3">
<tr><td><b>Ctrl+O</b></td><td>Open video</td></tr>
<tr><td><b>Ctrl+N</b></td><td>Reset project</td></tr>
<tr><td><b>Space</b></td><td>Play / Pause</td></tr>
<tr><td><b>M</b></td><td>Mute preview</td></tr>
<tr><td><b>S</b></td><td>Split</td></tr>
<tr><td><b>Shift+S</b></td><td>Remove cut at playhead</td></tr>
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
  <li>Редкие команды собраны в верхних меню <b>Файл / Правка / Воспроизведение / Аудио / Вид / Справка</b>.</li>
  <li><b>Вид → Язык</b> переключает русский / английский и сохраняет выбор для следующих запусков.</li>
</ul>
<h3>Просмотр и навигация</h3>
<ul>
  <li><b>Play / Pause [Space]</b> — воспроизводит будущий результат монтажа: удалённые участки пропускаются по тем же эффективным keyframe-границам, что и lossless export. На паузе ручной seek по удалённым кадрам остаётся доступен.</li>
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
  <li><b>Убрать разрез [Shift+S]</b> — объединить соседние фрагменты, когда playhead точно стоит на разрезе. Для перехода на разрез удобно использовать Q/E.</li>
  <li><b>Удалить [Delete]</b> — исключить выбранный фрагмент из общего экспорта.</li>
  <li><b>Восстановить</b> — вернуть удалённый фрагмент.</li>
  <li><b>Undo [Ctrl+Z]</b> / <b>Redo [Ctrl+Y]</b> — отменить / вернуть изменение.</li>
</ul>
<h3>Экспорт</h3>
<ul>
  <li><b>Lossless Export</b> — экспортировать все неудалённые фрагменты; видеоряд остаётся stream-copy, а Main Mix и другой обрабатываемый звук кодируются только при необходимости.</li>
  <li><b>Экспорт фрагмента</b> — сохранить только текущий выбранный фрагмент в отдельный файл.</li>
  <li>Экспорт выбранного фрагмента работает независимо от того, отмечен он на удаление или нет.</li>
  <li><b>Экспорт видео</b> и <b>Экспорт звука</b> включены по умолчанию.</li>
  <li><b>Аудио → Доступные аудиодорожки…</b> отвечает за выбор встроенных/внешних дорожек, которые видны на таймлайне и доступны для экспорта звука. Каждая видимая дорожка отображается прямо в меню <b>Аудио</b> со своим подменю Volume/Fade. Внешний клип можно скопировать из его подменю или через правый клик по блоку на таймлайне.</li>
  <li><b>Аудио → Добавить внешнее аудио</b> содержит пункт <b>Выбрать файл…</b> и до 10 последних добавленных аудиофайлов; список сохраняется между запусками программы.</li>
  <li><b>Флаг Play</b> слева от каждой видимой аудиодорожки управляет участием в миксе: ▶ входит в live preview и Main Mix, ▷ исключена. При открытии видео в миксе по умолчанию активна только первая встроенная дорожка; новое внешнее аудио сразу добавляется активным. Отдельные stems при этом сохраняются независимо, если их экспорт включён.</li>
  <li>Внешнее аудио позиционируется и обрезается прямо на таймлайне: блок перемещает дорожку, левый/правый край сокращает начало/конец.</li>
  <li>Область <b>Аудиодорожки</b> показывает встроенные и внешние дорожки на той же масштабированной временной шкале, что и видео. Высота области стабильна, а при большом числе выбранных дорожек появляется вертикальный скроллинг, поэтому конфигурация аудио больше не меняет размер preview; снятые с экспорта дорожки скрываются.</li>
  <li><b>Создавать Main Mix</b> формирует готовый AAC-микс первым аудиопотоком, делает его дорожкой по умолчанию и включён по умолчанию. <b>Сохранять отдельные дорожки (stems)</b> — дополнительный режим для продвинутого экспорта; по умолчанию он выключен.</li>
  <li>Можно экспортировать видео со звуком, только видео или только звук.</li>
  <li><b>Контейнеры для вывода видео:</b> MP4, MOV, MKV. Для остальных входных контейнеров по умолчанию предлагается MKV.</li>
  <li>Если снять обе галочки, кнопки экспорта становятся недоступны.</li>
  <li>При экспорте только звука используется контейнер <b>MKA</b>. Дорожки на 100% без Fade копируются без перекодирования; дорожки с изменённой громкостью или Fade кодируются в AAC.</li>
  <li>Во время экспорта можно нажать <b>Отмена экспорта</b>.</li>
  <li>После завершения доступна кнопка <b>Открыть папку с результатом</b>.</li>
</ul>
<h3>Важно о Lossless</h3>
<p>VFR FastCut сохраняет видео и неизменённые отдельные аудиодорожки в режиме FFmpeg stream copy (<b>-c copy</b>). Main Mix один раз кодируется в AAC и помещается первым аудиопотоком/дорожкой по умолчанию; выбранные stems при желании сохраняются после него. Stem с громкостью, отличной от 100%, или ненулевым Fade In/Fade Out также обрабатывается и кодируется в AAC. Fade применяется отдельно к каждому экспортируемому сохранённому диапазону. Если экспортируется видео, границы привязываются к keyframes и могут немного отличаться от выбранной позиции. При экспорте только звука keyframe-привязка не нужна: границы идут по аудиопакетам.</p>
<h3>Горячие клавиши</h3>
<table cellspacing="4" cellpadding="3">
<tr><td><b>Ctrl+O</b></td><td>Открыть видео</td></tr>
<tr><td><b>Ctrl+N</b></td><td>Сбросить проект</td></tr>
<tr><td><b>Space</b></td><td>Play / Pause</td></tr>
<tr><td><b>M</b></td><td>Mute preview</td></tr>
<tr><td><b>S</b></td><td>Разрезать</td></tr>
<tr><td><b>Shift+S</b></td><td>Убрать разрез под playhead</td></tr>
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


@dataclass
class AudioTrack:
    """One embedded or external audio stream available to the project."""

    stream_index: int
    audio_index: int
    source_path: str
    codec_name: str = ""
    channels: int = 0
    channel_layout: str = ""
    sample_rate: int = 0
    bit_rate: int = 0
    language: str = ""
    title: str = ""
    is_default: bool = False
    export_enabled: bool = True
    source_type: str = "embedded"
    offset_seconds: float = 0.0
    volume_percent: int = 100
    duration_seconds: float = 0.0
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0
    trim_start_seconds: float = 0.0
    trim_end_seconds: float = 0.0
    mix_enabled: bool = True
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    copy_number: int = 1


def _external_source_window(track: AudioTrack) -> tuple[float, float]:
    """Return the usable source-time window after edge trimming."""
    duration = max(0.0, float(track.duration_seconds))
    trim_start = max(0.0, float(track.trim_start_seconds))
    trim_end = max(0.0, float(track.trim_end_seconds))

    if duration <= 0:
        return trim_start, 0.0

    min_clip = min(0.010, duration)
    trim_start = min(trim_start, max(0.0, duration - min_clip))
    trim_end = min(trim_end, max(0.0, duration - trim_start - min_clip))
    source_end = max(trim_start + min_clip, duration - trim_end)
    return trim_start, min(duration, source_end)


def _external_project_window(track: AudioTrack) -> tuple[float, float]:
    """Return external clip boundaries on the project timeline."""
    source_start, source_end = _external_source_window(track)
    if track.duration_seconds <= 0:
        return track.offset_seconds + source_start, float("inf")
    return (
        track.offset_seconds + source_start,
        track.offset_seconds + source_end,
    )


def _track_has_trim(track: AudioTrack) -> bool:
    return (
        track.source_type == "external"
        and (
            track.trim_start_seconds > 0.0005
            or track.trim_end_seconds > 0.0005
        )
    )


def _safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _track_volume_changed(track: AudioTrack) -> bool:
    return int(track.volume_percent) != 100


def _track_has_fade(track: AudioTrack) -> bool:
    return track.fade_in_seconds > 0.0005 or track.fade_out_seconds > 0.0005


def _track_requires_processing(track: AudioTrack) -> bool:
    return _track_volume_changed(track) or _track_has_fade(track)


def _track_filter_chain(track: AudioTrack, duration: float) -> str:
    """Build one linear volume/fade chain for a zero-based audio clip."""
    clip_duration = max(0.0, float(duration))
    filters: list[str] = []

    if _track_volume_changed(track):
        gain = max(0.0, min(1.0, track.volume_percent / 100.0))
        filters.append(f"volume={gain:.6f}")

    fade_in = min(max(0.0, track.fade_in_seconds), clip_duration)
    if fade_in > 0.0005:
        filters.append(f"afade=t=in:st=0:d={fade_in:.6f}:curve=tri")

    fade_out = min(max(0.0, track.fade_out_seconds), clip_duration)
    if fade_out > 0.0005:
        fade_out_start = max(0.0, clip_duration - fade_out)
        filters.append(
            f"afade=t=out:st={fade_out_start:.6f}:d={fade_out:.6f}:curve=tri"
        )

    return ",".join(filters)


def probe_audio_tracks(
    ffprobe: str,
    input_path: str,
    source_type: str = "embedded",
) -> list[AudioTrack]:
    """Read audio-stream metadata without decoding media."""
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-select_streams", "a",
            "-show_streams",
            "-show_format",
            "-of", "json",
            input_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
        check=False,
    )

    if result.returncode != 0:
        details = (result.stderr or "").strip()[-2000:]
        raise RuntimeError(details or "ffprobe could not read audio streams")

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid audio metadata") from exc

    format_info = payload.get("format") or {}
    format_duration = max(0.0, _safe_float(format_info.get("duration")))

    tracks: list[AudioTrack] = []
    for audio_index, stream in enumerate(payload.get("streams", [])):
        tags = stream.get("tags") or {}
        disposition = stream.get("disposition") or {}
        stream_duration = max(0.0, _safe_float(stream.get("duration")))
        tracks.append(
            AudioTrack(
                stream_index=_safe_int(stream.get("index")),
                audio_index=audio_index,
                source_path=input_path,
                codec_name=str(stream.get("codec_name") or ""),
                channels=_safe_int(stream.get("channels")),
                channel_layout=str(stream.get("channel_layout") or ""),
                sample_rate=_safe_int(stream.get("sample_rate")),
                bit_rate=_safe_int(stream.get("bit_rate")),
                duration_seconds=stream_duration or format_duration,
                language=str(tags.get("language") or ""),
                title=str(tags.get("title") or ""),
                is_default=bool(_safe_int(disposition.get("default"))),
                source_type=source_type,
            )
        )

    return tracks


def clone_segments(segments: list[Segment]) -> list[Segment]:
    """Fast value-copy for undo/redo/export snapshots."""
    return [
        Segment(seg.start, seg.end, seg.deleted)
        for seg in segments
    ]


def kept_ranges_from_segments(
    segments: list[Segment],
) -> list[tuple[float, float]]:
    """Return contiguous non-deleted project ranges in timeline order."""
    ranges: list[tuple[float, float]] = []
    for seg in segments:
        if seg.deleted or seg.duration <= 0.001:
            continue
        if ranges and abs(ranges[-1][1] - seg.start) < 0.002:
            ranges[-1] = (ranges[-1][0], seg.end)
        else:
            ranges.append((seg.start, seg.end))
    return ranges


class SafePreviewWidget(QWidget):
    '''Raster preview that deliberately avoids QVideoWidget/native video surfaces.

    QMediaPlayer still performs normal media decoding (including hardware decode
    when Qt selects it), but decoded frames are converted to QImage and painted
    through the regular QWidget backing store. This keeps video presentation out
    of the dedicated native/video-surface path that can interact badly with
    VRR/G-SYNC/MPO on some Windows/NVIDIA configurations.
    '''

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


class PreviewMixChannel(QObject):
    """One audio-only QMediaPlayer participating in live preview mix.

    Every selected/displayed project track gets its own player/output. The main
    QMediaPlayer remains the video/transport clock; channels are hard-synced on
    play, seek and timeline timing edits, then allowed to run freely to avoid
    the micro-seek crackle fixed in the 0.3.x preview path.
    """

    def __init__(self, track: AudioTrack, parent=None):
        super().__init__(parent)
        self.track = track
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(1.0)
        self._last_gain = 1.0
        self.player.setAudioOutput(self.audio)

        # A newly enabled mix channel loads its media asynchronously. setPosition()
        # can be ignored if it happens before the source reaches LoadedMedia, so
        # always remember the transport request and re-apply it once the media
        # and stream list are ready. This keeps a re-enabled track at the current
        # project playhead instead of letting it restart from 00:00.
        self._pending_project_position_ms = 0
        self._pending_transport_state = QMediaPlayer.PlaybackState.PausedState
        self.player.tracksChanged.connect(self._sync_stream_selection)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.setSource(QUrl.fromLocalFile(track.source_path))

    def _sync_stream_selection(self):
        audio_tracks = self.player.audioTracks()
        if audio_tracks:
            index = max(0, min(self.track.audio_index, len(audio_tracks) - 1))
            if self.player.activeAudioTrack() != index:
                self.player.setActiveAudioTrack(index)
        if self.player.videoTracks() and self.player.activeVideoTrack() != -1:
            self.player.setActiveVideoTrack(-1)

        # tracksChanged may arrive after the first transport sync request. Once
        # the requested stream exists, align it to the current project position.
        self._resync_pending_transport()

    def _on_media_status_changed(self, status):
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            # _sync_stream_selection() already reapplies the pending
            # transport request once the media is ready. Avoid a second
            # identical hard seek on the same media-status event.
            self._sync_stream_selection()

    def _resync_pending_transport(self):
        if self.player.mediaStatus() not in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            return
        self.sync_transport(
            self._pending_project_position_ms,
            self._pending_transport_state,
            force_seek=True,
        )

    def set_gain(self, gain: float):
        """Update QAudioOutput only when the effective gain actually changed."""
        gain = max(0.0, min(1.0, float(gain)))
        if abs(gain - self._last_gain) <= 0.0005:
            return
        self._last_gain = gain
        self.audio.setVolume(gain)

    def stop_and_clear(self):
        self.player.stop()
        self.player.setSource(QUrl())

    def _source_target_ms(self, project_position_ms: int) -> tuple[int, int, int]:
        """Return target/source-start/source-end in milliseconds.

        source_end <= 0 means unknown/unbounded duration.
        """
        project_seconds = max(0.0, project_position_ms / 1000.0)
        if self.track.source_type == "external":
            source_start, source_end = _external_source_window(self.track)
            target_seconds = project_seconds - self.track.offset_seconds
            end_ms = (
                int(round(source_end * 1000.0))
                if self.track.duration_seconds > 0
                else 0
            )
            return (
                int(round(target_seconds * 1000.0)),
                int(round(source_start * 1000.0)),
                end_ms,
            )

        end_seconds = (
            self.track.duration_seconds
            if self.track.duration_seconds > 0
            else 0.0
        )
        return (
            int(project_position_ms),
            0,
            int(round(end_seconds * 1000.0)) if end_seconds > 0 else 0,
        )

    def sync_transport(
        self,
        project_position_ms: int,
        transport_state,
        force_seek: bool = False,
    ):
        self._pending_project_position_ms = int(project_position_ms)
        self._pending_transport_state = transport_state

        target_ms, source_start_ms, source_end_ms = self._source_target_ms(
            project_position_ms
        )

        before_start = target_ms < source_start_ms
        after_end = source_end_ms > 0 and target_ms >= source_end_ms
        if before_start or after_end:
            boundary = source_start_ms if before_start else max(0, source_end_ms - 1)
            if force_seek or abs(self.player.position() - boundary) > 120:
                self.player.setPosition(boundary)
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            return

        # During normal playback never chase small clock differences with
        # repeated seeks. All channels are aligned at explicit sync points.
        should_seek = force_seek or (
            transport_state != QMediaPlayer.PlaybackState.PlayingState
            and abs(self.player.position() - target_ms) > 120
        )
        if should_seek:
            self.player.setPosition(max(0, target_ms))

        current_state = self.player.playbackState()
        if transport_state == QMediaPlayer.PlaybackState.PlayingState:
            if current_state != QMediaPlayer.PlaybackState.PlayingState:
                self.player.play()
        elif current_state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()


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
        self.keyframes: list[float] = []
        self.keyframe_min_spacing_px = 6.0

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

    def set_keyframes(self, keyframes: list[float]):
        normalized = sorted(set(float(value) for value in keyframes if value >= 0.0))
        if normalized == self.keyframes:
            return
        self.keyframes = normalized
        self.update()

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

        # ---- keyframe map ----
        # Keep keyframe markers in their own narrow lane between the time ruler
        # and the video track.  This avoids visual collisions with ruler ticks.
        # Visibility is based on the representative *actual* keyframe spacing
        # on screen, so zooming does not make the whole marker set flicker merely
        # because one keyframe entered or left the viewport.
        if self.keyframes:
            first = bisect.bisect_left(self.keyframes, vis_start - 1e-9)
            last = bisect.bisect_right(self.keyframes, vis_end + 1e-9)
            visible_count = max(0, last - first)

            # A dense viewport can be rejected without slicing and sorting
            # thousands of timestamps on every playhead repaint. If there are
            # more markers than the lane can physically fit at the configured
            # minimum spacing, drawing the complete truthful keyframe set would
            # necessarily overlap, so hide it immediately.
            marker_capacity = max(
                2,
                int(width / max(1.0, self.keyframe_min_spacing_px)) + 2,
            )
            show_keyframes = 0 < visible_count <= marker_capacity
            visible_keyframes = (
                self.keyframes[first:last] if show_keyframes else []
            )

            if show_keyframes:
                # Include one neighbour outside each side when available.  It
                # keeps the actual-spacing estimate stable while panning near
                # viewport edges. The hard density cap above keeps this slice
                # small even on multi-hour VODs.
                spacing_first = max(0, first - 1)
                spacing_last = min(len(self.keyframes), last + 1)
                spacing_keyframes = self.keyframes[spacing_first:spacing_last]

                if len(spacing_keyframes) > 1:
                    px_per_second = width / max(0.001, self.visible_duration)
                    gaps_px = sorted(
                        max(0.0, b - a) * px_per_second
                        for a, b in zip(
                            spacing_keyframes,
                            spacing_keyframes[1:],
                        )
                        if b > a
                    )
                    if gaps_px:
                        # Median spacing is robust to an occasional unusually
                        # close scene-change keyframe.
                        representative_spacing_px = gaps_px[len(gaps_px) // 2]
                        show_keyframes = (
                            representative_spacing_px
                            >= self.keyframe_min_spacing_px
                        )

            if show_keyframes:
                lane_top = self.RULER_H + 1
                lane_bottom = max(lane_top, self.TRACK_Y - 2)
                painter.setPen(QPen(QColor(145, 145, 145, 205), 1))
                for keyframe in visible_keyframes:
                    x = self._x_from_time(keyframe)
                    if -1 <= x <= width + 1:
                        painter.drawLine(
                            int(x),
                            lane_top,
                            int(x),
                            lane_bottom,
                        )

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
            painter.drawLine(int(x), 0, int(x), self.height())


class AudioTimelineWidget(QWidget):
    """Project-time audio rows aligned with the main video timeline.

    Only tracks selected for export are supplied by MainWindow. The Play flag
    beside each row controls membership in live preview/Main Mix independently
    of stem availability. External tracks can be moved and trimmed directly on
    the shared project timeline.
    """

    trackTimingChanged = Signal(object, str)
    trackTimingDragFinished = Signal(object, str)
    trackMixToggled = Signal(object, bool)
    trackContextRequested = Signal(object, object)

    ROW_H = 30
    SELECTOR_W = 34
    LABEL_W = 230
    PAD = 0
    HANDLE_W = 7
    MIN_CLIP_SECONDS = 0.010

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 0.0
        self.position = 0.0
        self.tracks: list[AudioTrack] = []
        self.segments: list[Segment] = []
        self.view_offset = 0.0
        self.visible_duration = 0.0
        self.empty_text = UI_TEXT["en"]["audio_timeline_empty"]

        self._drag_track: Optional[AudioTrack] = None
        self._drag_mode = ""
        self._drag_start_x = 0.0
        self._drag_start_offset = 0.0
        self._drag_start_trim_start = 0.0
        self._drag_start_trim_end = 0.0
        self._drag_moved = False

        self.setMinimumHeight(self.ROW_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

    def set_empty_text(self, text: str):
        if text == self.empty_text:
            return
        self.empty_text = text
        self.update()

    def set_state(
        self,
        duration: float,
        tracks: list[AudioTrack],
        segments: list[Segment],
        position: float,
        view_offset: float,
        visible_duration: float,
    ):
        self.duration = max(0.0, float(duration))
        self.tracks = list(tracks)
        self.segments = segments
        self.position = max(0.0, min(self.duration, float(position)))
        self.view_offset = max(0.0, float(view_offset))
        self.visible_duration = max(0.0, float(visible_duration))

        # Content may grow to any number of selected tracks. The surrounding
        # QScrollArea owns the visible height, so adding/removing tracks cannot
        # steal vertical space from the video preview or resize the controls.
        row_count = max(1, len(self.tracks))
        height = self.PAD * 2 + self.ROW_H * row_count
        self.setFixedHeight(height)
        self.updateGeometry()
        self.update()

    def set_position(self, position: float):
        self.position = max(0.0, min(self.duration, float(position)))
        self.update()

    def set_view(self, offset: float, visible_duration: float):
        self.view_offset = max(0.0, float(offset))
        self.visible_duration = max(0.0, float(visible_duration))
        self.update()

    def _label_width(self) -> int:
        if self.width() <= 0:
            return self.LABEL_W
        return max(160, min(self.LABEL_W, int(self.width() * 0.32)))

    def _visible_window(self) -> tuple[float, float]:
        if self.duration <= 0:
            return 0.0, 0.0
        visible = self.visible_duration if self.visible_duration > 0 else self.duration
        start = max(0.0, min(self.view_offset, self.duration))
        end = min(self.duration, start + visible)
        if end <= start:
            end = self.duration
        return start, end

    def _timeline_width(self) -> float:
        return max(1.0, float(self.width() - self.SELECTOR_W))

    def _x_from_time(self, t: float) -> float:
        vis_start, vis_end = self._visible_window()
        if vis_end <= vis_start:
            return float(self.SELECTOR_W)
        ratio = (t - vis_start) / (vis_end - vis_start)
        return self.SELECTOR_W + ratio * self._timeline_width()

    def _seconds_per_pixel(self) -> float:
        vis_start, vis_end = self._visible_window()
        if vis_end <= vis_start:
            return 0.0
        return (vis_end - vis_start) / self._timeline_width()

    def _track_bounds(self, track: AudioTrack) -> tuple[float, float]:
        if self.duration <= 0:
            return 0.0, 0.0

        if track.source_type != "external":
            end = track.duration_seconds if track.duration_seconds > 0 else self.duration
            return 0.0, min(self.duration, max(0.0, end))

        project_start, project_end = _external_project_window(track)
        if not math.isfinite(project_end):
            project_end = self.duration
        return (
            max(0.0, min(self.duration, project_start)),
            max(0.0, min(self.duration, project_end)),
        )

    def _clamp_external_offset(self, track: AudioTrack, offset: float) -> float:
        """Keep at least a tiny visible part of a moved external clip."""
        if self.duration <= 0:
            return float(offset)

        source_start, source_end = _external_source_window(track)
        if track.duration_seconds <= 0:
            return max(-self.duration, min(self.duration, float(offset)))

        minimum = -source_end + self.MIN_CLIP_SECONDS
        maximum = self.duration - source_start - self.MIN_CLIP_SECONDS
        return max(minimum, min(maximum, float(offset)))

    def _clamp_trim_start(self, track: AudioTrack, value: float) -> float:
        duration = max(0.0, track.duration_seconds)
        if duration <= 0:
            return max(0.0, float(value))
        max_trim = max(
            0.0,
            duration - max(0.0, track.trim_end_seconds) - self.MIN_CLIP_SECONDS,
        )
        return max(0.0, min(max_trim, float(value)))

    def _clamp_trim_end(self, track: AudioTrack, value: float) -> float:
        duration = max(0.0, track.duration_seconds)
        if duration <= 0:
            return 0.0
        max_trim = max(
            0.0,
            duration - max(0.0, track.trim_start_seconds) - self.MIN_CLIP_SECONDS,
        )
        return max(0.0, min(max_trim, float(value)))

    def _external_hit_test(
        self,
        x: float,
        y: float,
    ) -> Optional[tuple[AudioTrack, str]]:
        if not self.tracks or y < self.PAD or x < self.SELECTOR_W:
            return None

        index = int((y - self.PAD) // self.ROW_H)
        if not (0 <= index < len(self.tracks)):
            return None

        track = self.tracks[index]
        if track.source_type != "external":
            return None

        vis_start, vis_end = self._visible_window()
        project_start, project_end = _external_project_window(track)
        if not math.isfinite(project_end):
            project_end = self.duration

        draw_start = max(project_start, vis_start, 0.0)
        draw_end = min(project_end, vis_end, self.duration)
        if draw_end <= draw_start:
            return None

        x1 = self._x_from_time(draw_start)
        x2 = self._x_from_time(draw_end)
        if not (x1 - 2 <= x <= x2 + 2):
            return None

        # An edge can be trimmed only when the real clip boundary is visible;
        # a viewport-clipped edge must continue to behave as body drag.
        if vis_start <= project_start <= vis_end:
            left_x = self._x_from_time(project_start)
            if abs(x - left_x) <= self.HANDLE_W:
                return track, "trim_start"
        if vis_start <= project_end <= vis_end:
            right_x = self._x_from_time(project_end)
            if abs(x - right_x) <= self.HANDLE_W:
                return track, "trim_end"

        return track, "move"

    @staticmethod
    def _track_label(track: AudioTrack) -> str:
        if track.source_type == "external":
            suffix = f" #{track.copy_number}" if track.copy_number > 1 else ""
            return f"EXT • {Path(track.source_path).name}{suffix}"

        base = f"A{track.audio_index + 1}"
        detail = track.title.strip() if track.title else ""
        if not detail and track.codec_name:
            detail = track.codec_name.upper()
        return f"{base} • {detail}" if detail else base

    @staticmethod
    def _track_badge(track: AudioTrack) -> str:
        parts: list[str] = []
        if track.volume_percent != 100:
            parts.append(f"{track.volume_percent}%")
        if track.fade_in_seconds > 0.0005:
            parts.append(f"FI {track.fade_in_seconds:g}s")
        if track.fade_out_seconds > 0.0005:
            parts.append(f"FO {track.fade_out_seconds:g}s")
        return " • ".join(parts)

    def _track_at_y(self, y: float) -> Optional[AudioTrack]:
        if y < self.PAD:
            return None
        index = int((y - self.PAD) // self.ROW_H)
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def _selector_track_at(self, x: float, y: float) -> Optional[AudioTrack]:
        if not (0 <= x < self.SELECTOR_W):
            return None
        return self._track_at_y(y)

    def _cursor_for_hit(self, hit: Optional[tuple[AudioTrack, str]]):
        if hit is None:
            return Qt.CursorShape.ArrowCursor
        return (
            Qt.CursorShape.SizeHorCursor
            if hit[1].startswith("trim_")
            else Qt.CursorShape.OpenHandCursor
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            context_track = self._track_at_y(event.position().y())
            if context_track is not None:
                self.trackContextRequested.emit(
                    context_track,
                    event.globalPosition().toPoint(),
                )
                event.accept()
                return
            super().mousePressEvent(event)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        selector_track = self._selector_track_at(
            event.position().x(),
            event.position().y(),
        )
        if selector_track is not None:
            self.trackMixToggled.emit(
                selector_track,
                not bool(selector_track.mix_enabled),
            )
            event.accept()
            return

        hit = self._external_hit_test(
            event.position().x(),
            event.position().y(),
        )
        if hit is None:
            super().mousePressEvent(event)
            return

        track, mode = hit
        self._drag_track = track
        self._drag_mode = mode
        self._drag_start_x = event.position().x()
        self._drag_start_offset = track.offset_seconds
        self._drag_start_trim_start = track.trim_start_seconds
        self._drag_start_trim_end = track.trim_end_seconds
        self._drag_moved = False
        self.setCursor(
            Qt.CursorShape.ClosedHandCursor
            if mode == "move"
            else Qt.CursorShape.SizeHorCursor
        )
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_track is not None:
            seconds_per_pixel = self._seconds_per_pixel()
            delta_x = event.position().x() - self._drag_start_x
            delta_seconds = delta_x * seconds_per_pixel
            track = self._drag_track

            if self._drag_mode == "move":
                new_value = round(
                    self._clamp_external_offset(
                        track,
                        self._drag_start_offset + delta_seconds,
                    ),
                    3,
                )
                changed = abs(new_value - track.offset_seconds) > 0.0005
                if changed:
                    track.offset_seconds = new_value
            elif self._drag_mode == "trim_start":
                new_value = round(
                    self._clamp_trim_start(
                        track,
                        self._drag_start_trim_start + delta_seconds,
                    ),
                    3,
                )
                changed = abs(new_value - track.trim_start_seconds) > 0.0005
                if changed:
                    track.trim_start_seconds = new_value
            else:  # trim_end
                new_value = round(
                    self._clamp_trim_end(
                        track,
                        self._drag_start_trim_end - delta_seconds,
                    ),
                    3,
                )
                changed = abs(new_value - track.trim_end_seconds) > 0.0005
                if changed:
                    track.trim_end_seconds = new_value

            if changed:
                self._drag_moved = True
                self.trackTimingChanged.emit(track, self._drag_mode)
                self.update()
            event.accept()
            return

        if self._selector_track_at(
            event.position().x(),
            event.position().y(),
        ) is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            hit = self._external_hit_test(
                event.position().x(),
                event.position().y(),
            )
            self.setCursor(self._cursor_for_hit(hit))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._drag_track is not None
        ):
            track = self._drag_track
            mode = self._drag_mode
            moved = self._drag_moved
            self._drag_track = None
            self._drag_mode = ""
            self._drag_moved = False
            hit = self._external_hit_test(
                event.position().x(),
                event.position().y(),
            )
            self.setCursor(self._cursor_for_hit(hit))
            if moved:
                self.trackTimingDragFinished.emit(track, mode)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if self._drag_track is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        bg = self.palette().window().color().darker(106)
        painter.fillRect(self.rect(), bg)

        def draw_outlined_text(rect: QRectF, flags, text: str):
            if not text:
                return
            outline = QColor(0, 0, 0, 220)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                painter.setPen(outline)
                painter.drawText(rect.translated(dx, dy), flags, text)
            painter.setPen(QColor(245, 245, 245, 235))
            painter.drawText(rect, flags, text)

        if self.duration <= 0 or not self.tracks:
            painter.setPen(self.palette().text().color())
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                self.empty_text,
            )
            return

        label_w = self._label_width()
        vis_start, vis_end = self._visible_window()

        # The fixed selector lane contains one Play flag per visible track.
        # Filled Play means the track participates in both live preview and the
        # exported Main Mix; outline Play keeps the track visible/stem-capable
        # but excludes it from the mix.
        painter.fillRect(
            QRectF(0, 0, self.SELECTOR_W, self.height()),
            self.palette().base().color().darker(118),
        )
        painter.setPen(QPen(QColor(60, 60, 60, 180), 1))
        painter.drawLine(
            self.SELECTOR_W - 1,
            0,
            self.SELECTOR_W - 1,
            self.height(),
        )

        for index, track in enumerate(self.tracks):
            top = self.PAD + index * self.ROW_H
            row_rect = QRectF(0, top, self.width(), self.ROW_H)
            if index % 2:
                painter.fillRect(row_rect, QColor(255, 255, 255, 8))

            selector_rect = QRectF(0, top, self.SELECTOR_W, self.ROW_H)
            if track.mix_enabled:
                painter.fillRect(selector_rect, QColor(65, 105, 145, 115))
            painter.setPen(
                QColor(245, 245, 245, 235)
                if track.mix_enabled
                else QColor(150, 150, 150, 200)
            )
            painter.drawText(
                selector_rect,
                Qt.AlignmentFlag.AlignCenter,
                "▶" if track.mix_enabled else "▷",
            )

            track_start, track_end = self._track_bounds(track)
            draw_start = max(track_start, vis_start)
            draw_end = min(track_end, vis_end)
            bar: Optional[QRectF] = None
            if draw_end > draw_start:
                x1 = self._x_from_time(draw_start)
                x2 = self._x_from_time(draw_end)
                bar = QRectF(
                    x1,
                    top + 4,
                    max(2.0, x2 - x1),
                    self.ROW_H - 8,
                )

                fill = (
                    QColor(198, 126, 64, 195)
                    if track.source_type == "external"
                    else QColor(82, 162, 122, 195)
                )
                painter.fillRect(bar, fill)

                painter.setPen(QPen(QColor(35, 35, 35, 180), 1))
                painter.drawRect(bar.adjusted(0, 0, -1, -1))

                if track.source_type == "external":
                    project_start, project_end = _external_project_window(track)
                    handle_fill = QColor(245, 245, 245, 145)
                    if vis_start <= project_start <= vis_end:
                        hx = self._x_from_time(project_start)
                        painter.fillRect(
                            QRectF(
                                hx,
                                bar.top(),
                                min(self.HANDLE_W, max(2.0, bar.width())),
                                bar.height(),
                            ),
                            handle_fill,
                        )
                    if math.isfinite(project_end) and vis_start <= project_end <= vis_end:
                        hx = self._x_from_time(project_end)
                        painter.fillRect(
                            QRectF(
                                max(bar.left(), hx - self.HANDLE_W),
                                bar.top(),
                                min(self.HANDLE_W, max(2.0, bar.width())),
                                bar.height(),
                            ),
                            handle_fill,
                        )

                badge = self._track_badge(track)
                if badge and bar.width() >= label_w + 90:
                    text = painter.fontMetrics().elidedText(
                        badge,
                        Qt.TextElideMode.ElideRight,
                        max(1, int(bar.width() - label_w) - 12),
                    )
                    draw_outlined_text(
                        bar.adjusted(label_w + 4, 0, -5, 0),
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                        text,
                    )

                # Keep the identity label inside the actual media block. For an
                # external track the name moves with the draggable/trimmed clip.
                # No dark caption box is drawn; instead the text gets a subtle
                # black outline so it stays readable without looking like a
                # separate clip overlay.
                label_width = min(label_w, max(0.0, bar.width() - 8.0))
                if label_width >= 20:
                    label_box = QRectF(
                        bar.left() + 4,
                        bar.top(),
                        label_width,
                        bar.height(),
                    )
                    label = painter.fontMetrics().elidedText(
                        self._track_label(track),
                        Qt.TextElideMode.ElideMiddle,
                        max(1, int(label_box.width()) - 10),
                    )
                    draw_outlined_text(
                        label_box.adjusted(5, 0, -5, 0),
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                        label,
                    )

        track_top = 0
        track_bottom = self.height()

        # Deleted project segments shade every visible audio row.
        for seg in self.segments:
            if not seg.deleted or seg.end <= vis_start or seg.start >= vis_end:
                continue
            x1 = self._x_from_time(max(seg.start, vis_start))
            x2 = self._x_from_time(min(seg.end, vis_end))
            painter.fillRect(
                QRectF(x1, track_top, max(1.0, x2 - x1), track_bottom),
                QColor(20, 20, 20, 110),
            )

        # User-created cut boundaries pass through the whole audio stack.
        painter.setPen(QPen(QColor(55, 55, 55, 190), 1))
        for seg in self.segments[1:]:
            if vis_start < seg.start < vis_end:
                x = self._x_from_time(seg.start)
                painter.drawLine(int(x), track_top, int(x), track_bottom)

        if vis_start <= self.position <= vis_end:
            x = self._x_from_time(self.position)
            painter.setPen(QPen(QColor(235, 65, 65), 2))
            painter.drawLine(int(x), 0, int(x), self.height())

class KeyframeScanSignals(QObject):
    progress = Signal(int, int)
    finished = Signal(int, object)
    failed = Signal(int, str)


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
        export_main_mix: bool = True,
        export_separate_audio_tracks: bool = False,
        audio_tracks: Optional[list[AudioTrack]] = None,
        source_audio_probe_ok: bool = True,
        ranges_override: Optional[list[tuple[float, float]]] = None,
        keyframes: Optional[list[float]] = None,
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
        self.export_main_mix = bool(export_main_mix)
        self.export_separate_audio_tracks = bool(export_separate_audio_tracks)
        self.audio_tracks = list(audio_tracks or [])
        self.source_audio_probe_ok = bool(source_audio_probe_ok)
        self.language = language if language in SUPPORTED_LANGUAGES else "en"
        self.ranges_override = (
            list(ranges_override)
            if ranges_override is not None
            else None
        )
        self.keyframes = sorted(
            set(float(value) for value in (keyframes or []) if value >= 0.0)
        )

        self._cancel_event = threading.Event()
        self._used_single_track_main_mix_copy = False
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
        return kept_ranges_from_segments(self.segments)

    def _scan_keyframes(self, interval: Optional[tuple[float, float]] = None) -> list[float]:
        self._check_cancelled()
        self.signals.progress.emit(3, self._t("scan_keyframes"))
        try:
            return scan_video_keyframes(
                self.ffprobe,
                self.input_path,
                duration=self.duration,
                interval=interval,
                cancel_event=self._cancel_event,
            )
        except KeyframeScanCancelled as exc:
            raise ExportCancelledError() from exc
        except KeyframeScanError as exc:
            message = str(exc)
            if "No keyframes" in message:
                raise RuntimeError(self._t("no_keyframes")) from exc
            raise RuntimeError(message or self._t("ffprobe_scan_failed")) from exc

    def _keyframes_for_export(
        self,
        interval: Optional[tuple[float, float]] = None,
    ) -> list[float]:
        if self.keyframes:
            return self.keyframes
        return self._scan_keyframes(interval)

    def _snap_range(
        self, start: float, end: float, keyframes: list[float]
    ) -> Optional[tuple[float, float]]:
        return snap_range_to_keyframes(
            start, end, keyframes, self.duration
        )

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

    def _selected_audio_tracks(
        self,
        source_type: Optional[str] = None,
    ) -> list[AudioTrack]:
        if not self.export_audio:
            return []
        return [
            track
            for track in self.audio_tracks
            if track.export_enabled
            and (source_type is None or track.source_type == source_type)
        ]

    def _selected_external_tracks(self) -> list[AudioTrack]:
        return self._selected_audio_tracks("external")

    def _selected_embedded_tracks(self) -> list[AudioTrack]:
        return self._selected_audio_tracks("embedded")

    def _selected_mix_tracks(
        self,
        source_type: Optional[str] = None,
    ) -> list[AudioTrack]:
        return [
            track
            for track in self._selected_audio_tracks(source_type)
            if track.mix_enabled
        ]

    def _required_audio_tracks(
        self,
        source_type: Optional[str] = None,
    ) -> list[AudioTrack]:
        """Source tracks needed by stems and/or the Main Mix."""
        if not self.export_audio:
            return []
        selected = self._selected_audio_tracks(source_type)
        if self.export_separate_audio_tracks:
            return selected
        if self.export_main_mix:
            return [track for track in selected if track.mix_enabled]
        return []

    def _required_external_tracks(self) -> list[AudioTrack]:
        return self._required_audio_tracks("external")

    def _required_embedded_tracks(self) -> list[AudioTrack]:
        return self._required_audio_tracks("embedded")

    def _has_main_mix(self) -> bool:
        return (
            self.export_audio
            and self.export_main_mix
            and bool(self._selected_mix_tracks())
        )

    def _main_mix_metadata_args(self) -> list[str]:
        if not self._has_main_mix():
            return []

        args = [
            "-metadata:s:a:0", "title=Main Mix",
            "-disposition:a:0", "default",
        ]
        if self.export_separate_audio_tracks:
            for audio_index in range(1, 1 + len(self._selected_audio_tracks())):
                args += [f"-disposition:a:{audio_index}", "0"]
        return args

    def _selected_external_sources(self) -> list[str]:
        sources: list[str] = []
        seen: set[str] = set()
        for track in self._required_external_tracks():
            key = str(Path(track.source_path).resolve(strict=False)).casefold()
            if key in seen:
                continue
            seen.add(key)
            sources.append(track.source_path)
        return sources

    def _has_external_offsets(self) -> bool:
        return any(
            abs(track.offset_seconds) > 0.0005
            for track in self._required_external_tracks()
        )

    def _has_external_trims(self) -> bool:
        return any(
            _track_has_trim(track)
            for track in self._required_external_tracks()
        )

    def _has_external_timing_edits(self) -> bool:
        return self._has_external_offsets() or self._has_external_trims()

    def _has_audio_processing(self) -> bool:
        return any(
            _track_requires_processing(track)
            for track in self._required_audio_tracks()
        )

    def _has_embedded_audio_processing(self) -> bool:
        return any(
            _track_requires_processing(track)
            for track in self._required_embedded_tracks()
        )

    @staticmethod
    def _processed_audio_bitrate(track: AudioTrack) -> int:
        ceiling = 512000 if track.channels > 2 else 320000
        if track.bit_rate > 0:
            return max(96000, min(ceiling, int(track.bit_rate)))
        return 128000 if track.channels == 1 else 256000

    def _has_primary_streams(self) -> bool:
        if self.export_video:
            return True
        if not self.export_audio:
            return False
        if not self.source_audio_probe_ok:
            return True
        return bool(self._required_embedded_tracks())

    def _primary_stream_map_args(self, input_index: int = 0) -> list[str]:
        args: list[str] = []
        if self.export_video:
            args += ["-map", f"{input_index}:v:0"]

        if not self.export_audio:
            return args

        if self.source_audio_probe_ok:
            for track in self._required_embedded_tracks():
                args += ["-map", f"{input_index}:{track.stream_index}"]
        else:
            args += ["-map", f"{input_index}:a?"]
        return args

    def _external_input_map(self) -> dict[str, int]:
        return {
            str(Path(source).resolve(strict=False)).casefold(): index
            for index, source in enumerate(
                self._selected_external_sources(),
                start=1,
            )
        }

    def _input_args(self, start: Optional[float] = None) -> list[str]:
        args: list[str] = []
        sources = [self.input_path, *self._selected_external_sources()]
        for source in sources:
            if start is not None and start > 0.001:
                args += ["-ss", f"{start:.6f}"]
            args += ["-i", source]
        return args

    def _stream_map_args(self, original_input: bool = True) -> list[str]:
        if not original_input:
            args: list[str] = []
            if self.export_video:
                args += ["-map", "0:v:0"]
            if self.export_audio:
                # Temporary concat parts already contain exactly the audio
                # streams selected for export, renumbered from zero by FFmpeg.
                args += ["-map", "0:a?"]
            return args

        args = self._primary_stream_map_args(0)
        if not self.export_audio:
            return args

        external_inputs = self._external_input_map()
        for track in self._required_external_tracks():
            key = str(Path(track.source_path).resolve(strict=False)).casefold()
            input_index = external_inputs.get(key)
            if input_index is not None:
                args += ["-map", f"{input_index}:{track.stream_index}"]

        return args

    def _processing_export_ranges(self) -> tuple[list[tuple[float, float]], float]:
        """Resolve edited project ranges for audio processing export."""
        if (
            self.ranges_override is None
            and not any(seg.deleted for seg in self.segments)
        ):
            return [(0.0, self.duration)], 0.0

        keep = (
            list(self.ranges_override)
            if self.ranges_override is not None
            else self._keep_ranges()
        )
        if not keep:
            raise RuntimeError(self._t("no_ranges"))

        if (
            len(keep) == 1
            and keep[0][0] <= 0.001
            and keep[0][1] >= self.duration - 0.001
        ):
            return [(0.0, self.duration)], 0.0

        if not self.export_video:
            return list(keep), 0.0

        scan_interval = (
            keep[0]
            if self.ranges_override is not None and len(keep) == 1
            else None
        )
        keyframes = self._keyframes_for_export(scan_interval)
        self._check_cancelled()
        export_ranges, max_shift = snap_ranges_to_keyframes(
            keep,
            keyframes,
            self.duration,
        )

        if not export_ranges:
            raise RuntimeError(self._t("no_ranges_after_snap"))
        return export_ranges, max_shift

    def _build_primary_range_part(
        self,
        output: Path,
        start: float,
        end: float,
    ) -> None:
        """Create the video/embedded-audio part for one project range.

        Video and untouched embedded audio remain stream-copied. Embedded
        tracks with per-track volume/fade processing are the only streams
        decoded, filtered and encoded to AAC.
        """
        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
        ]
        if start > 0.001:
            cmd += ["-ss", f"{start:.6f}"]
        cmd += ["-i", self.input_path]
        cmd += ["-t", f"{max(0.0, end - start):.6f}"]

        embedded_tracks = self._required_embedded_tracks()
        modified_tracks = [
            track
            for track in embedded_tracks
            if _track_requires_processing(track)
        ]

        # If the source audio could not be enumerated, or no embedded track
        # needs processing, preserve the proven stream-copy path.
        if not modified_tracks or not self.source_audio_probe_ok:
            cmd += self._primary_stream_map_args(0)
            cmd += ["-map_metadata", "0", "-c", "copy"]
        else:
            filters: list[str] = []
            maps: list[str] = []
            codec_args: list[str] = []

            if self.export_video:
                maps += ["-map", "0:v:0"]
                codec_args += ["-c:v", "copy"]

            output_audio_index = 0
            for track in embedded_tracks:
                if _track_requires_processing(track):
                    label = f"embedded_processed_{output_audio_index}"
                    filter_chain = _track_filter_chain(
                        track,
                        max(0.0, end - start),
                    )
                    filters.append(
                        f"[0:{track.stream_index}]{filter_chain}[{label}]"
                    )
                    maps += ["-map", f"[{label}]"]
                    codec_args += [
                        f"-c:a:{output_audio_index}", "aac",
                        f"-b:a:{output_audio_index}",
                        str(self._processed_audio_bitrate(track)),
                    ]
                else:
                    maps += ["-map", f"0:{track.stream_index}"]
                    codec_args += [
                        f"-c:a:{output_audio_index}", "copy",
                    ]
                output_audio_index += 1

            if filters:
                cmd += ["-filter_complex", ";".join(filters)]
            cmd += maps
            cmd += ["-map_metadata", "0"]
            cmd += codec_args

        if start > 0.001:
            cmd += ["-avoid_negative_ts", "make_zero"]
        cmd += [str(output)]
        self._run(cmd)

    def _build_external_processed_clip(
        self,
        track: AudioTrack,
        output: Path,
        range_start: float,
        range_end: float,
    ) -> float:
        """Prepare one external stream for a project range.

        Offset is represented with source seeking plus a positive timestamp
        delay. Unchanged audio remains copied; volume/fade processing encodes
        only this audio track to AAC.
        """
        range_duration = max(0.0, range_end - range_start)
        source_window_start, source_window_end = _external_source_window(track)
        project_clip_start, project_clip_end = _external_project_window(track)
        if not math.isfinite(project_clip_end):
            project_clip_end = range_end

        overlap_start = max(range_start, project_clip_start)
        overlap_end = min(range_end, project_clip_end)
        effective_duration = max(0.0, overlap_end - overlap_start)
        source_start = max(source_window_start, overlap_start - track.offset_seconds)
        delay = max(0.0, overlap_start - range_start)
        if effective_duration <= 0.0005:
            source_start = source_window_start
            delay = range_duration + 1.0

        # Even when the track is fully outside this project range, keep a tiny
        # placeholder stream so every concat part preserves identical layout.
        clip_duration = max(0.05, effective_duration)

        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
        ]
        if source_start > 0.001:
            cmd += ["-ss", f"{source_start:.6f}"]
        cmd += ["-i", track.source_path]
        cmd += ["-t", f"{clip_duration:.6f}"]

        if _track_requires_processing(track):
            filter_chain = _track_filter_chain(track, clip_duration)
            cmd += [
                "-filter_complex",
                f"[0:{track.stream_index}]{filter_chain}[external_processed]",
                "-map", "[external_processed]",
                "-c:a", "aac",
                "-b:a", str(self._processed_audio_bitrate(track)),
            ]
        else:
            cmd += [
                "-map", f"0:{track.stream_index}",
                "-c", "copy",
            ]

        cmd += [str(output)]
        self._run(cmd)
        return delay

    def _single_track_main_mix_copy_track(self) -> Optional[AudioTrack]:
        """Return the one embedded AAC track eligible for direct Main Mix copy.

        The default Main Mix path decodes and mixes audio, which is necessary
        for real mixes, external audio, fades, volume changes and stems. When
        Main Mix is just one untouched embedded AAC stream, doing that work is
        redundant and forces an expensive extra pass over long VOD ranges.
        """
        if not self._has_main_mix() or self.export_separate_audio_tracks:
            return None
        if not self.source_audio_probe_ok or self._required_external_tracks():
            return None

        tracks = self._selected_mix_tracks("embedded")
        if len(tracks) != 1:
            return None

        track = tracks[0]
        if _track_requires_processing(track):
            return None

        # AAC is safe for every video/audio output container currently offered
        # by VFR FastCut. Other codecs keep the proven transcoding path instead
        # of risking a container/codec incompatibility regression.
        if track.codec_name.strip().lower() != "aac":
            return None
        return track

    def _build_single_track_main_mix_copy_part(
        self,
        track: AudioTrack,
        output: Path,
        start: float,
        end: float,
    ) -> None:
        """Write one edited range in a single FFmpeg stream-copy pass."""
        duration = max(0.0, end - start)
        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
        ]
        if start > 0.001:
            cmd += ["-ss", f"{start:.6f}"]
        cmd += ["-i", self.input_path]
        cmd += ["-t", f"{duration:.6f}"]

        if self.export_video:
            cmd += ["-map", "0:v:0", "-c:v", "copy"]

        cmd += [
            "-map", f"0:{track.stream_index}",
            "-c:a:0", "copy",
            "-map_metadata", "0",
        ]
        cmd += self._main_mix_metadata_args()

        if start > 0.001:
            cmd += ["-avoid_negative_ts", "make_zero"]
        cmd += [str(output)]

        self._used_single_track_main_mix_copy = True
        self._run(cmd)

    def _build_processed_range_part(
        self,
        output: Path,
        start: float,
        end: float,
        temp_dir: Path,
        tag: str,
    ) -> None:
        """Build one edited range with external offsets / per-track audio processing."""
        duration = max(0.0, end - start)
        fast_main_mix_track = self._single_track_main_mix_copy_track()
        if fast_main_mix_track is not None:
            self._build_single_track_main_mix_copy_part(
                fast_main_mix_track,
                output,
                start,
                end,
            )
            return

        external_tracks = self._required_external_tracks()

        primary_path: Optional[Path] = None
        primary_is_original = False
        if self._has_primary_streams():
            if start <= 0.001 and not self._has_embedded_audio_processing():
                # A range that begins at project zero can use the source file
                # directly when its embedded streams need no processing.
                primary_path = Path(self.input_path)
                primary_is_original = True
            else:
                primary_path = temp_dir / (
                    f"primary_{tag}{'.mkv' if self.export_video else '.mka'}"
                )
                self._build_primary_range_part(primary_path, start, end)

        prepared: list[tuple[Path, float]] = []
        for ext_index, track in enumerate(external_tracks, start=1):
            self._check_cancelled()
            clip = temp_dir / f"external_{tag}_{ext_index:03d}.mka"
            delay = self._build_external_processed_clip(
                track,
                clip,
                start,
                end,
            )
            prepared.append((clip, delay))

        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
        ]
        input_index = 0
        primary_input_index: Optional[int] = None
        if primary_path is not None:
            primary_input_index = input_index
            cmd += ["-i", str(primary_path)]
            input_index += 1

        external_input_indices: list[int] = []
        external_input_delays: list[float] = []
        for clip, delay in prepared:
            if delay > 0.001:
                # Keep timestamp offset for separate stems. Main Mix also gets
                # an explicit audio delay below because amix does not preserve
                # input start timestamps as audible leading silence.
                cmd += ["-itsoffset", f"{delay:.6f}"]
            cmd += ["-i", str(clip)]
            external_input_indices.append(input_index)
            external_input_delays.append(delay)
            input_index += 1

        if not self._has_main_mix():
            # Preserve the proven 0.3.5 remux path when Main Mix is disabled.
            if primary_input_index is not None:
                if primary_is_original:
                    cmd += self._primary_stream_map_args(primary_input_index)
                else:
                    # A prepared primary part already contains exactly the selected
                    # video/embedded-audio streams.
                    cmd += ["-map", str(primary_input_index)]
            for ext_input_index in external_input_indices:
                cmd += ["-map", f"{ext_input_index}:a:0"]

            cmd += ["-t", f"{duration:.6f}", "-c", "copy"]
            if primary_input_index is not None:
                cmd += ["-map_metadata", str(primary_input_index)]
            cmd += [str(output)]
            self._run(cmd)
            return

        embedded_tracks = self._required_embedded_tracks()

        # Main Mix needs the actual project-time delay for each input.
        # FFmpeg amix aligns decoded audio content and does not turn an input
        # start timestamp from -itsoffset into leading silence, so external
        # tracks carry an explicit delay value into the filter graph.
        mix_inputs: list[tuple[str, float]] = []
        stem_maps: list[str] = []

        if primary_input_index is not None:
            for audio_ordinal, track in enumerate(embedded_tracks):
                if primary_is_original:
                    stream_ref = f"{primary_input_index}:{track.stream_index}"
                else:
                    stream_ref = f"{primary_input_index}:a:{audio_ordinal}"
                if track.mix_enabled:
                    mix_inputs.append((stream_ref, 0.0))
                if self.export_separate_audio_tracks:
                    stem_maps.append(stream_ref)

        for track, ext_input_index, mix_delay in zip(
            external_tracks,
            external_input_indices,
            external_input_delays,
        ):
            stream_ref = f"{ext_input_index}:a:0"
            if track.mix_enabled:
                mix_inputs.append((stream_ref, mix_delay))
            if self.export_separate_audio_tracks:
                stem_maps.append(stream_ref)

        if not mix_inputs:
            raise RuntimeError("Main Mix has no selected audio streams")

        filters: list[str] = []
        normalized_labels: list[str] = []
        for index, (stream_ref, mix_delay) in enumerate(mix_inputs):
            label = f"main_mix_in_{index}"
            chain = (
                "aformat=sample_fmts=fltp:sample_rates=48000:"
                "channel_layouts=stereo"
            )
            if mix_delay > 0.0005:
                delay_ms = max(0, int(round(mix_delay * 1000.0)))
                # Delay both stereo channels with real silence before amix.
                chain += f",adelay={delay_ms}|{delay_ms}"
            filters.append(f"[{stream_ref}]{chain}[{label}]")
            normalized_labels.append(label)

        limiter = "alimiter=limit=0.95:attack=5:release=50:level=false:latency=true"
        if len(normalized_labels) == 1:
            filters.append(f"[{normalized_labels[0]}]{limiter}[main_mix]")
        else:
            joined = "".join(f"[{label}]" for label in normalized_labels)
            filters.append(
                f"{joined}amix=inputs={len(normalized_labels)}:"
                "duration=longest:dropout_transition=0:normalize=0,"
                f"{limiter}[main_mix]"
            )

        cmd += ["-filter_complex", ";".join(filters)]

        if self.export_video and primary_input_index is not None:
            cmd += ["-map", f"{primary_input_index}:v:0", "-c:v", "copy"]

        # Main Mix is always audio stream 0 and is intentionally AAC/stereo.
        cmd += [
            "-map", "[main_mix]",
            "-c:a:0", "aac",
            "-b:a:0", "256000",
        ]

        if self.export_separate_audio_tracks:
            output_audio_index = 1
            for stream_ref in stem_maps:
                cmd += [
                    "-map", stream_ref,
                    f"-c:a:{output_audio_index}", "copy",
                ]
                output_audio_index += 1

        cmd += ["-t", f"{duration:.6f}"]
        if primary_input_index is not None:
            cmd += ["-map_metadata", str(primary_input_index)]
        cmd += self._main_mix_metadata_args()
        cmd += [str(output)]
        self._run(cmd)

    def _run_audio_processing_export(
        self,
        staging: Path,
        out: Path,
    ) -> None:
        export_ranges, max_shift = self._processing_export_ranges()

        with tempfile.TemporaryDirectory(
            prefix=".vfr_fastcut_offset_",
            dir=str(out.parent),
        ) as tmp_str:
            tmp = Path(tmp_str)

            if len(export_ranges) == 1:
                range_start, range_end = export_ranges[0]
                self.signals.progress.emit(
                    15,
                    self._t(
                        "copying_range",
                        start=fmt_time(range_start),
                        end=fmt_time(range_end),
                    ),
                )
                self._build_processed_range_part(
                    staging,
                    range_start,
                    range_end,
                    tmp,
                    "single",
                )
            else:
                part_paths: list[Path] = []
                count = len(export_ranges)
                for index, (range_start, range_end) in enumerate(
                    export_ranges,
                    start=1,
                ):
                    self._check_cancelled()
                    pct = 8 + int((index - 1) / count * 82)
                    self.signals.progress.emit(
                        pct,
                        self._t(
                            "copying_range_n",
                            index=index,
                            count=count,
                            start=fmt_time(range_start),
                            end=fmt_time(range_end),
                        ),
                    )
                    part = tmp / (
                        f"part_{index:04d}"
                        f"{'.mkv' if self.export_video else '.mka'}"
                    )
                    part_paths.append(part)
                    self._build_processed_range_part(
                        part,
                        range_start,
                        range_end,
                        tmp,
                        f"{index:04d}",
                    )

                concat_file = tmp / "concat.txt"
                lines: list[str] = []
                for part in part_paths:
                    escaped = part.as_posix().replace("'", r"'\''")
                    lines.append(f"file '{escaped}'")
                concat_file.write_text("\n".join(lines), encoding="utf-8")

                self.signals.progress.emit(92, self._t("joining_ranges"))
                cmd = [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel", "error",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                ]
                cmd += self._stream_map_args(original_input=False)
                cmd += ["-c", "copy"]
                cmd += self._main_mix_metadata_args()
                if staging.suffix.lower() == ".mp4":
                    cmd += ["-movflags", "+faststart"]
                cmd += [str(staging)]
                self._run(cmd)

        self._commit_staging_output(staging, out)
        self.signals.progress.emit(100, self._t("done"))

        if len(export_ranges) == 1:
            range_start, range_end = export_ranges[0]
            is_full = (
                range_start <= 0.001
                and range_end >= self.duration - 0.001
            )
            note = (
                self._t("full_range_note")
                if is_full
                else self._t("single_range_note")
                + self._boundary_result_note(max_shift)
            )
        else:
            note = (
                self._t("multi_range_note", count=len(export_ranges))
                + self._boundary_result_note(max_shift)
            )

        if self._has_external_timing_edits():
            note += "\n" + self._t("external_offset_note")
        if self._has_audio_processing():
            note += "\n" + self._t("audio_processing_note")
        if self._has_main_mix():
            note += "\n" + self._t(
                "main_mix_stream_copy_note"
                if self._used_single_track_main_mix_copy
                else "main_mix_note"
            )
        note += self._stream_result_note()
        self.signals.finished.emit(str(out), note)

    def _stream_result_note(self) -> str:
        notes: list[str] = []
        if not self.export_video:
            notes.append(self._t("video_excluded"))
        if not self.export_audio:
            notes.append(self._t("audio_excluded"))
        elif (
            not self.export_video
            and not self._has_audio_processing()
            and not self._has_main_mix()
        ):
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

        cmd += self._input_args(start)

        if start is not None and end is not None:
            cmd += ["-t", f"{max(0.0, end - start):.6f}"]
        elif self._selected_external_sources():
            # An external file may be longer than the project video. Cap a
            # full-file remux to the project duration without shortening video
            # when an external track is shorter.
            cmd += ["-t", f"{self.duration:.6f}"]

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

            if (
                self._has_main_mix()
                or self._has_external_timing_edits()
                or self._has_audio_processing()
            ):
                self._run_audio_processing_export(staging, out)
                staging = None
                return

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
                keyframes = self._keyframes_for_export(scan_interval)
                self._check_cancelled()
                export_ranges, max_shift = snap_ranges_to_keyframes(
                    keep,
                    keyframes,
                    self.duration,
                )
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
                    ]
                    cmd += self._input_args(range_start)
                    cmd += [
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
                cmd += self._stream_map_args(original_input=False)
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


class TaskProgressDialog(QDialog):
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
        saved_audio_timeline = self.settings.value("ui/show_audio_timeline", True)
        self.show_audio_timeline = (
            saved_audio_timeline
            if isinstance(saved_audio_timeline, bool)
            else str(saved_audio_timeline).strip().lower() not in {"0", "false", "no"}
        )

        self.resize(980, 800)
        self.setAcceptDrops(True)

        icon_path = find_app_icon()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        # Created after the native HWND exists (singleShot below).
        self.taskbar_progress: Optional[WindowsTaskbarProgress] = None

        self.task_progress_dialog = TaskProgressDialog(self)
        self.task_progress_dialog.cancelRequested.connect(self.cancel_export)
        self._task_progress_owner = ""
        self._keyframe_scan_percent = 0
        self._keyframe_progress_show_timer = QTimer(self)
        self._keyframe_progress_show_timer.setSingleShot(True)
        self._keyframe_progress_show_timer.setInterval(300)
        self._keyframe_progress_show_timer.timeout.connect(
            self._show_keyframe_progress_dialog
        )

        self.input_path = ""
        self.duration = 0.0
        self.segments: list[Segment] = []
        self.audio_tracks: list[AudioTrack] = []
        self.audio_probe_ok = False
        self.keyframes: list[float] = []
        self._edited_preview_ranges: list[tuple[float, float]] = []
        self._edited_preview_ranges_exact = False
        self._edited_preview_has_deletions = False
        self._edited_preview_jump_active = False
        self._keyframe_scan_generation = 0
        self._keyframe_scan_cancel_event: Optional[threading.Event] = None
        self.keyframe_scan_thread: Optional[threading.Thread] = None
        self.preview_mix_channels: dict[
            tuple[str, str, int, str], PreviewMixChannel
        ] = {}
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

        self.keyframe_scan_signals = KeyframeScanSignals(self)
        self.keyframe_scan_signals.progress.connect(
            self.on_keyframe_scan_progress
        )
        self.keyframe_scan_signals.finished.connect(
            self.on_keyframe_scan_finished
        )
        self.keyframe_scan_signals.failed.connect(
            self.on_keyframe_scan_failed
        )

        self.player = QMediaPlayer(self)
        # Keep a muted fallback output attached to the video/transport player.
        # When ffprobe metadata is unavailable it can still provide legacy
        # single-stream preview; normally all known tracks are reproduced by
        # PreviewMixChannel instances below.
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

        # Automatic edited-preview jumps use direct seeks so cuts do not
        # inherit the user-seek debounce delay. A short guard suppresses
        # stale positionChanged events from retriggering the same jump.
        self._edited_preview_jump_guard_timer = QTimer(self)
        self._edited_preview_jump_guard_timer.setSingleShot(True)
        self._edited_preview_jump_guard_timer.setInterval(250)
        self._edited_preview_jump_guard_timer.timeout.connect(
            self._clear_edited_preview_jump_guard
        )

        self._resume_after_seek = False
        self._seek_was_playing = False
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

        self.play_btn = QPushButton(self._t("play"))
        self.play_btn.setFixedWidth(135)
        self.play_btn.setStyleSheet(PLAY_BUTTON_STYLE)
        self.play_btn.clicked.connect(self.toggle_play)

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
        self.split_btn.setFixedWidth(175)
        self.split_btn.setStyleSheet(SPLIT_BUTTON_STYLE)
        self.split_btn.clicked.connect(self.toggle_split_cut_at_playhead)

        # Delete and Restore are mutually exclusive for the selected segment,
        # so the essentials bar uses one context-sensitive button instead of
        # spending permanent space on both commands.
        self.segment_state_btn = QPushButton(self._t("delete"))
        self.segment_state_btn.setFixedWidth(125)
        self.segment_state_btn.clicked.connect(self.toggle_selected_segment_state)

        self.undo_btn = QPushButton(self._t("undo"))
        self.undo_btn.clicked.connect(self.undo)

        self.export_video_check = QCheckBox(self._t("export_video"))
        self.export_video_check.setChecked(True)
        self.export_video_check.setToolTip(self._t("export_video_tip"))
        self.export_video_check.toggled.connect(
            lambda _checked: self._update_ui_state()
        )

        # Audio output mode is configured from the top-level Audio menu.
        # Main Mix is the default ready-to-play output. Separate stems are an
        # advanced opt-in so ordinary exports contain one mixed audio stream.
        self.export_main_mix = True
        self.export_separate_audio_tracks = False

        self.export_audio_check = QCheckBox(self._t("export_audio"))
        self.export_audio_check.setChecked(True)
        self.export_audio_check.setToolTip(self._t("export_audio_tip"))
        self.export_audio_check.toggled.connect(
            self._on_export_audio_toggled
        )

        self.export_btn = QPushButton("Lossless Export")
        self.export_btn.setFixedWidth(140)
        self.export_btn.setStyleSheet(EXPORT_BUTTON_STYLE)
        self.export_btn.clicked.connect(self.export_lossless)

        self.audio_timeline = AudioTimelineWidget()
        self.audio_timeline.setToolTip(self._t("audio_timeline_drag_tip"))
        self.audio_timeline.trackTimingChanged.connect(
            self.on_audio_timeline_timing_changed
        )
        self.audio_timeline.trackTimingDragFinished.connect(
            self.on_audio_timeline_timing_drag_finished
        )
        self.audio_timeline.trackMixToggled.connect(
            self.on_audio_mix_track_toggled
        )
        self.audio_timeline.trackContextRequested.connect(
            self.show_audio_timeline_context_menu
        )

        # The visible audio area has a stable height. Track rows grow downward
        # inside it; after five rows the vertical scrollbar takes over. This
        # prevents any audio configuration change from resizing the preview.
        self.audio_timeline_scroll = QScrollArea()
        self.audio_timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.audio_timeline_scroll.setWidgetResizable(True)
        self.audio_timeline_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.audio_timeline_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.audio_timeline_scroll.setFixedHeight(
            AudioTimelineWidget.ROW_H * 5
        )
        self.audio_timeline_scroll.setWidget(self.audio_timeline)
        self.audio_timeline_scroll.setVisible(self.show_audio_timeline)

        # Reserve the same width beside the video ruler/scrollbar as the audio
        # vertical scrollbar consumes. The project-time X coordinate therefore
        # remains identical across video and audio even while audio is scrolled.
        audio_scrollbar_width = max(
            1,
            self.audio_timeline_scroll.verticalScrollBar().sizeHint().width(),
        )
        self.timeline_left_gutter = QWidget()
        self.timeline_left_gutter.setFixedWidth(AudioTimelineWidget.SELECTOR_W)
        self.timeline_left_gutter.setVisible(self.show_audio_timeline)
        self.timeline_scroll_left_gutter = QWidget()
        self.timeline_scroll_left_gutter.setFixedWidth(AudioTimelineWidget.SELECTOR_W)
        self.timeline_scroll_left_gutter.setVisible(self.show_audio_timeline)

        self.timeline_right_gutter = QWidget()
        self.timeline_right_gutter.setFixedWidth(audio_scrollbar_width)
        self.timeline_right_gutter.setVisible(self.show_audio_timeline)
        self.timeline_scroll_right_gutter = QWidget()
        self.timeline_scroll_right_gutter.setFixedWidth(audio_scrollbar_width)
        self.timeline_scroll_right_gutter.setVisible(self.show_audio_timeline)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.video, stretch=1)

        timeline_header = QHBoxLayout()
        self.timeline_title_label = QLabel(self._t("timeline"))
        timeline_header.addWidget(self.timeline_title_label)
        timeline_header.addStretch(1)
        timeline_header.addWidget(self.zoom_label)
        layout.addLayout(timeline_header)

        # Video and audio are a single visual timeline. A fixed Play-flag gutter
        # on the left and the permanent audio scrollbar gutter on the right keep
        # project-time X coordinates identical across all rows.
        timeline_stack = QVBoxLayout()
        timeline_stack.setContentsMargins(0, 0, 0, 0)
        timeline_stack.setSpacing(0)

        video_timeline_row = QHBoxLayout()
        video_timeline_row.setContentsMargins(0, 0, 0, 0)
        video_timeline_row.setSpacing(0)
        video_timeline_row.addWidget(self.timeline_left_gutter)
        video_timeline_row.addWidget(self.timeline, 1)
        video_timeline_row.addWidget(self.timeline_right_gutter)
        timeline_stack.addLayout(video_timeline_row)
        timeline_stack.addWidget(self.audio_timeline_scroll)
        layout.addLayout(timeline_stack)

        timeline_scroll_row = QHBoxLayout()
        timeline_scroll_row.setContentsMargins(0, 0, 0, 0)
        timeline_scroll_row.setSpacing(0)
        timeline_scroll_row.addWidget(self.timeline_scroll_left_gutter)
        timeline_scroll_row.addWidget(self.timeline_scroll, 1)
        timeline_scroll_row.addWidget(self.timeline_scroll_right_gutter)
        layout.addLayout(timeline_scroll_row)

        timeline_info = QHBoxLayout()
        timeline_info.addWidget(self.time_label)
        timeline_info.addSpacing(12)
        timeline_info.addWidget(self.selection_label)
        timeline_info.addStretch(1)
        self.audio_timeline_title_label = QLabel(self._t("audio_timeline"))
        self.audio_timeline_title_label.setVisible(self.show_audio_timeline)
        timeline_info.addWidget(self.audio_timeline_title_label)
        layout.addLayout(timeline_info)

        # Treat all essentials/export widgets as one fixed bottom panel. The
        # upper workspace owns every flexible pixel, so controls never float up
        # or leave unused space below them when the audio track count changes.
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        essentials = QHBoxLayout()
        essentials.addWidget(self.play_btn)
        essentials.addWidget(self.split_btn)
        essentials.addWidget(self.segment_state_btn)
        essentials.addWidget(self.undo_btn)
        essentials.addStretch(1)
        essentials.addWidget(self.mute_btn)
        self.volume_title_label = QLabel(self._t("volume"))
        essentials.addWidget(self.volume_title_label)
        essentials.addWidget(self.volume_slider)
        essentials.addWidget(self.volume_label)
        bottom_layout.addLayout(essentials)

        export_row = QHBoxLayout()
        author_label = QLabel("by Sergilol")
        author_label.setStyleSheet("color: #777; font-size: 10px;")
        export_row.addWidget(author_label)
        export_row.addStretch(1)
        export_row.addWidget(self.export_video_check)
        export_row.addWidget(self.export_audio_check)
        export_row.addWidget(self.export_btn)
        bottom_layout.addLayout(export_row)

        layout.addWidget(bottom_panel, stretch=0)

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
        self.player.tracksChanged.connect(self._disable_main_player_audio)

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
        difference between the full window and the preview widget represents the
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

    def set_language(self, language: str):
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

    def _refresh_segment_state_button(self):
        selected = (
            0 <= self.selected_index < len(self.segments)
            and self.duration > 0
        )
        if selected and self.segments[self.selected_index].deleted:
            self.segment_state_btn.setText(self._t("restore"))
        else:
            self.segment_state_btn.setText(self._t("delete"))

    def _apply_language(self):
        self.timeline.set_empty_text(self._t("timeline_empty"))
        self.audio_timeline.set_empty_text(self._t("audio_timeline_empty"))
        self.audio_timeline.setToolTip(self._t("audio_timeline_drag_tip"))
        self.timeline_title_label.setText(self._t("timeline"))
        self.audio_timeline_title_label.setText(self._t("audio_timeline"))
        self.volume_title_label.setText(self._t("volume"))
        self.split_btn.setText(self._t("split"))
        self.undo_btn.setText(self._t("undo"))
        self.export_video_check.setText(self._t("export_video"))
        self.export_video_check.setToolTip(self._t("export_video_tip"))
        self.export_audio_check.setText(self._t("export_audio"))
        self.export_audio_check.setToolTip(self._t("export_audio_tip"))
        self.task_progress_dialog.cancel_btn.setText(self._t("cancel_export"))
        self.mute_btn.setText(
            self._t("unmute") if self.preview_muted else self._t("mute")
        )

        self.file_menu.setTitle(self._t("menu_file"))
        self.edit_menu.setTitle(self._t("menu_edit"))
        self.playback_menu.setTitle(self._t("menu_playback"))
        self.audio_menu.setTitle(self._t("menu_audio"))
        self.view_menu.setTitle(self._t("menu_view"))
        self.help_menu.setTitle(self._t("menu_help"))
        self.language_menu.setTitle(self._t("menu_language"))

        self.act_open.setText(self._t("menu_open_video"))
        self.act_reset.setText(self._t("menu_reset_project"))
        self.act_export.setText(self._t("menu_export"))
        self.act_export_fragment.setText(self._t("menu_export_fragment"))
        self.act_exit.setText(self._t("menu_exit"))
        self.act_undo.setText(self._t("menu_undo"))
        self.act_redo.setText(self._t("menu_redo"))
        self.act_split.setText(self._t("menu_split"))
        self.remove_cut_action.setText(self._t("menu_remove_cut"))
        self.act_delete.setText(self._t("menu_delete"))
        self.act_restore.setText(self._t("menu_restore"))
        self.act_prev_cut.setText(self._t("menu_prev_cut"))
        self.act_next_cut.setText(self._t("menu_next_cut"))
        self.act_mute.setText(
            self._t("unmute") if self.preview_muted else self._t("menu_mute")
        )
        self.act_audio_tracks.setText(self._t("menu_audio_tracks"))
        self.add_external_menu.setTitle(self._t("menu_add_external_audio"))
        self.act_choose_external_audio.setText(self._t("menu_choose_external_audio"))
        self.remove_external_menu.setTitle(self._t("menu_remove_external_audio"))
        self.act_main_mix.setText(self._t("audio_main_mix"))
        self.act_main_mix.setToolTip(self._t("audio_main_mix_tip"))
        self.act_keep_stems.setText(self._t("audio_keep_stems"))
        self.act_keep_stems.setToolTip(self._t("audio_keep_stems_tip"))
        self.act_zoom_in.setText(self._t("menu_zoom_in"))
        self.act_zoom_out.setText(self._t("menu_zoom_out"))
        self.act_zoom_reset.setText(self._t("menu_zoom_reset"))
        self.act_show_audio_tracks.setText(self._t("menu_show_audio_tracks"))
        self.act_language_en.setText(self._t("menu_language_en"))
        self.act_language_ru.setText(self._t("menu_language_ru"))
        self.act_help.setText(self._t("menu_help_contents"))

        self.act_language_en.setChecked(self.language == "en")
        self.act_language_ru.setChecked(self.language == "ru")
        self._sync_play_button()
        self._refresh_segment_state_button()
        self._refresh_selection_label()
        self._refresh_audio_tracks_control()
        self._refresh_audio_menu()
        self._update_audio_timeline()
        self._update_ui_state()

    def _create_actions(self):
        # ----- File -----
        self.file_menu = self.menuBar().addMenu("")
        self.act_open = QAction(self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_video)
        self.file_menu.addAction(self.act_open)

        self.act_reset = QAction(self)
        self.act_reset.setShortcut(QKeySequence("Ctrl+N"))
        self.act_reset.triggered.connect(self.reset_project)
        self.file_menu.addAction(self.act_reset)
        self.file_menu.addSeparator()

        self.act_export = QAction(self)
        self.act_export.triggered.connect(self.export_lossless)
        self.file_menu.addAction(self.act_export)

        self.act_export_fragment = QAction(self)
        self.act_export_fragment.triggered.connect(self.export_selected_fragment)
        self.file_menu.addAction(self.act_export_fragment)
        self.file_menu.addSeparator()

        self.act_exit = QAction(self)
        self.act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        self.act_exit.triggered.connect(self.close)
        self.file_menu.addAction(self.act_exit)

        # ----- Edit -----
        self.edit_menu = self.menuBar().addMenu("")
        self.act_undo = QAction(self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self.undo)
        self.edit_menu.addAction(self.act_undo)

        self.act_redo = QAction(self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(self.redo)
        self.edit_menu.addAction(self.act_redo)
        self.edit_menu.addSeparator()

        self.act_split = QAction(self)
        self.act_split.setShortcut(QKeySequence("S"))
        self.act_split.triggered.connect(self.split_at_playhead)
        self.edit_menu.addAction(self.act_split)

        self.remove_cut_action = QAction(self)
        self.remove_cut_action.setShortcut(QKeySequence("Shift+S"))
        self.remove_cut_action.triggered.connect(self.remove_cut_at_playhead)
        self.edit_menu.addAction(self.remove_cut_action)

        self.act_delete = QAction(self)
        self.act_delete.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        self.act_delete.triggered.connect(self.delete_selected)
        self.edit_menu.addAction(self.act_delete)

        self.act_restore = QAction(self)
        self.act_restore.triggered.connect(self.restore_selected)
        self.edit_menu.addAction(self.act_restore)

        # ----- Playback -----
        self.playback_menu = self.menuBar().addMenu("")
        self.act_play = QAction(self)
        self.act_play.setShortcut(QKeySequence(Qt.Key.Key_Space))
        self.act_play.triggered.connect(self.toggle_play)
        self.playback_menu.addAction(self.act_play)

        self.act_prev_cut = QAction(self)
        self.act_prev_cut.setShortcut(QKeySequence("Q"))
        self.act_prev_cut.triggered.connect(self.seek_previous_cut)
        self.playback_menu.addAction(self.act_prev_cut)

        self.act_next_cut = QAction(self)
        self.act_next_cut.setShortcut(QKeySequence("E"))
        self.act_next_cut.triggered.connect(self.seek_next_cut)
        self.playback_menu.addAction(self.act_next_cut)
        self.playback_menu.addSeparator()

        self.act_mute = QAction(self)
        self.act_mute.setCheckable(True)
        self.act_mute.setShortcut(QKeySequence("M"))
        self.act_mute.triggered.connect(self.toggle_mute)
        self.playback_menu.addAction(self.act_mute)

        # ----- Audio -----
        self.audio_menu = self.menuBar().addMenu("")
        self.act_audio_tracks = QAction(self)
        self.act_audio_tracks.triggered.connect(self.show_audio_tracks_dialog)
        self.audio_menu.addAction(self.act_audio_tracks)

        self.add_external_menu = self.audio_menu.addMenu("")
        self.act_add_external_audio = self.add_external_menu.menuAction()
        self.act_choose_external_audio = QAction(self)
        self.act_choose_external_audio.triggered.connect(self.add_external_audio)
        self.add_external_menu.addAction(self.act_choose_external_audio)
        self.add_external_menu.addSeparator()
        self.recent_external_actions: list[QAction] = []

        self.remove_external_menu = self.audio_menu.addMenu("")
        self.audio_menu.addSeparator()

        self.act_main_mix = QAction(self)
        self.act_main_mix.setCheckable(True)
        self.act_main_mix.setChecked(self.export_main_mix)
        self.act_main_mix.toggled.connect(self._on_audio_output_mode_changed)
        self.audio_menu.addAction(self.act_main_mix)

        self.act_keep_stems = QAction(self)
        self.act_keep_stems.setCheckable(True)
        self.act_keep_stems.setChecked(self.export_separate_audio_tracks)
        self.act_keep_stems.toggled.connect(self._on_audio_output_mode_changed)
        self.audio_menu.addAction(self.act_keep_stems)

        self.audio_menu.addSeparator()
        self.audio_track_setting_actions: list[QAction] = []

        # ----- View -----
        self.view_menu = self.menuBar().addMenu("")
        self.act_zoom_in = QAction(self)
        self.act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        self.act_zoom_in.triggered.connect(self.timeline.zoom_in)
        self.view_menu.addAction(self.act_zoom_in)

        self.act_zoom_out = QAction(self)
        self.act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self.act_zoom_out.triggered.connect(self.timeline.zoom_out)
        self.view_menu.addAction(self.act_zoom_out)

        self.act_zoom_reset = QAction(self)
        self.act_zoom_reset.triggered.connect(self.timeline.zoom_reset)
        self.view_menu.addAction(self.act_zoom_reset)
        self.view_menu.addSeparator()

        self.act_show_audio_tracks = QAction(self)
        self.act_show_audio_tracks.setCheckable(True)
        self.act_show_audio_tracks.setChecked(self.show_audio_timeline)
        self.act_show_audio_tracks.toggled.connect(self._set_audio_timeline_visible)
        self.view_menu.addAction(self.act_show_audio_tracks)

        self.language_menu = self.view_menu.addMenu("")
        self.language_action_group = QActionGroup(self)
        self.language_action_group.setExclusive(True)
        self.act_language_en = QAction(self)
        self.act_language_en.setCheckable(True)
        self.act_language_en.triggered.connect(lambda: self.set_language("en"))
        self.language_action_group.addAction(self.act_language_en)
        self.language_menu.addAction(self.act_language_en)
        self.act_language_ru = QAction(self)
        self.act_language_ru.setCheckable(True)
        self.act_language_ru.triggered.connect(lambda: self.set_language("ru"))
        self.language_action_group.addAction(self.act_language_ru)
        self.language_menu.addAction(self.act_language_ru)

        # ----- Help -----
        self.help_menu = self.menuBar().addMenu("")
        self.act_help = QAction(self)
        self.act_help.setShortcut(QKeySequence("F1"))
        self.act_help.triggered.connect(self.show_help)
        self.help_menu.addAction(self.act_help)

        # Arrow seek shortcuts are intentionally not exposed as menu items.
        self.act_seek_left = QAction(self)
        self.act_seek_left.setShortcut(QKeySequence(Qt.Key.Key_Left))
        self.act_seek_left.triggered.connect(
            lambda: self.seek_seconds_smooth(max(0.0, self.current_seconds() - 1.0))
        )
        self.addAction(self.act_seek_left)

        self.act_seek_right = QAction(self)
        self.act_seek_right.setShortcut(QKeySequence(Qt.Key.Key_Right))
        self.act_seek_right.triggered.connect(
            lambda: self.seek_seconds_smooth(
                min(self.duration, self.current_seconds() + 1.0)
            )
        )
        self.addAction(self.act_seek_right)

    def _set_audio_timeline_visible(self, visible: bool):
        self.show_audio_timeline = bool(visible)
        self.audio_timeline_scroll.setVisible(self.show_audio_timeline)
        self.timeline_left_gutter.setVisible(self.show_audio_timeline)
        self.timeline_scroll_left_gutter.setVisible(self.show_audio_timeline)
        self.timeline_right_gutter.setVisible(self.show_audio_timeline)
        self.timeline_scroll_right_gutter.setVisible(self.show_audio_timeline)
        self.audio_timeline_title_label.setVisible(self.show_audio_timeline)
        self.settings.setValue("ui/show_audio_timeline", self.show_audio_timeline)

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
        self._edited_preview_jump_guard_timer.stop()
        self._cancel_preview_prime()
        self._seek_session_active = False
        self._resume_after_seek = False
        self._seek_was_playing = False
        self._edited_preview_jump_active = False
        self._seek_temp_muted = False
        self._apply_audio_mute_state()

        self._cancel_keyframe_scan()
        self.player.stop()
        self.player.setSource(QUrl())
        self._clear_preview_mix()
        self.video.clear_frame()

        self.input_path = ""
        self.duration = 0.0
        self.segments.clear()
        self.audio_tracks.clear()
        self.audio_probe_ok = False
        self.keyframes.clear()
        self.timeline.set_keyframes([])
        self._edited_preview_ranges.clear()
        self._edited_preview_ranges_exact = False
        self._edited_preview_has_deletions = False
        self.selected_index = -1
        self.undo_stack.clear()
        self.redo_stack.clear()

        self.timeline.zoom = 1.0
        self.timeline.offset = 0.0
        self.timeline.set_state(0.0, self.segments, 0.0, -1)

        self.time_label.setText("00:00.000 / 00:00.000")
        self.selection_label.setText(self._t("selection_none"))

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
        self.audio_tracks.clear()
        self.audio_probe_ok = False
        self.keyframes.clear()
        self.timeline.set_keyframes([])
        self._clear_preview_mix()
        self.selected_index = -1
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.timeline.zoom = 1.0
        self.timeline.offset = 0.0

        audio_probe_ok = False
        ffprobe = find_tool("ffprobe.exe")
        if ffprobe:
            try:
                self.audio_tracks = probe_audio_tracks(ffprobe, self.input_path)
                for index, track in enumerate(self.audio_tracks):
                    track.mix_enabled = index == 0
                audio_probe_ok = True
                self.audio_probe_ok = True
            except Exception:
                # Audio metadata is useful for editing, but a probe failure must
                # never make an otherwise playable video impossible to open.
                self.audio_tracks.clear()
                self.audio_probe_ok = False

        self._preview_prime_pending = True
        self.video.clear_frame()
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))
        self._rebuild_preview_mix()

        if audio_probe_ok:
            self.statusBar().showMessage(
                self._t(
                    "opened_with_audio",
                    name=video_path.name,
                    count=len(self.audio_tracks),
                )
            )
        else:
            self.statusBar().showMessage(
                self._t("opened_audio_probe_failed", name=video_path.name)
            )
        self._update_timeline()
        self._update_ui_state()

    def _cancel_keyframe_scan(self):
        self._keyframe_progress_show_timer.stop()
        self._hide_task_progress("keyframes")
        cancel_event = self._keyframe_scan_cancel_event
        if cancel_event is not None:
            cancel_event.set()

        # Any late signals from the old worker become stale immediately.
        self._keyframe_scan_generation += 1
        self._keyframe_scan_cancel_event = None
        self.keyframe_scan_thread = None

    def _start_keyframe_scan(self):
        if not self.input_path or self.duration <= 0 or self.keyframes:
            return
        if self.keyframe_scan_thread and self.keyframe_scan_thread.is_alive():
            return

        ffprobe = find_tool("ffprobe.exe")
        if not ffprobe:
            return

        self._keyframe_scan_generation += 1
        generation = self._keyframe_scan_generation
        cancel_event = threading.Event()
        self._keyframe_scan_cancel_event = cancel_event
        source_path = self.input_path
        duration = self.duration
        signals = self.keyframe_scan_signals

        self._keyframe_scan_percent = 0
        self.statusBar().showMessage(self._t("keyframe_scan_started"))

        def worker():
            try:
                keyframes = scan_video_keyframes(
                    ffprobe,
                    source_path,
                    duration=duration,
                    cancel_event=cancel_event,
                    progress_callback=lambda pct: signals.progress.emit(
                        generation, pct
                    ),
                )
            except KeyframeScanCancelled:
                return
            except Exception as exc:
                signals.failed.emit(generation, str(exc))
                return
            signals.finished.emit(generation, keyframes)

        thread = threading.Thread(
            target=worker,
            daemon=True,
            name="VFRFastCutKeyframeScan",
        )
        self.keyframe_scan_thread = thread
        thread.start()
        self._keyframe_progress_show_timer.start()

    def on_keyframe_scan_progress(self, generation: int, percent: int):
        if generation != self._keyframe_scan_generation:
            return
        self._keyframe_scan_percent = max(0, min(100, int(percent)))
        if self._task_progress_owner == "keyframes":
            self._update_task_progress(
                "keyframes",
                percent=self._keyframe_scan_percent,
                text=self._t(
                    "keyframe_scan_progress",
                    percent=self._keyframe_scan_percent,
                ),
            )
        if not self._export_busy:
            self.statusBar().showMessage(
                self._t("keyframe_scan_progress", percent=percent)
            )

    def on_keyframe_scan_finished(self, generation: int, keyframes):
        if generation != self._keyframe_scan_generation:
            return

        self._keyframe_progress_show_timer.stop()
        self._hide_task_progress("keyframes")
        self.keyframe_scan_thread = None
        self._keyframe_scan_cancel_event = None
        self.keyframes = sorted(
            set(float(value) for value in keyframes if value >= 0.0)
        )
        self.timeline.set_keyframes(self.keyframes)
        self._refresh_edited_preview_ranges()
        if not self._export_busy:
            self.statusBar().showMessage(
                self._t("keyframe_scan_finished", count=len(self.keyframes)),
                3500,
            )

    def on_keyframe_scan_failed(self, generation: int, error: str):
        if generation != self._keyframe_scan_generation:
            return

        self._keyframe_progress_show_timer.stop()
        self._hide_task_progress("keyframes")
        self.keyframe_scan_thread = None
        self._keyframe_scan_cancel_event = None
        self.keyframes.clear()
        self.timeline.set_keyframes([])
        self._refresh_edited_preview_ranges()
        if not self._export_busy:
            self.statusBar().showMessage(
                self._t("keyframe_scan_failed_status"),
                5000,
            )

    def _activate_after_drop(self):
        """Request foreground and keyboard focus after a successful file drop."""
        self.raise_()
        self.activateWindow()

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
        self._start_keyframe_scan()

    def _refresh_edited_preview_ranges(self):
        """Rebuild playable source-time ranges for edited-result preview."""
        self._edited_preview_has_deletions = any(
            seg.deleted for seg in self.segments
        )
        kept = kept_ranges_from_segments(self.segments)
        if not kept:
            self._edited_preview_ranges = []
            self._edited_preview_ranges_exact = bool(self.keyframes)
            return

        if self.keyframes and self.duration > 0:
            ranges, _max_shift = snap_ranges_to_keyframes(
                kept,
                self.keyframes,
                self.duration,
            )
            self._edited_preview_ranges = ranges
            self._edited_preview_ranges_exact = True
        else:
            # Keep preview usable while the background ffprobe scan is still
            # running (or unavailable). As soon as the map arrives this cache
            # is rebuilt with the exact export snapping rules.
            self._edited_preview_ranges = kept
            self._edited_preview_ranges_exact = False

    def _edited_preview_enabled(self) -> bool:
        return self._edited_preview_has_deletions

    def _is_edited_preview_playable(self, position: float) -> bool:
        if not self._edited_preview_enabled():
            return True
        index, _jump_target = resolve_preview_playback_position(
            self._edited_preview_ranges,
            position,
        )
        return index >= 0

    def _clear_edited_preview_jump_guard(self):
        self._edited_preview_jump_active = False

    def _jump_edited_preview_to(self, seconds: float):
        if self.duration <= 0:
            return
        seconds = max(0.0, min(self.duration, float(seconds)))
        target_ms = int(round(seconds * 1000.0))

        self._edited_preview_jump_active = True
        self._edited_preview_jump_guard_timer.start()
        self.player.setPosition(target_ms)
        self.timeline.ensure_time_visible(seconds)
        self._sync_preview_mix_transport(
            force_seek=True,
            project_position_ms=target_ms,
        )
        self._apply_preview_mix_gains(project_position=seconds)

    def _maybe_route_edited_preview_playback(self, position: float) -> bool:
        """Skip removed source-time gaps while normal playback is running."""
        if (
            not self._edited_preview_enabled()
            or self._edited_preview_jump_active
            or self._preview_priming
            or self._seek_session_active
            or self.player.playbackState()
            != QMediaPlayer.PlaybackState.PlayingState
        ):
            return False

        range_index, jump_target = resolve_preview_playback_position(
            self._edited_preview_ranges,
            position,
        )
        if range_index >= 0:
            return False

        if jump_target is not None:
            self._jump_edited_preview_to(jump_target)
            return True

        # No future kept range. If the edit ends before source EOF, stop on the
        # last kept frame instead of continuing into the trailing deleted area.
        if self._edited_preview_ranges:
            last_start, last_end = self._edited_preview_ranges[-1]
            if last_end < self.duration - 0.001:
                self.player.pause()
                stop_at = max(last_start, last_end - 0.001)
                self._jump_edited_preview_to(stop_at)
                self._sync_play_button(QMediaPlayer.PlaybackState.PausedState)
                return True
        else:
            self.player.pause()
            self._sync_play_button(QMediaPlayer.PlaybackState.PausedState)
            self.statusBar().showMessage(
                self._t("preview_nothing_to_play"),
                2500,
            )
            return True

        return False

    def on_position_changed(self, ms: int):
        pos = ms / 1000.0
        if self._maybe_route_edited_preview_playback(pos):
            return
        self.timeline.set_position(pos)
        self.audio_timeline.set_position(pos)
        self.time_label.setText(
            f"{fmt_time(pos)} / {fmt_time(self.duration)}"
        )
        self._refresh_remove_cut_state(pos)
        self._sync_preview_mix_transport(project_position_ms=ms)
        self._apply_preview_mix_gains(project_position=pos)

    def on_playback_state_changed(self, state):
        # Preview priming and smooth seeking temporarily change the real
        # QMediaPlayer state for technical reasons. Those transitions must not
        # make the user-facing Play/Pause button flicker.
        if self._preview_priming:
            return

        # Hard-align every preview-mix channel once when playback starts.
        # During normal playback channels run freely; repeated clock chasing
        # would recreate the compressed-audio crackle fixed earlier.
        self._sync_preview_mix_transport(
            state,
            force_seek=(
                state == QMediaPlayer.PlaybackState.PlayingState
            ),
        )

        if self._seek_session_active:
            return
        self._sync_play_button(state)

    def _set_play_button_playing(self, playing: bool):
        self.play_btn.setText(
            self._t("pause") if playing else self._t("play")
        )
        action = getattr(self, "act_play", None)
        if action is not None:
            action.setText(
                self._t("menu_pause") if playing else self._t("menu_play")
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
            self._seek_was_playing = (
                self.player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
            )

            if self._seek_was_playing:
                self.player.pause()

            self._seek_temp_muted = True
            self._apply_audio_mute_state()

        # Manual seek is allowed everywhere, including removed source ranges.
        # If a seek that started during playback lands in a removed/effectively
        # snapped-out region, remain paused so the user can inspect that frame.
        self._resume_after_seek = (
            self._seek_was_playing
            and self._is_edited_preview_playable(seconds)
        )
        self._set_play_button_playing(self._resume_after_seek)

        target_ms = int(seconds * 1000)
        self.player.setPosition(target_ms)
        self._sync_preview_mix_transport(
            force_seek=True,
            project_position_ms=target_ms,
        )
        self.timeline.ensure_time_visible(seconds)

        # Every new seek restarts the quiet period. Audio is restored only
        # after the user has stopped seeking for a while.
        self._seek_timer.start()

    def _finish_smooth_seek(self):
        resume_playback = self._resume_after_seek
        self._resume_after_seek = False
        self._seek_was_playing = False

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
        muted = self.preview_muted or self._seek_temp_muted
        # With known tracks the video player must stay silent; every audible
        # stream comes from the live preview mixer. ffprobe failure keeps the
        # legacy single-output fallback alive.
        self.audio.setMuted(True if self.audio_probe_ok else muted)
        for channel in self.preview_mix_channels.values():
            channel.audio.setMuted(muted)

    def toggle_mute(self):
        self.preview_muted = not self.preview_muted
        self.mute_btn.blockSignals(True)
        self.mute_btn.setChecked(self.preview_muted)
        self.mute_btn.setText(self._t("unmute") if self.preview_muted else self._t("mute"))
        self.mute_btn.blockSignals(False)
        action = getattr(self, "act_mute", None)
        if action is not None:
            action.setChecked(self.preview_muted)
            action.setText(
                self._t("unmute") if self.preview_muted else self._t("menu_mute")
            )
        self._apply_audio_mute_state()

    def _preview_kept_range_at(
        self,
        position: float,
    ) -> Optional[tuple[float, float]]:
        """Return the effective range used by Edited Preview and export."""
        for start, end in self._edited_preview_ranges:
            if start - 0.001 <= position <= end + 0.001:
                return start, end
        return None

    def _preview_fade_gain(
        self,
        track: Optional[AudioTrack],
        project_position: float,
    ) -> float:
        if track is None or not _track_has_fade(track):
            return 1.0

        active_range = self._preview_kept_range_at(project_position)
        if active_range is None:
            return 1.0

        audible_start, audible_end = active_range
        if track.source_type == "external":
            project_start, project_end = _external_project_window(track)
            audible_start = max(audible_start, project_start)
            if math.isfinite(project_end):
                audible_end = min(audible_end, project_end)

        if audible_end <= audible_start:
            return 1.0

        position = max(audible_start, min(audible_end, project_position))
        gain = 1.0

        if track.fade_in_seconds > 0.0005:
            gain = min(
                gain,
                max(0.0, min(1.0, (position - audible_start) / track.fade_in_seconds)),
            )

        if track.fade_out_seconds > 0.0005:
            gain = min(
                gain,
                max(0.0, min(1.0, (audible_end - position) / track.fade_out_seconds)),
            )

        return gain

    def on_volume_changed(self, value: int):
        value = max(0, min(100, int(value)))
        self._apply_preview_mix_gains()
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
            self._seek_was_playing = False

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return

        if self._edited_preview_enabled():
            range_index, jump_target = resolve_preview_playback_position(
                self._edited_preview_ranges,
                self.current_seconds(),
            )
            if range_index < 0:
                if jump_target is None:
                    self.statusBar().showMessage(
                        self._t("preview_nothing_to_play"),
                        2500,
                    )
                    return
                self._jump_edited_preview_to(jump_target)

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
        self.audio_timeline.set_view(offset, visible_duration)

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
        self.audio_timeline.set_view(
            self.timeline.offset,
            self.timeline.visible_duration,
        )

    def _snapshot(self):
        self.undo_stack.append(clone_segments(self.segments))
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def toggle_split_cut_at_playhead(self):
        """Run Split normally, or Remove cut when playhead is on a cut."""
        if self._cut_index_at_playhead() >= 1:
            self.remove_cut_at_playhead()
        else:
            self.split_at_playhead()

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

    def _cut_index_at_time(
        self,
        seconds: float,
        tolerance: float = 0.005,
    ) -> int:
        """Return the right-hand segment index for a cut near ``seconds``."""
        if len(self.segments) < 2:
            return -1

        cuts = self._cut_positions()
        index = bisect.bisect_left(cuts, seconds)
        candidates = []
        if index < len(cuts):
            candidates.append(index)
        if index > 0:
            candidates.append(index - 1)

        for cut_index in candidates:
            if abs(cuts[cut_index] - seconds) <= tolerance:
                return cut_index + 1
        return -1

    def _cut_index_at_playhead(self, tolerance: float = 0.005) -> int:
        return self._cut_index_at_time(self.current_seconds(), tolerance)

    def _can_remove_cut_at(
        self,
        seconds: float,
        tolerance: float = 0.005,
    ) -> bool:
        right_index = self._cut_index_at_time(seconds, tolerance)
        if right_index < 1:
            return False
        left = self.segments[right_index - 1]
        right = self.segments[right_index]
        return left.deleted == right.deleted

    def _refresh_remove_cut_state(self, seconds: Optional[float] = None):
        if seconds is None:
            seconds = self.current_seconds()

        editable = (
            not self._export_busy
            and self.duration > 0
            and bool(self.segments)
        )
        on_cut = self._cut_index_at_time(seconds) >= 1
        removable = editable and self._can_remove_cut_at(seconds)

        # The fixed-size essentials button is context-sensitive, mirroring the
        # existing Delete/Restore button without changing the toolbar geometry.
        if on_cut:
            self.split_btn.setText(self._t("remove_cut"))
            self.split_btn.setToolTip(self._t("remove_cut_tip"))
            self.split_btn.setEnabled(removable)
        else:
            self.split_btn.setText(self._t("split"))
            self.split_btn.setToolTip("")
            self.split_btn.setEnabled(editable)

        action = getattr(self, "remove_cut_action", None)
        if action is not None:
            action.setEnabled(removable)

    def remove_cut_at_playhead(self):
        if self._export_busy:
            return
        if len(self.segments) < 2 or self.duration <= 0:
            return

        right_index = self._cut_index_at_playhead()
        if right_index < 0:
            self.statusBar().showMessage(
                self._t("no_cut_at_playhead"), 3000
            )
            return

        left = self.segments[right_index - 1]
        right = self.segments[right_index]

        # Joining segments with different deletion states would silently decide
        # whether media should be restored or deleted. Require the user to make
        # both sides consistent first instead.
        if left.deleted != right.deleted:
            self.statusBar().showMessage(
                self._t("cut_state_mismatch"), 4000
            )
            return

        cut_time = right.start
        self._snapshot()
        merged = Segment(left.start, right.end, left.deleted)
        self.segments[right_index - 1:right_index + 1] = [merged]
        self.selected_index = right_index - 1
        self._refresh_selection_label()
        self._update_timeline()
        self._update_ui_state()
        self.statusBar().showMessage(
            self._t("cut_removed_status", time=fmt_time(cut_time)),
            2500,
        )

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

    def toggle_selected_segment_state(self):
        if not (0 <= self.selected_index < len(self.segments)):
            return
        if self.segments[self.selected_index].deleted:
            self.restore_selected()
        else:
            self.delete_selected()

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
        self._refresh_edited_preview_ranges()
        self.timeline.set_state(
            self.duration,
            self.segments,
            self.current_seconds(),
            self.selected_index,
        )
        self._update_audio_timeline()

    def _update_audio_timeline(self):
        visible_tracks = [
            track for track in self.audio_tracks if track.export_enabled
        ]
        self.audio_timeline.set_state(
            self.duration,
            visible_tracks,
            self.segments,
            self.current_seconds(),
            self.timeline.offset,
            self.timeline.visible_duration,
        )

    def on_audio_timeline_timing_changed(
        self,
        track: AudioTrack,
        edit_kind: str,
    ):
        # The timeline edits the real AudioTrack object in-place. While dragging
        # repaint only; hard-syncing all live-mix players on every mouse move
        # would recreate the seek-related crackle fixed in 0.3.x.
        status_key = (
            "audio_timeline_trim_status"
            if edit_kind.startswith("trim_")
            else "audio_timeline_offset_status"
        )
        self.statusBar().showMessage(self._t(status_key), 800)

    def on_audio_timeline_timing_drag_finished(
        self,
        track: AudioTrack,
        edit_kind: str,
    ):
        # One hard synchronization on mouse release applies the new position /
        # trim to the complete preview mix without continuous micro-seeks.
        self._sync_preview_mix_transport(force_seek=True)
        self._apply_preview_mix_gains()
        self._update_audio_timeline()

    def on_audio_mix_track_toggled(
        self,
        track: AudioTrack,
        enabled: bool,
    ):
        if self._export_busy:
            return
        model_track = self._audio_track_by_key(self._audio_track_key(track))
        if model_track is None or not model_track.export_enabled:
            return
        model_track.mix_enabled = bool(enabled)
        self._rebuild_preview_mix()
        self._update_ui_state()
        self.statusBar().showMessage(
            self._t(
                "audio_mix_track_enabled_status"
                if model_track.mix_enabled
                else "audio_mix_track_disabled_status",
                track=self._audio_track_short_label(model_track),
            ),
            1800,
        )

    def _audio_track_key(self, track: AudioTrack) -> tuple[str, str, int, str]:
        return (
            track.source_type,
            self._normalized_file_path(track.source_path),
            track.stream_index,
            track.instance_id,
        )

    def _audio_source_key(self, track: AudioTrack) -> tuple[str, str, int]:
        """Identity of the underlying media stream, ignoring timeline copies."""
        return (
            track.source_type,
            self._normalized_file_path(track.source_path),
            track.stream_index,
        )

    def _audio_track_by_key(
        self,
        track_key: tuple[str, str, int, str],
    ) -> Optional[AudioTrack]:
        return next(
            (
                track
                for track in self.audio_tracks
                if self._audio_track_key(track) == track_key
            ),
            None,
        )

    def _visible_audio_tracks(self) -> list[AudioTrack]:
        """Tracks shown on the project timeline and available for export."""
        return [track for track in self.audio_tracks if track.export_enabled]

    def _active_preview_mix_tracks(self) -> list[AudioTrack]:
        """Visible tracks whose Play flag includes them in the live mix."""
        return [
            track
            for track in self.audio_tracks
            if track.export_enabled and track.mix_enabled
        ]

    def _disable_main_player_audio(self):
        """The main QMediaPlayer is the video/transport clock, not the mixer."""
        if self.audio_probe_ok:
            self.audio.setMuted(True)
            if self.player.audioTracks() and self.player.activeAudioTrack() != -1:
                self.player.setActiveAudioTrack(-1)
        else:
            # Preserve the legacy fallback when ffprobe could not enumerate
            # source streams. There is no reliable way to build per-track mix.
            self._apply_audio_mute_state()
            self.audio.setVolume(
                max(0.0, min(1.0, self.volume_slider.value() / 100.0))
            )

    def _clear_preview_mix(self):
        for channel in self.preview_mix_channels.values():
            channel.stop_and_clear()
            channel.deleteLater()
        self.preview_mix_channels.clear()

    def _rebuild_preview_mix(self):
        """Match live preview players to tracks whose Play flag is active."""
        desired_tracks = self._active_preview_mix_tracks()
        desired = {
            self._audio_track_key(track): track
            for track in desired_tracks
        }

        for key in list(self.preview_mix_channels):
            if key in desired:
                continue
            channel = self.preview_mix_channels.pop(key)
            channel.stop_and_clear()
            channel.deleteLater()

        for key, track in desired.items():
            channel = self.preview_mix_channels.get(key)
            if channel is None:
                self.preview_mix_channels[key] = PreviewMixChannel(track, self)
            else:
                # AudioTrack objects may be replaced transactionally by the
                # selection dialog; keep the live channel pointed at the model.
                channel.track = track

        self._disable_main_player_audio()
        self._apply_audio_mute_state()
        self._apply_preview_mix_gains()
        self._sync_preview_mix_transport(force_seek=True)
        self._update_audio_timeline()
        self._refresh_audio_menu()

    def _sync_preview_mix_transport(
        self,
        state=None,
        force_seek: bool = False,
        project_position_ms: Optional[int] = None,
    ):
        if not self.audio_probe_ok:
            return
        if project_position_ms is None:
            project_position_ms = self.player.position()
        if state is None:
            state = self.player.playbackState()
        if self._preview_priming:
            state = QMediaPlayer.PlaybackState.PausedState

        for channel in self.preview_mix_channels.values():
            channel.sync_transport(
                int(project_position_ms),
                state,
                force_seek=force_seek,
            )

    def _apply_preview_mix_gains(
        self,
        project_position: Optional[float] = None,
    ):
        global_gain = max(
            0.0,
            min(1.0, self.volume_slider.value() / 100.0),
        )
        if not self.audio_probe_ok:
            self.audio.setVolume(global_gain)
            return

        if project_position is None:
            project_position = self.current_seconds()

        for key, channel in self.preview_mix_channels.items():
            track = self._audio_track_by_key(key) or channel.track
            track_gain = max(
                0.0,
                min(1.0, track.volume_percent / 100.0),
            )
            fade_gain = self._preview_fade_gain(track, project_position)
            channel.set_gain(global_gain * track_gain * fade_gain)

    def _sync_audio_output_actions(self):
        for action, checked in (
            (getattr(self, "act_main_mix", None), self.export_main_mix),
            (
                getattr(self, "act_keep_stems", None),
                self.export_separate_audio_tracks,
            ),
        ):
            if action is None:
                continue
            action.blockSignals(True)
            action.setChecked(bool(checked))
            action.blockSignals(False)

    def _on_audio_output_mode_changed(self, checked: bool):
        if not hasattr(self, "act_main_mix"):
            return
        had_destination = (
            self.export_main_mix or self.export_separate_audio_tracks
        )
        self.export_main_mix = self.act_main_mix.isChecked()
        self.export_separate_audio_tracks = self.act_keep_stems.isChecked()

        any_destination = (
            self.export_main_mix or self.export_separate_audio_tracks
        )
        has_audio = (
            not self.audio_probe_ok
            or self._selected_audio_track_count() > 0
        )

        self.export_audio_check.blockSignals(True)
        if not any_destination:
            self.export_audio_check.setChecked(False)
        elif checked and not had_destination and has_audio:
            # Re-enabling an output destination after both were disabled also
            # re-opens the global audio gate. Merely changing modes while audio
            # is globally disabled does not unexpectedly turn audio back on.
            self.export_audio_check.setChecked(True)
        self.export_audio_check.blockSignals(False)
        self._update_ui_state()

    def show_audio_timeline_context_menu(self, track: AudioTrack, global_pos):
        if self._export_busy:
            return
        model_track = self._audio_track_by_key(self._audio_track_key(track))
        if model_track is None or not model_track.export_enabled:
            return

        track_key = self._audio_track_key(model_track)
        menu = QMenu(self)

        volume_action = menu.addAction(
            f"{self._t('menu_track_volume')}  {model_track.volume_percent}%"
        )
        fade_in_action = menu.addAction(
            f"{self._t('menu_track_fade_in')}  "
            f"{model_track.fade_in_seconds:.3f} s"
        )
        fade_out_action = menu.addAction(
            f"{self._t('menu_track_fade_out')}  "
            f"{model_track.fade_out_seconds:.3f} s"
        )
        reset_action = menu.addAction(self._t("menu_track_reset_processing"))

        duplicate_action = None
        delete_copy_action = None
        if model_track.source_type == "external":
            menu.addSeparator()
            duplicate_action = menu.addAction(
                self._t("menu_duplicate_external_audio")
            )
            if model_track.copy_number > 1:
                delete_copy_action = menu.addAction(
                    self._t("menu_delete_external_audio_copy")
                )

        chosen = menu.exec(global_pos)
        if chosen is volume_action:
            self._edit_track_value(
                track_key,
                "volume_percent",
                "audio_track_volume",
                0.0,
                100.0,
                0,
                5.0,
                " %",
            )
        elif chosen is fade_in_action:
            self._edit_track_value(
                track_key,
                "fade_in_seconds",
                "audio_track_fade_in",
                0.0,
                3600.0,
                3,
                0.100,
                " s",
            )
        elif chosen is fade_out_action:
            self._edit_track_value(
                track_key,
                "fade_out_seconds",
                "audio_track_fade_out",
                0.0,
                3600.0,
                3,
                0.100,
                " s",
            )
        elif chosen is reset_action:
            self._reset_track_processing(track_key)
        elif duplicate_action is not None and chosen is duplicate_action:
            self.duplicate_external_audio(track_key)
        elif delete_copy_action is not None and chosen is delete_copy_action:
            self.delete_external_audio_copy(track_key)

    def duplicate_external_audio(
        self,
        track_key: tuple[str, str, int, str],
    ):
        """Create another timeline instance of one external audio stream."""
        if self._export_busy:
            return
        source = self._audio_track_by_key(track_key)
        if source is None or source.source_type != "external":
            return

        source_key = self._audio_source_key(source)
        next_copy_number = 1 + max(
            (
                track.copy_number
                for track in self.audio_tracks
                if self._audio_source_key(track) == source_key
            ),
            default=0,
        )

        source_start, source_end = _external_source_window(source)
        clip_duration = max(0.010, source_end - source_start)
        desired_offset = source.offset_seconds + clip_duration

        # Prefer placing a duplicate immediately after the source clip. Close to
        # project EOF, keep as much of the new copy visible as possible so it
        # can still be grabbed and moved on the timeline.
        if self.duration > 0 and source.duration_seconds > 0:
            minimum = -source_end + AudioTimelineWidget.MIN_CLIP_SECONDS
            maximum = (
                self.duration
                - source_start
                - AudioTimelineWidget.MIN_CLIP_SECONDS
            )
            if clip_duration <= self.duration:
                desired_offset = min(
                    desired_offset,
                    self.duration - source_end,
                )
            desired_offset = max(minimum, min(maximum, desired_offset))

        duplicate = replace(
            source,
            instance_id=uuid.uuid4().hex,
            copy_number=next_copy_number,
            offset_seconds=round(desired_offset, 3),
            export_enabled=True,
            mix_enabled=True,
        )
        source_index = self.audio_tracks.index(source)
        self.audio_tracks.insert(source_index + 1, duplicate)

        if self.export_main_mix or self.export_separate_audio_tracks:
            self.export_audio_check.blockSignals(True)
            self.export_audio_check.setChecked(True)
            self.export_audio_check.blockSignals(False)

        self._rebuild_preview_mix()
        self._update_ui_state()
        self.statusBar().showMessage(
            self._t(
                "external_audio_duplicated_status",
                track=self._audio_track_short_label(duplicate),
            ),
            2200,
        )

    def delete_external_audio_copy(
        self,
        track_key: tuple[str, str, int, str],
    ):
        """Delete only a duplicated external-audio timeline instance."""
        if self._export_busy:
            return

        track = self._audio_track_by_key(track_key)
        if (
            track is None
            or track.source_type != "external"
            or track.copy_number <= 1
        ):
            return

        label = self._audio_track_short_label(track)
        self.remove_external_audio(track_key)
        self.statusBar().showMessage(
            self._t("external_audio_copy_deleted_status", track=label),
            2200,
        )

    def _recent_external_audio_paths(self) -> list[str]:
        value = self.settings.value("audio/recent_external_files", [])
        if isinstance(value, str):
            candidates = [value] if value else []
        elif isinstance(value, (list, tuple)):
            candidates = [str(item) for item in value]
        else:
            candidates = []

        paths: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if not path.is_file():
                continue
            key = self._normalized_file_path(str(path))
            if key in seen:
                continue
            seen.add(key)
            paths.append(str(path))
            if len(paths) >= 10:
                break

        # Prune stale/moved files lazily when the menu is next refreshed.
        stored = [str(item) for item in candidates[:10]]
        if paths != stored:
            self.settings.setValue("audio/recent_external_files", paths)
        return paths

    def _remember_recent_external_audio(self, path: str):
        normalized = self._normalized_file_path(path)
        recent = [
            item
            for item in self._recent_external_audio_paths()
            if self._normalized_file_path(item) != normalized
        ]
        recent.insert(0, str(Path(path)))
        self.settings.setValue("audio/recent_external_files", recent[:10])

    def _refresh_recent_external_audio_menu(self, editable: bool):
        for action in self.recent_external_actions:
            self.add_external_menu.removeAction(action)
            action.deleteLater()
        self.recent_external_actions.clear()

        recent = self._recent_external_audio_paths()
        if not recent:
            action = self.add_external_menu.addAction(
                self._t("menu_no_recent_external_audio")
            )
            action.setEnabled(False)
            self.recent_external_actions.append(action)
            return

        for path in recent:
            action = self.add_external_menu.addAction(Path(path).name)
            action.setToolTip(path)
            action.setEnabled(editable)
            action.triggered.connect(
                lambda _checked=False, recent_path=path: self._add_external_audio_path(
                    recent_path
                )
            )
            self.recent_external_actions.append(action)

    def add_external_audio(self):
        if self._export_busy or not self.input_path:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("audio_file_dialog"),
            str(Path(self.input_path).parent),
            self._t("audio_file_filter"),
        )
        if path:
            self._add_external_audio_path(path)

    def _add_external_audio_path(self, path: str):
        if self._export_busy or not self.input_path:
            return

        ffprobe = find_tool("ffprobe.exe")
        if not ffprobe:
            QMessageBox.critical(
                self,
                APP_NAME,
                self._t("tools_missing", missing="ffprobe.exe"),
            )
            return

        audio_path = Path(path)
        if not audio_path.is_file():
            QMessageBox.warning(self, APP_NAME, self._t("file_not_found"))
            self._refresh_audio_menu()
            return

        path = str(audio_path)
        if self._normalized_file_path(path) == self._normalized_file_path(
            self.input_path
        ):
            QMessageBox.information(
                self,
                APP_NAME,
                self._t("external_audio_is_source"),
            )
            return

        try:
            discovered = probe_audio_tracks(
                ffprobe,
                path,
                source_type="external",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                APP_NAME,
                self._t("external_audio_probe_failed", error=str(exc)),
            )
            return

        if not discovered:
            QMessageBox.information(
                self,
                APP_NAME,
                self._t("external_audio_no_streams"),
            )
            return

        existing_sources = {
            self._audio_source_key(track)
            for track in self.audio_tracks
            if track.source_type == "external"
        }
        new_tracks = [
            track
            for track in discovered
            if self._audio_source_key(track) not in existing_sources
        ]
        for track in new_tracks:
            track.mix_enabled = True
            track.copy_number = 1
        if not new_tracks:
            QMessageBox.information(
                self,
                APP_NAME,
                self._t("external_audio_duplicate"),
            )
            return

        self.audio_tracks.extend(new_tracks)
        self._remember_recent_external_audio(path)
        if self.export_main_mix or self.export_separate_audio_tracks:
            self.export_audio_check.blockSignals(True)
            self.export_audio_check.setChecked(True)
            self.export_audio_check.blockSignals(False)
        self._rebuild_preview_mix()
        self._update_ui_state()

    def remove_external_audio(self, track_key: tuple[str, str, int, str]):
        if self._export_busy:
            return
        removed = next(
            (
                track
                for track in self.audio_tracks
                if self._audio_track_key(track) == track_key
                and track.source_type == "external"
            ),
            None,
        )
        if removed is None:
            return

        self.audio_tracks = [
            track
            for track in self.audio_tracks
            if self._audio_track_key(track) != track_key
        ]

        if (
            self.audio_probe_ok
            and self._selected_audio_track_count() == 0
        ):
            self.export_audio_check.blockSignals(True)
            self.export_audio_check.setChecked(False)
            self.export_audio_check.blockSignals(False)

        self._rebuild_preview_mix()
        self._update_ui_state()

    def _refresh_audio_menu(self):
        if not hasattr(self, "audio_menu"):
            return

        editable = bool(self.input_path) and not self._export_busy
        self.act_audio_tracks.setEnabled(editable)
        self.act_add_external_audio.setEnabled(editable)
        self.act_choose_external_audio.setEnabled(editable)
        self._refresh_recent_external_audio_menu(editable)

        self._sync_audio_output_actions()
        self.act_main_mix.setEnabled(editable)
        self.act_keep_stems.setEnabled(editable)

        self.remove_external_menu.clear()
        external_tracks = [
            track
            for track in self.audio_tracks
            if track.source_type == "external"
        ]
        if external_tracks:
            for track in external_tracks:
                action = self.remove_external_menu.addAction(
                    self._audio_track_short_label(track)
                )
                key = self._audio_track_key(track)
                action.triggered.connect(
                    lambda _checked=False, item_key=key: self.remove_external_audio(
                        item_key
                    )
                )
        else:
            action = self.remove_external_menu.addAction(
                self._t("menu_no_external_audio")
            )
            action.setEnabled(False)
        self.remove_external_menu.setEnabled(editable and bool(external_tracks))

        # Every selected/displayed track is shown directly in the Audio menu.
        # There is no special preview track: every visible row is audible.
        for action in self.audio_track_setting_actions:
            self.audio_menu.removeAction(action)
            action.deleteLater()
        self.audio_track_setting_actions.clear()

        menu_tracks = self._visible_audio_tracks()
        if not menu_tracks:
            action = self.audio_menu.addAction(
                self._t("menu_no_active_audio_tracks")
            )
            action.setEnabled(False)
            self.audio_track_setting_actions.append(action)
            return

        for track in menu_tracks:
            track_key = self._audio_track_key(track)
            mix_marker = "▶" if track.mix_enabled else "▷"
            submenu = self.audio_menu.addMenu(
                f"{mix_marker} {self._audio_track_short_label(track)}"
            )
            submenu.setEnabled(editable)
            self.audio_track_setting_actions.append(submenu.menuAction())

            volume_action = submenu.addAction(
                f"{self._t('menu_track_volume')}  {track.volume_percent}%"
            )
            volume_action.setToolTip(self._t("audio_track_volume_tip"))
            volume_action.triggered.connect(
                lambda _checked=False, key=track_key: self._edit_track_value(
                    key,
                    "volume_percent",
                    "audio_track_volume",
                    0.0,
                    100.0,
                    0,
                    5.0,
                    " %",
                )
            )

            fade_in_action = submenu.addAction(
                f"{self._t('menu_track_fade_in')}  {track.fade_in_seconds:.3f} s"
            )
            fade_in_action.setToolTip(self._t("audio_track_fade_tip"))
            fade_in_action.triggered.connect(
                lambda _checked=False, key=track_key: self._edit_track_value(
                    key,
                    "fade_in_seconds",
                    "audio_track_fade_in",
                    0.0,
                    3600.0,
                    3,
                    0.100,
                    " s",
                )
            )

            fade_out_action = submenu.addAction(
                f"{self._t('menu_track_fade_out')}  {track.fade_out_seconds:.3f} s"
            )
            fade_out_action.setToolTip(self._t("audio_track_fade_tip"))
            fade_out_action.triggered.connect(
                lambda _checked=False, key=track_key: self._edit_track_value(
                    key,
                    "fade_out_seconds",
                    "audio_track_fade_out",
                    0.0,
                    3600.0,
                    3,
                    0.100,
                    " s",
                )
            )

            if track.source_type == "external":
                duplicate_action = submenu.addAction(
                    self._t("menu_duplicate_external_audio")
                )
                duplicate_action.triggered.connect(
                    lambda _checked=False, key=track_key: self.duplicate_external_audio(
                        key
                    )
                )

            submenu.addSeparator()
            reset_action = submenu.addAction(
                self._t("menu_track_reset_processing")
            )
            reset_action.triggered.connect(
                lambda _checked=False, key=track_key: self._reset_track_processing(key)
            )

    def _edit_track_value(
        self,
        track_key: tuple[str, str, int, str],
        attribute: str,
        setting_key: str,
        minimum: float,
        maximum: float,
        decimals: int,
        step: float,
        suffix: str,
    ):
        track = self._audio_track_by_key(track_key)
        if track is None or self._export_busy or not track.export_enabled:
            return

        dialog = QDialog(self)
        setting = self._t(setting_key).rstrip(":… ")
        track_name = self._audio_track_short_label(track)
        dialog.setWindowTitle(
            self._t(
                "audio_track_value_dialog",
                setting=setting,
                track=track_name,
            )
        )
        dialog.setMinimumWidth(360)

        layout = QVBoxLayout(dialog)
        row = QHBoxLayout()
        row.addWidget(QLabel(self._t(setting_key), dialog))
        spin = QDoubleSpinBox(dialog)
        spin.setDecimals(decimals)
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setValue(float(getattr(track, attribute)))
        row.addWidget(spin, 1)
        layout.addLayout(row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        apply_btn = QPushButton(self._t("audio_tracks_apply"), dialog)
        cancel_btn = QPushButton(self._t("audio_tracks_cancel"), dialog)
        apply_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        value = spin.value()
        if attribute == "volume_percent":
            value = int(round(value))
        else:
            value = float(value)
        setattr(track, attribute, value)
        self._apply_preview_mix_gains()
        self._update_audio_timeline()
        self._refresh_audio_menu()
        self.statusBar().showMessage(
            self._t(
                "audio_track_setting_status",
                setting=setting,
                track=track_name,
            ),
            1800,
        )

    def _reset_track_processing(
        self,
        track_key: tuple[str, str, int, str],
    ):
        track = self._audio_track_by_key(track_key)
        if track is None or self._export_busy or not track.export_enabled:
            return
        track.volume_percent = 100
        track.fade_in_seconds = 0.0
        track.fade_out_seconds = 0.0
        self._apply_preview_mix_gains()
        self._update_audio_timeline()
        self._refresh_audio_menu()
        self.statusBar().showMessage(
            self._t(
                "audio_track_processing_reset_status",
                track=self._audio_track_short_label(track),
            ),
            1800,
        )

    def _on_export_audio_toggled(self, checked: bool):
        if checked and not (self.export_main_mix or self.export_separate_audio_tracks):
            self.export_main_mix = True
            self.export_separate_audio_tracks = False
            self._sync_audio_output_actions()

        # The global checkbox is a gate. Turning it off does not forget the
        # per-track selection. Turning it back on after all tracks were
        # explicitly cleared is treated as "enable audio again" and restores
        # all known tracks.
        if checked and self.audio_probe_ok and not self.audio_tracks:
            # There is nothing known to export. Keep the global state honest;
            # the user can add an external track from the Audio menu.
            self.export_audio_check.blockSignals(True)
            self.export_audio_check.setChecked(False)
            self.export_audio_check.blockSignals(False)
            self._update_ui_state()
            return

        if (
            checked
            and self.audio_probe_ok
            and self.audio_tracks
            and self._selected_audio_track_count() == 0
        ):
            for track in self.audio_tracks:
                track.export_enabled = True
            self._rebuild_preview_mix()

        self._update_ui_state()
        self._refresh_audio_menu()

    def _selected_audio_track_count(self) -> int:
        return sum(1 for track in self.audio_tracks if track.export_enabled)

    def _audio_export_enabled(self) -> bool:
        """Return whether export should include at least one audio stream.

        When ffprobe metadata is unavailable we preserve the legacy fallback
        and let FFmpeg map optional audio streams with ``0:a?``.
        """
        if not self.export_audio_check.isChecked():
            return False
        if not (self.export_main_mix or self.export_separate_audio_tracks):
            return False
        if not self.audio_probe_ok:
            return True
        selected = [track for track in self.audio_tracks if track.export_enabled]
        if self.export_separate_audio_tracks and selected:
            return True
        if self.export_main_mix and any(track.mix_enabled for track in selected):
            return True
        return False

    def _refresh_audio_tracks_control(self):
        total = len(self.audio_tracks)
        selected = self._selected_audio_track_count()

        if total:
            self.audio_timeline_title_label.setText(
                f"{self._t('audio_timeline')} · {selected}/{total}"
            )
            tip = self._t(
                "audio_tracks_tip",
                selected=selected,
                total=total,
            )
        else:
            self.audio_timeline_title_label.setText(self._t("audio_timeline"))
            if not self.input_path:
                tip = self._t("audio_tracks_no_file_tip")
            elif self.audio_probe_ok:
                tip = self._t("audio_tracks_none_tip")
            else:
                tip = self._t("audio_tracks_unavailable_tip")

        self.audio_timeline_title_label.setToolTip(tip)
        action = getattr(self, "act_audio_tracks", None)
        if action is not None:
            action.setToolTip(tip)
            action.setEnabled(bool(self.input_path) and not self._export_busy)

    def _audio_track_short_label(self, track: AudioTrack) -> str:
        if track.source_type == "external":
            suffix = f" #{track.copy_number}" if track.copy_number > 1 else ""
            return f"EXT • {Path(track.source_path).name}{suffix}"
        base = f"A{track.audio_index + 1}"
        detail = track.title.strip() if track.title else ""
        if not detail and track.codec_name:
            detail = track.codec_name.upper()
        return f"{base} • {detail}" if detail else base

    def _audio_track_label(self, track: AudioTrack) -> str:
        if track.source_type == "external":
            parts = [
                self._t(
                    "audio_track_external",
                    name=(
                        Path(track.source_path).name
                        + (f" #{track.copy_number}" if track.copy_number > 1 else "")
                    ),
                ),
                self._t(
                    "audio_track_external_stream",
                    number=track.audio_index + 1,
                ),
            ]
        else:
            parts = [
                self._t("audio_track_number", number=track.audio_index + 1)
            ]

        if track.title:
            parts.append(track.title)
        if track.codec_name:
            parts.append(track.codec_name.upper())
        if track.channel_layout:
            parts.append(track.channel_layout)
        elif track.channels:
            parts.append(self._t("audio_track_channels", count=track.channels))
        if track.sample_rate:
            if track.sample_rate % 1000 == 0:
                sample_rate = f"{track.sample_rate // 1000} kHz"
            else:
                sample_rate = f"{track.sample_rate / 1000:.1f} kHz"
            parts.append(sample_rate)
        if track.bit_rate:
            parts.append(f"{round(track.bit_rate / 1000)} kb/s")
        if track.language:
            parts.append(track.language)
        if track.source_type == "embedded" and track.is_default:
            parts.append(self._t("audio_track_default"))

        return " • ".join(parts)

    def show_audio_tracks_dialog(self):
        if self._export_busy or not self.input_path:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(
            f"{APP_NAME} — {self._t('audio_tracks_title')}"
        )
        dialog.setMinimumWidth(720)

        layout = QVBoxLayout(dialog)
        intro = QLabel(self._t("audio_tracks_intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # This dialog now owns one job only: track availability/selection.
        # Timing lives on the timeline; processing/output settings live in the
        # main Audio menu. Copies keep Cancel fully transactional.
        working_tracks = [replace(track) for track in self.audio_tracks]

        tracks_widget = QWidget(dialog)
        tracks_layout = QVBoxLayout(tracks_widget)
        tracks_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tracks_widget)

        summary = QLabel()
        layout.addWidget(summary)
        row_entries: list[tuple[AudioTrack, QCheckBox]] = []

        def clear_rows():
            while tracks_layout.count():
                item = tracks_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            row_entries.clear()

        def refresh_summary():
            selected = sum(
                1 for track in working_tracks if track.export_enabled
            )
            summary.setText(
                self._t(
                    "audio_tracks_selected",
                    selected=selected,
                    total=len(working_tracks),
                )
            )

        def on_track_toggled(track: AudioTrack, checked: bool):
            track.export_enabled = bool(checked)
            refresh_summary()

        def rebuild_rows():
            clear_rows()
            for track in working_tracks:
                row_widget = QWidget(tracks_widget)
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(0, 0, 0, 0)

                checkbox = QCheckBox(self._audio_track_label(track), row_widget)
                checkbox.setChecked(track.export_enabled)
                checkbox.toggled.connect(
                    lambda checked, item=track: on_track_toggled(item, checked)
                )
                row.addWidget(checkbox, 1)
                row_entries.append((track, checkbox))
                tracks_layout.addWidget(row_widget)
            refresh_summary()

        controls = QHBoxLayout()
        select_all_btn = QPushButton(self._t("audio_tracks_select_all"))
        select_none_btn = QPushButton(self._t("audio_tracks_select_none"))
        apply_btn = QPushButton(self._t("audio_tracks_apply"))
        cancel_btn = QPushButton(self._t("audio_tracks_cancel"))

        def set_all_checked(checked: bool):
            for track in working_tracks:
                track.export_enabled = checked
            rebuild_rows()

        select_all_btn.clicked.connect(lambda: set_all_checked(True))
        select_none_btn.clicked.connect(lambda: set_all_checked(False))
        apply_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        controls.addWidget(select_all_btn)
        controls.addWidget(select_none_btn)
        controls.addStretch(1)
        controls.addWidget(apply_btn)
        controls.addWidget(cancel_btn)
        layout.addLayout(controls)

        rebuild_rows()

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.audio_tracks = [replace(track) for track in working_tracks]
        selected = self._selected_audio_track_count()
        audio_output_enabled = (
            selected > 0
            and (self.export_main_mix or self.export_separate_audio_tracks)
        )
        self.export_audio_check.blockSignals(True)
        self.export_audio_check.setChecked(audio_output_enabled)
        self.export_audio_check.blockSignals(False)
        self._rebuild_preview_mix()

        self.statusBar().showMessage(
            self._t(
                "audio_tracks_status",
                selected=selected,
                total=len(self.audio_tracks),
            ),
            3000,
        )
        self._update_ui_state()
        self._refresh_audio_menu()

    def _update_ui_state(self):
        ready = bool(self.input_path and self.duration > 0)
        editable = ready and not self._export_busy

        # Essentials remain visible in the main workspace.
        self.play_btn.setEnabled(ready)
        self.mute_btn.setEnabled(ready)
        self.volume_slider.setEnabled(ready)
        self.split_btn.setEnabled(editable)
        self.undo_btn.setEnabled(editable and bool(self.undo_stack))
        self.audio_timeline.setEnabled(editable)

        selected_valid = (
            ready
            and 0 <= self.selected_index < len(self.segments)
            and self.segments[self.selected_index].duration > 0.001
        )
        selected_deleted = (
            selected_valid and self.segments[self.selected_index].deleted
        )
        self.segment_state_btn.setEnabled(editable and selected_valid)
        self._refresh_segment_state_button()

        streams_selected = (
            self.export_video_check.isChecked()
            or self._audio_export_enabled()
        )

        self.export_btn.setEnabled(editable and streams_selected)
        self.export_video_check.setEnabled(not self._export_busy)
        self.export_audio_check.setEnabled(not self._export_busy)
        self._refresh_audio_tracks_control()

        # Menu actions mirror the same state without duplicating behaviour.
        self.act_open.setEnabled(not self._export_busy)
        self.act_reset.setEnabled(bool(self.input_path) and not self._export_busy)
        self.act_export.setEnabled(editable and streams_selected)
        self.act_export_fragment.setEnabled(
            editable and selected_valid and streams_selected
        )
        self.act_exit.setEnabled(not self._export_busy)

        self.act_play.setEnabled(ready)
        self.act_prev_cut.setEnabled(ready)
        self.act_next_cut.setEnabled(ready)
        self.act_mute.setEnabled(ready)
        self.act_mute.setChecked(self.preview_muted)

        self.act_zoom_in.setEnabled(ready)
        self.act_zoom_out.setEnabled(ready)
        self.act_zoom_reset.setEnabled(ready)

        self.act_split.setEnabled(editable)
        self._refresh_remove_cut_state()
        self.act_undo.setEnabled(editable and bool(self.undo_stack))
        self.act_redo.setEnabled(editable and bool(self.redo_stack))
        self.act_delete.setEnabled(editable and selected_valid and not selected_deleted)
        self.act_restore.setEnabled(editable and selected_valid and selected_deleted)

        self._update_audio_timeline()
        self._refresh_audio_menu()

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
        export_audio = self._audio_export_enabled()
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
            export_main_mix=self.export_main_mix,
            export_separate_audio_tracks=self.export_separate_audio_tracks,
            audio_tracks=list(self.audio_tracks),
            source_audio_probe_ok=self.audio_probe_ok,
            ranges_override=ranges_override,
            keyframes=list(self.keyframes),
            language=self.language,
        )

        self.set_export_busy(True)
        self.export_thread = threading.Thread(
            target=self.exporter.run,
            daemon=True,
            name="VFRFastCutExport",
        )
        self.export_thread.start()

    def _audio_only_export(self) -> bool:
        return (
            self._audio_export_enabled()
            and not self.export_video_check.isChecked()
        )

    def _has_selected_external_audio(self) -> bool:
        return any(
            track.source_type == "external" and track.export_enabled
            for track in self.audio_tracks
        )

    def _default_video_output_suffix(self) -> str:
        """Choose a stream-copy-friendly default output container."""
        # External audio can use codecs that MP4/MOV cannot mux. Matroska is
        # the safest default while still keeping every stream lossless.
        if (
            self._audio_export_enabled()
            and self.export_separate_audio_tracks
            and self._has_selected_external_audio()
        ):
            return ".mkv"

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

    def _show_task_progress(
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

    def cancel_export(self):
        if not self._export_busy or not self.exporter:
            return

        self.task_progress_dialog.set_cancel_enabled(False)
        self._update_task_progress(
            "export",
            text=self._t("stopping_export"),
        )
        self.statusBar().showMessage(self._t("stopping_export"))
        self.exporter.cancel()

    def _clear_export_refs(self):
        self.exporter = None
        self.export_thread = None

    def on_export_progress(self, pct: int, text: str):
        self._update_task_progress(
            "export",
            percent=pct,
            text=text,
        )
        if self.taskbar_progress:
            self.taskbar_progress.update(pct)
        self.statusBar().showMessage(text)

    def on_export_finished(self, output: str, note: str):
        self.set_export_busy(False)
        self._clear_export_refs()
        self.statusBar().showMessage(self._t("export_finished_status"), 5000)

        dialog = QDialog(self)
        dialog.setWindowTitle(APP_NAME)
        dialog.setModal(True)
        dialog.setMinimumWidth(500)

        layout = QVBoxLayout(dialog)

        title = QLabel(self._t("export_finished_title"))
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        output_label = QLabel(self._t("output_file", output=output))
        output_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        output_label.setWordWrap(True)
        layout.addWidget(output_label)

        details = QTextBrowser(dialog)
        details.setPlainText(note)
        details.setMinimumHeight(180)
        details.setVisible(False)
        layout.addWidget(details)

        buttons = QHBoxLayout()
        details_btn = QPushButton(self._t("show_details"))
        details_btn.setCheckable(True)
        buttons.addWidget(details_btn)
        buttons.addStretch(1)

        open_folder_btn = QPushButton(self._t("open_result_folder"))
        buttons.addWidget(open_folder_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        buttons.addWidget(ok_btn)
        layout.addLayout(buttons)

        def toggle_details(checked: bool):
            details.setVisible(checked)
            details_btn.setText(
                self._t("hide_details") if checked else self._t("show_details")
            )
            if checked:
                dialog.resize(max(dialog.width(), 650), 430)
            else:
                dialog.adjustSize()

        def open_result_folder():
            folder = Path(output).resolve().parent
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            if not opened:
                self.statusBar().showMessage(
                    self._t("folder_open_failed"),
                    5000,
                )

        details_btn.toggled.connect(toggle_details)
        open_folder_btn.clicked.connect(open_result_folder)
        ok_btn.clicked.connect(dialog.accept)

        # Keep keyboard focus on the primary action when the result dialog opens.
        QTimer.singleShot(
            0,
            lambda: ok_btn.setFocus(Qt.FocusReason.OtherFocusReason),
        )
        dialog.exec()

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
        keyframe_thread = self.keyframe_scan_thread
        self._cancel_keyframe_scan()
        if keyframe_thread and keyframe_thread.is_alive():
            keyframe_thread.join(timeout=0.75)

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

        self._keyframe_progress_show_timer.stop()
        self.task_progress_dialog.finish()
        self._task_progress_owner = ""

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
