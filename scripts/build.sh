#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
# Deterministic regeneration of every figure and data table in the paper.
# All scripts read committed CSV/JSON artifacts (and qme.db read-only) only.
set -euo pipefail
cd "$(dirname "$0")"

# Use $QME_PY if set, else the active python3 on PATH (e.g. the repo venv).
PY="${QME_PY:-python3}"
export MPLBACKEND=Agg
# Pin PDF metadata timestamps so byte-identical reruns are possible.
export SOURCE_DATE_EPOCH=1780272000

"$PY" make_tables.py
"$PY" fig1_parity.py
"$PY" fig2_residuals.py
"$PY" fig3_decomposition.py
# fig4_d1_offsets.py is BRANCH A ONLY: it hard-refuses until the complete
# pre-registered D1 set is banked and the operator authorizes insertion.
# "$PY" fig4_d1_offsets.py

echo "build.sh: all figures and tables regenerated."
