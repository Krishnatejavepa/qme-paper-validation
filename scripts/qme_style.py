# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""Shared matplotlib style for the QME validation paper.

Contract (Phase 3): 8-9 pt sans (Helvetica/Arial family), consistent math
text, single-column width 3.375 in / double 7.0 in, Okabe-Ito colorblind-safe
palette, vector PDF output, no figure titles (captions carry them), no
gridlines. All figure scripts read committed CSV/JSON artifacts only, zero
hand-typed numbers. build.sh pins SOURCE_DATE_EPOCH for deterministic PDF
metadata.
"""
import os
from pathlib import Path

import matplotlib as mpl

# Public companion-repo layout: <root>/scripts/qme_style.py
# Repo root defaults to the parent of scripts/; override with $QME_ROOT.
ROOT = Path(os.environ.get("QME_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "data"
# In this repo the na_wedge_diag CSV/JSON and the gnome_debunk summaries are
# flattened into data/, so both roots point there.
NWD = DATA
GNOME = DATA
DB = ROOT / "db" / "qme.db"
FIGDIR = ROOT / "figures"
TABDIR = ROOT / "tables"

OKABE_ITO = {
    "black": "#000000",
    "orange": "#E69F00",
    "skyblue": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
}

FAMILY_COLOR = {
    "polyanionic_phosphate": OKABE_ITO["vermillion"],
    "polyanionic_fluorophosphate": OKABE_ITO["blue"],
    "layered_oxide": OKABE_ITO["green"],
    "polyanionic_sulfate": OKABE_ITO["orange"],
}
FAMILY_LABEL = {
    "polyanionic_phosphate": "phosphate",
    "polyanionic_fluorophosphate": "fluorophosphate",
    "layered_oxide": "layered oxide",
    "polyanionic_sulfate": "sulfate",
}
GRADE_MARKER = {"A": "o", "B": "s", "C": "^"}

# Short display labels keyed by mp-id (text only; every number comes from the
# committed artifacts).
SHORT_LABEL = {
    "mp-19226": "NaFePO$_4$-m",
    "mp-1203835": "NFPP",
    "mp-562796": "NaCoPO$_4$-ABW",
    "mp-683773": r"NaCoPO$_4$-$\beta$",
    "mp-1194940": "Na$_2$FePO$_4$F",
    "mp-694937": "NVPF",
    "mp-578604": "NaCrO$_2$",
}

SINGLE_COL = 3.375  # in
DOUBLE_COL = 7.0    # in


def apply():
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 8.5,
        "axes.labelsize": 8.5,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 7.5,
        "mathtext.fontset": "dejavusans",
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "axes.grid": False,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    })
