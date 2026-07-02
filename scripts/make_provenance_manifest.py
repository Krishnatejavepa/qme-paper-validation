#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""Provenance manifest generator and checker for verdict artifacts.

For every verdict artifact this repo publishes, the manifest records:
  - sha256 of the artifact itself,
  - sha256 of the generator script and of every committed input it reads
    (including the vendored gate module, since the verdict depends on it),
  - the pre-registration the artifact answers to,
  - the declared execution environment (the facts fixed by the study), and
  - the captured environment (what actually ran when the manifest was made).

Write mode (default) writes <artifact>.manifest.json next to the artifact.
Check mode (--check) re-hashes every referenced file against the committed
manifest and exits nonzero on any mismatch; environment differences are
reported as information, never as failure (a stranger's Python patch version
does not invalidate a file-hash check).

Usage:
  python scripts/make_provenance_manifest.py            # write manifest(s)
  python scripts/make_provenance_manifest.py --check    # verify manifest(s)

Determinism: output is a pure function of the referenced file contents plus
the declared environment. A timestamp is included only when SOURCE_DATE_EPOCH
is set (the same convention build.sh uses), so byte-identical reruns are the
default, not a special mode.
"""
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("QME_ROOT", Path(__file__).resolve().parents[1]))

# Registry: one entry per verdict artifact this repo publishes.
REGISTRY = {
    "data/d1_corrected_offsets.json": {
        "generator": "scripts/d1_offset_verdict_70_560.py",
        "inputs": [
            "data/results.json",
            "scripts/d1_audit.py",
        ],
        "preregistration": {
            "prereg_id": "d1_offset_audit_2026-06-10",
            "canonical_document": "prereg/D1_PREREGISTRATION_2026-06-10.md",
            "note": "Machine-readable instance ships with QME Validation Protocol v1.0 "
                    "(protocol/instances/prereg_d1_offset_audit_2026-06-10.json).",
        },
        "declared_environment": {
            "dft_code": "Quantum ESPRESSO 7.3.1 (pw.x, local Mac Mini M4)",
            "conda_env": "qme_gauntlet",
            "hubbard": "HUBBARD {ortho-atomic}, U Fe-3d 5.30 / Mn-3d 3.90 / Co-3d 3.40 eV",
            "cutoffs": "ecutwfc 70 Ry / ecutrho 560 Ry (deviation from the registered "
                       "50/200 Ry, disclosed in the artifact)",
            "mace_oracle": "MACE Oracle v3.0 (MACE-MP-0 backbone); NOT used by this "
                           "artifact, declared for stack completeness",
        },
    },
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def captured_environment() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def build_manifest(artifact_rel: str, spec: dict) -> dict:
    artifact = ROOT / artifact_rel
    files = {artifact_rel: sha256_of(artifact)}
    files[spec["generator"]] = sha256_of(ROOT / spec["generator"])
    for rel in spec["inputs"]:
        files[rel] = sha256_of(ROOT / rel)
    prereg_doc = spec["preregistration"]["canonical_document"]
    if (ROOT / prereg_doc).exists():
        files[prereg_doc] = sha256_of(ROOT / prereg_doc)

    manifest = {
        "manifest_for": artifact_rel,
        "generator": spec["generator"],
        "regeneration_command": f"QME_ROOT=$PWD python {spec['generator']}",
        "sha256": dict(sorted(files.items())),
        "preregistration": spec["preregistration"],
        "declared_environment": spec["declared_environment"],
        "captured_environment": captured_environment(),
    }
    sde = os.environ.get("SOURCE_DATE_EPOCH")
    if sde:
        manifest["generated_utc"] = datetime.fromtimestamp(
            int(sde), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return manifest


def manifest_path(artifact_rel: str) -> Path:
    p = ROOT / artifact_rel
    return p.with_suffix(p.suffix + ".manifest.json")


def write_all() -> int:
    for artifact_rel, spec in REGISTRY.items():
        out = manifest_path(artifact_rel)
        out.write_text(json.dumps(build_manifest(artifact_rel, spec), indent=2) + "\n")
        print(f"wrote {out.relative_to(ROOT)}")
    return 0


def check_all() -> int:
    bad = 0
    for artifact_rel, spec in REGISTRY.items():
        mpath = manifest_path(artifact_rel)
        if not mpath.exists():
            print(f"FAIL {artifact_rel}: manifest missing ({mpath.relative_to(ROOT)})")
            bad += 1
            continue
        committed = json.loads(mpath.read_text())
        ok = True
        for rel, want in committed.get("sha256", {}).items():
            f = ROOT / rel
            if not f.exists():
                print(f"  MISSING {rel}")
                ok = False
                continue
            got = sha256_of(f)
            if got != want:
                print(f"  HASH MISMATCH {rel}")
                print(f"    manifest: {want}")
                print(f"    on disk : {got}")
                ok = False
        env_now = captured_environment()
        env_then = committed.get("captured_environment", {})
        if env_now != env_then:
            print(f"  info: environment differs (manifest: {env_then}, "
                  f"now: {env_now}); not a failure")
        print(f"{'PASS' if ok else 'FAIL'} {artifact_rel}: "
              f"{len(committed.get('sha256', {}))} file hash(es) checked")
        bad += 0 if ok else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(check_all() if "--check" in sys.argv[1:] else write_all())
