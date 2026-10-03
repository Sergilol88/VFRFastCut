# SPDX-License-Identifier: MIT
"""Robust wrapper for the 0.5.x Task Progress Dialog integration helper.

The original helper removes the legacy progress-bar reset by matching a line
that also occurs inside set_export_busy(). This wrapper narrows that one
replacement to _clear_project_state() and delegates every other transformation
to the original helper unchanged.
"""

from __future__ import annotations

import apply_task_progress_dialog as impl


_original_replace_once = impl.replace_once


def _replace_once_scoped(text: str, old: str, new: str, label: str) -> str:
    if label != "remove reset progress value":
        return _original_replace_once(text, old, new, label)

    start_marker = "    def _clear_project_state(self):\n"
    end_marker = "    def reset_project(self):\n"
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: _clear_project_state not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: reset_project boundary not found")

    block = text[start:end]
    count = block.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one match inside _clear_project_state, found {count}"
        )

    block = block.replace(old, new, 1)
    return text[:start] + block + text[end:]


def main() -> int:
    impl.replace_once = _replace_once_scoped
    return impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
