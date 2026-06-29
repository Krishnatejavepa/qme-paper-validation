# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""
Superseded. This was the v1 pre-registered D1 stub (200 Ry design, no verdict).

The D1 offset audit now has a verdict, computed at the cutoff-converged 70/560 Ry
energies. The single source of truth is:

    scripts/d1_offset_verdict_70_560.py  ->  data/d1_corrected_offsets.json

Run that instead:

    QME_ROOT="$PWD" python scripts/d1_offset_verdict_70_560.py
"""
import sys

print(__doc__.strip())
sys.exit(0)
