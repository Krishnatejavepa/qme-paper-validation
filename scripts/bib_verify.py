# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Krishna Teja Vepa
"""PROVENANCE SCRIPT, NOT part of the offline reproduce set: requires network
access (queries Crossref and the arXiv API). Regenerates refs.bib from fetched
records. The committed refs.bib / paper.bbl are the shipped bibliography.

Phase-4 bibliography verification (zero tolerance).

For every citation key: resolve the DOI on Crossref (or arXiv for
preprint-only entries), field-match the fetched record against the expected
title keywords / first author / year, and emit (a) bib_audit_cache.json with
the raw fetched metadata and per-field verdicts, and (b) refs.gen.bib whose
entries are constructed FROM THE FETCHED RECORDS, no field is typed from
memory. Entries that fail to resolve or to match are emitted to the audit
log only and excluded from refs.gen.bib (cut-or-replace per contract).

Run:  python3 bib_verify.py
"""
import html
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "QME-paper-bib-audit/1.0 (mailto:ops@example.invalid)"}

# key -> (doi, expected-title-keywords, expected-first-author-family,
#         expected-year, why-cited)
ENTRIES = {
    "merchant2023": ("10.1038/s41586-023-06735-9",
                     ["scaling deep learning", "materials"],
                     "Merchant", 2023, "GNoME release (pinned in gnome_debunk provenance)"),
    "szymanski2023": ("10.1038/s41586-023-06734-w",
                      ["autonomous", "laboratory"],
                      "Szymanski", 2023, "A-lab autonomous synthesis claims"),
    "cheetham2024": ("10.1021/acs.chemmater.4c00643",
                     ["artificial intelligence", "driving"],
                     "Cheetham", 2024, "GNoME critique (credible/new/useful)"),
    "leeman2024": ("10.1103/PRXEnergy.3.011002",
                   ["challenges", "high-throughput"],
                   "Leeman", 2024, "A-lab/GNoME synthesis re-examination"),
    "nosek2018": ("10.1073/pnas.1708274114",
                  ["preregistration revolution"],
                  "Nosek", 2018, "pre-registration methodology"),
    "aydinol1997": ("10.1103/PhysRevB.56.1354",
                    ["ab initio", "lithium intercalation"],
                    "Aydinol", 1997, "DFT voltage formalism"),
    "wang2006": ("10.1103/PhysRevB.73.195107",
                 ["oxidation energies", "gga"],
                 "Wang", 2006, "GGA+U voltage convention / FM standard"),
    "jain2013": ("10.1063/1.4812323",
                 ["materials project"],
                 "Jain", 2013, "Materials Project"),
    "davies2019": ("10.21105/joss.01361",
                   ["smact"],
                   "Davies", 2019, "SMACT screening"),
    "giannozzi2009": ("10.1088/0953-8984/21/39/395502",
                      ["quantum espresso"],
                      "Giannozzi", 2009, "Quantum ESPRESSO"),
    "giannozzi2017": ("10.1088/1361-648x/aa8f79",
                      ["advanced capabilities", "quantum espresso"],
                      "Giannozzi", 2017, "QE advanced capabilities"),
    "monkhorst1976": ("10.1103/PhysRevB.13.5188",
                      ["special points", "brillouin"],
                      "Monkhorst", 1976, "k-point sampling"),
    "dudarev1998": ("10.1103/PhysRevB.57.1505",
                    ["electron-energy-loss", "structural stability"],
                    "Dudarev", 1998, "DFT+U (Dudarev) formulation"),
    "timrov2022": ("10.1016/j.cpc.2022.108455",
                   ["hp", "hubbard"],
                   "Timrov", 2022, "linear-response Hubbard U code"),
    "garrity2014": ("10.1016/j.commatsci.2013.08.053",
                    ["pseudopotentials", "high-throughput"],
                    "Garrity", 2014, "GBRV pseudopotential library"),
    "dalcorso2014": ("10.1016/j.commatsci.2014.07.043",
                     ["pseudopotentials", "periodic table"],
                     "Dal Corso", 2014, "PSlibrary pseudopotentials"),
    "chen2022": ("10.1038/s43588-022-00349-3",
                 ["universal graph deep learning", "interatomic"],
                 "Chen", 2022, "M3GNet relaxer"),
    "efron1979": ("10.1214/aos/1176344552",
                  ["bootstrap"],
                  "Efron", 1979, "bootstrap CIs"),
    "padhi1997": ("10.1149/1.1837571",
                  ["phospho-olivines", "positive-electrode"],
                  "Padhi", 1997, "LiFePO4 3.45 V reference (pre-registered)"),
    "nishimura2010": ("10.1021/ja106297a",
                      ["pyrophosphate", "3.5"],
                      "Nishimura", 2010, "Li2FeP2O7 3.5 V reference (pre-registered)"),
    "thackeray1983": ("10.1016/0025-5408(83)90138-1",
                      ["lithium insertion", "manganese"],
                      "Thackeray", 1983, "LiMn2O4 spinel reference (pre-registered)"),
    "ohzuku1990": ("10.1149/1.2086552",
                   ["electrochemistry of manganese dioxide", "lithium"],
                   "Ohzuku", 1990, "LiMn2O4/lambda-MnO2 4.05 V (pre-registered)"),
    "rodriguez1998": ("10.1103/PhysRevLett.81.4660",
                      ["electronic crystallization", "lithium"],
                      "Rodr", 1998, "LiMn2O4 low-T charge order (stretch caveat)"),
    "kim2015": ("10.1039/C4EE03215B",
                ["maricite", "nafepo4"],
                "Kim", 2015, "maricite NaFePO4 amorphization (curated set)"),
    "kim2012": ("10.1021/ja3038646",
                ["mixed-polyanion", "sodium"],
                "Kim", 2012, "NFPP 3.2 V (curated set)"),
    "chiring2021": ("10.1016/j.jssc.2020.121766",
                    ["nacopo4"],
                    "Chiring", 2021, "NaCoPO4 polymorphs 4.3/4.5 V (curated set)"),
    "kawabe2011": ("10.1016/j.elecom.2011.08.038",
                   ["na2fepo4f"],
                   "Kawabe", 2011, "Na2FePO4F plateaus (curated set)"),
    "yan2019": ("10.1038/s41467-019-08359-y",
                ["na3v2(po4)2f3"],
                "Yan", 2019, "NVPF plateaus (curated set; CSV note misattributes first author as Bianchini, cited as resolved)"),
    "bo2016": ("10.1021/acs.chemmater.5b04626",
               ["cro2", "desodiated"],
               "Bo", 2016, "NaCrO2 phase windows (curated set)"),
    "barpanda2012": ("10.1016/j.elecom.2012.08.028",
                     ["sodium iron pyrophosphate"],
                     "Barpanda", 2012, "Na2FeP2O7 ~3 V (curated set)"),
    "barpanda2014": ("10.1038/ncomms5358",
                     ["3.8 v", "earth-abundant"],
                     "Barpanda", 2014, "alluaudite sulfate 3.8 V (curated set)"),
    "mohsin2023": ("10.1155/2023/6054452",
                   ["maricite"],
                   "Mohsin", 2023, "NaMnPO4 drop-log evidence"),
    "barker2003": ("10.1149/1.1523691",
                   ["sodium-ion cell", "fluorophosphate"],
                   "Barker", 2003, "NaVPO4F drop-log evidence (full-cell V)"),
    "tripathi2010": ("10.1002/anie.201003743",
                     ["tavorite", "nafeso4f"],
                     "Tripathi", 2010, "NaFeSO4F drop-log evidence"),
    "komaba2012": ("10.1021/ic300357d",
                   ["reversible electrode reaction"],
                   "Komaba", 2012, "NaNi0.5Mn0.5O2 drop-log evidence"),
    "ellis2007": ("10.1038/nmat2007",
                  ["multifunctional", "3.5 v"],
                  "Ellis", 2007, "Na2FePO4F Li-cell 3.5 V (superseded for Na)"),
    "nfp2016": ("10.1021/acssuschemeng.6b01536",
                ["na3fe2(po4)3"],
                None, 2016, "Na3Fe2(PO4)3 ~2.5 V Fe3+/Fe2+ couple (ledger note)"),
    "jian2012": ("10.1016/j.elecom.2011.11.009",
                 ["na3v2(po4)3"],
                 "Jian", 2012, "Na3V2(PO4)3 ~3.4 V plateau (touchpoint context)"),
}

ARXIV_ENTRIES = {
    "batatia2022": ("2206.07697", ["mace", "higher order equivariant"],
                    "MACE architecture"),
    "batatia2024": ("2401.00096", ["foundation model", "atomistic"],
                    "MACE-MP-0 foundation model"),
}


def strip_html(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r"<sub>(.*?)</sub>", r"$_{\1}$", s)
    s = re.sub(r"<sup>(.*?)</sup>", r"$^{\1}$", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\u2010", "-").replace("\u2011", "-")
    s = re.sub(r"\}\$(?=[A-Za-z])", "}$ ", s)  # space after subscript runs
    return re.sub(r"\s+", " ", s).strip()


def squash(s: str) -> str:
    """Lowercase alphanumerics only: robust to subscripts/markup in titles."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tex_escape(s: str) -> str:
    for a, b in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"),
                 ("é", r"\'e"), ("í", r"\'i"), ("ü", r"\"u"),
                 ("ö", r"\"o"), ("á", r"\'a"), ("è", r"\`e"),
                 ("ç", r"\c{c}"), ("ă", r"\u{a}"), ("š", r"\v{s}"),
                 ("ž", r"\v{z}"), ("č", r"\v{c}"), ("ć", r"\'c"),
                 ("ñ", r"\~n"), ("ø", r"\o{}"), ("å", r"\aa{}"),
                 ("ş", r"\c{s}"), ("ó", r"\'o"), ("ú", r"\'u")]:
        s = s.replace(a, b)
    return s


def fetch_crossref(doi: str):
    url = f"https://api.crossref.org/works/{doi}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)["message"]


def fetch_arxiv(aid: str):
    url = f"https://export.arxiv.org/api/query?id_list={aid}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        root = ET.fromstring(r.read())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    e = root.find("a:entry", ns)
    title = re.sub(r"\s+", " ", e.find("a:title", ns).text).strip()
    authors = [a.find("a:name", ns).text for a in e.findall("a:author", ns)]
    year = int(e.find("a:published", ns).text[:4])
    return {"title": title, "authors": authors, "year": year}


def main():
    cache, bib, failures = {}, [], []

    for key, (doi, kws, fam, year, why) in ENTRIES.items():
        try:
            m = fetch_crossref(doi)
        except Exception as exc:
            cache[key] = {"doi": doi, "resolved": False, "error": str(exc)}
            failures.append((key, doi, f"UNRESOLVED: {exc}"))
            continue
        title = strip_html(m.get("title", [""])[0])
        container = strip_html((m.get("container-title") or [""])[0])
        issued = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
        authors = m.get("author", [])
        first_fam = authors[0].get("family", "") if authors else ""
        tl = title.lower()
        kw_ok = all((k.lower() in tl) or (squash(k) in squash(title))
                    for k in kws)
        fam_ok = (fam is None) or (fam.lower() in first_fam.lower())
        yr_ok = (issued == year) or (issued in (year - 1, year + 1))
        verdict = "MATCH" if (kw_ok and fam_ok and yr_ok) else "MISMATCH"
        cache[key] = {
            "doi": doi, "resolved": True, "title": title,
            "container": container, "year": issued,
            "first_author": first_fam, "n_authors": len(authors),
            "kw_ok": kw_ok, "author_ok": fam_ok, "year_ok": yr_ok,
            "verdict": verdict, "why_cited": why,
        }
        if verdict != "MATCH":
            failures.append((key, doi,
                             f"MISMATCH kw={kw_ok} author={fam_ok} "
                             f"year={yr_ok} title={title[:70]!r}"))
            continue
        if len(authors) > 20:
            names = " and ".join(
                f"{a.get('family','')}, {a.get('given','')}"
                for a in authors[:10]) + " and others"
        else:
            names = " and ".join(
                f"{a.get('family','')}, {a.get('given','')}" for a in authors)
        fields = [
            f"  author = {{{tex_escape(names)}}}",
            f"  title = {{{{{tex_escape(title)}}}}}",
            f"  journal = {{{tex_escape(container)}}}",
            f"  year = {{{issued}}}",
        ]
        if m.get("volume"):
            fields.append(f"  volume = {{{m['volume']}}}")
        if m.get("page"):
            fields.append(f"  pages = {{{m['page'].replace('-', '--')}}}")
        fields.append(f"  doi = {{{doi}}}")
        bib.append(f"@article{{{key},\n" + ",\n".join(fields) + "\n}\n")
        time.sleep(0.4)

    for key, (aid, kws, why) in ARXIV_ENTRIES.items():
        try:
            m = fetch_arxiv(aid)
        except Exception as exc:
            cache[key] = {"arxiv": aid, "resolved": False, "error": str(exc)}
            failures.append((key, aid, f"UNRESOLVED: {exc}"))
            continue
        kw_ok = all(k.lower() in m["title"].lower() for k in kws)
        cache[key] = {"arxiv": aid, "resolved": True, **m,
                      "kw_ok": kw_ok,
                      "verdict": "MATCH" if kw_ok else "MISMATCH",
                      "why_cited": why}
        if not kw_ok:
            failures.append((key, aid, f"MISMATCH title={m['title'][:70]!r}"))
            continue
        if len(m["authors"]) > 20:
            names = " and ".join(m["authors"][:10]) + " and others"
        else:
            names = " and ".join(m["authors"])
        bib.append(
            f"@misc{{{key},\n  author = {{{tex_escape(names)}}},\n"
            f"  title = {{{{{tex_escape(m['title'])}}}}},\n"
            f"  year = {{{m['year']}}},\n  eprint = {{{aid}}},\n"
            f"  archivePrefix = {{arXiv}}\n}}\n")

    (HERE / "bib_audit_cache.json").write_text(json.dumps(cache, indent=1))
    (HERE / "refs.gen.bib").write_text("\n".join(bib))
    print(f"resolved+matched: {len(bib)} / {len(ENTRIES) + len(ARXIV_ENTRIES)}")
    for k, d, msg in failures:
        print(f"  FAIL {k} ({d}): {msg}")


if __name__ == "__main__":
    main()
