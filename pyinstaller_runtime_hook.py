# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sergilol

# Early runtime configuration for packaged VFR FastCut builds.

import os

# Qt Multimedia hardware texture conversion can produce corrupted/green
# preview frames on some Windows GPU/driver combinations. This must be set
# before PySide6/Qt runtime hooks initialize Qt Multimedia.
os.environ["QT_DISABLE_HW_TEXTURES_CONVERSION"] = "1"
