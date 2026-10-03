# SPDX-License-Identifier: MIT
"""Fix stale main-window references after Task Progress Dialog integration.

Run after apply_task_progress_dialog_v2.py. The Task Progress refactor removes
legacy MainWindow widgets (cancel_export_btn/export_stack/progress), so language
refresh must address the dialog's cancel button instead.
"""

from __future__ import annotations

import re
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "vfr_fastcut.py"
    if not target.is_file():
        raise RuntimeError(f"vfr_fastcut.py not found at {target}")

    text = target.read_text(encoding="utf-8")
    if "class TaskProgressDialog(QDialog):" not in text:
        raise RuntimeError(
            "Task Progress Dialog is not integrated yet; run "
            "apply_task_progress_dialog_v2.py first"
        )

    old = '        self.cancel_export_btn.setText(self._t("cancel_export"))\n'
    new = '        self.task_progress_dialog.cancel_btn.setText(self._t("cancel_export"))\n'

    if old in text:
        if text.count(old) != 1:
            raise RuntimeError(
                "stale cancel_export_btn language reference: expected one match, "
                f"found {text.count(old)}"
            )
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError(
            "Could not find either the old or fixed cancel-button language reference"
        )

    # Guard against any other MainWindow references to widgets removed by #8.
    forbidden = {
        "self.cancel_export_btn": re.compile(r"\bself\.cancel_export_btn\b"),
        "self.export_stack": re.compile(r"\bself\.export_stack\b"),
        "self.progress": re.compile(r"\bself\.progress\b"),
    }
    problems: list[str] = []
    for label, pattern in forbidden.items():
        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                problems.append(f"line {line_no}: {label}: {line.strip()}")

    if problems:
        joined = "\n".join(problems)
        raise RuntimeError(
            "Legacy task-progress widget references remain after the fix:\n" + joined
        )

    target.write_text(text, encoding="utf-8")
    print("Fixed stale Task Progress Dialog widget references in vfr_fastcut.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
