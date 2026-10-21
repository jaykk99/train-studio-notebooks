#!/usr/bin/env python3
"""Validate every notebook published in this repo.

Train Studio publishes generated notebooks here for one-click "Open in
Colab". A broken notebook (bad JSON, wrong nbformat, empty code cells)
fails at open time for the user, so this script is the gate: it checks
every *.ipynb in the repo (stdlib only, no nbformat dependency) and exits
non-zero when any notebook is invalid.

Checks per notebook:
  - parses as JSON
  - nbformat == 4 (nbformat_minor is informational)
  - top-level keys: cells, metadata, nbformat, nbformat_minor
  - every cell has a valid cell_type and a source
  - code cells have outputs (list) and execution_count (int or null)
  - at least one non-empty code cell (a notebook with no code is
    almost certainly a bad export) -- warning, not failure
  - kernelspec name matches metadata.language_info.name when both exist

Usage:
    python scripts/validate_notebooks.py [--strict] [path...]

--strict turns warnings into failures. With no paths, the repo root is
scanned. An empty repo (no notebooks yet) is valid -- this repo is empty
by design until Train Studio publishes.
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID_CELL_TYPES = {"code", "markdown", "raw"}


class NotebookReport:
    def __init__(self, path):
        self.path = path
        self.errors = []
        self.warnings = []

    def ok(self, strict=False):
        return not self.errors and (not strict or not self.warnings)


def _cell_source_text(cell):
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(s) for s in source)
    return str(source)


def validate_notebook(path):
    """Return a NotebookReport for the notebook at path."""
    rep = NotebookReport(path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            nb = json.load(fh)
    except (OSError, ValueError) as exc:
        rep.errors.append(f"not parseable as JSON: {exc}")
        return rep

    if not isinstance(nb, dict):
        rep.errors.append("top level is not a JSON object")
        return rep

    for key in ("cells", "metadata", "nbformat", "nbformat_minor"):
        if key not in nb:
            rep.errors.append(f"missing required top-level key {key!r}")
    if nb.get("nbformat") != 4:
        rep.errors.append(
            f"nbformat is {nb.get('nbformat')!r}, expected 4 "
            "(Colab targets nbformat 4)"
        )
    cells = nb.get("cells")
    if not isinstance(cells, list):
        rep.errors.append("'cells' is not a list")
        return rep
    if not cells:
        rep.warnings.append("notebook has no cells")

    nonempty_code = 0
    for i, cell in enumerate(cells):
        where = f"cell {i}"
        if not isinstance(cell, dict):
            rep.errors.append(f"{where}: not an object")
            continue
        ctype = cell.get("cell_type")
        if ctype not in VALID_CELL_TYPES:
            rep.errors.append(f"{where}: bad cell_type {ctype!r}")
            continue
        if "source" not in cell:
            rep.errors.append(f"{where}: missing 'source'")
        if ctype == "code":
            if _cell_source_text(cell).strip():
                nonempty_code += 1
            if not isinstance(cell.get("outputs"), list):
                rep.errors.append(f"{where}: code cell 'outputs' is not a list")
            ec = cell.get("execution_count")
            if ec is not None and not isinstance(ec, int):
                rep.errors.append(
                    f"{where}: execution_count is {ec!r}, want int or null"
                )

    if cells and nonempty_code == 0:
        rep.warnings.append("no non-empty code cells (bad export?)")

    meta = nb.get("metadata") or {}
    ks_name = (meta.get("kernelspec") or {}).get("name")
    li_name = (meta.get("language_info") or {}).get("name")
    if ks_name and li_name and ks_name != li_name:
        rep.warnings.append(
            f"kernelspec name {ks_name!r} != language_info name {li_name!r}"
        )
    return rep


def find_notebooks(paths):
    found = []
    for base in paths:
        if os.path.isfile(base) and base.endswith(".ipynb"):
            found.append(base)
        elif os.path.isdir(base):
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d != ".git"]
                for f in sorted(files):
                    if f.endswith(".ipynb"):
                        found.append(os.path.join(root, f))
        else:
            print(f"warning: not found: {base}", file=sys.stderr)
    return sorted(set(found))


def main(argv=None):
    args = list(argv or sys.argv[1:])
    strict = False
    if "--strict" in args:
        strict = True
        args.remove("--strict")
    paths = args or [REPO_ROOT]

    notebooks = find_notebooks(paths)
    if not notebooks:
        print("no notebooks found -- nothing to validate (repo is empty by design).")
        return 0

    failed = 0
    for path in notebooks:
        rep = validate_notebook(path)
        rel = os.path.relpath(path, REPO_ROOT)
        if rel.startswith(".."):
            rel = os.path.abspath(path)
        if rep.ok(strict):
            notes = ""
            if rep.warnings:
                notes = " (warnings: " + "; ".join(rep.warnings) + ")"
            print(f"OK   {rel}{notes}")
        else:
            failed += 1
            print(f"FAIL {rel}")
            for e in rep.errors:
                print(f"       error: {e}")
            for w in rep.warnings:
                print(f"       warning: {w}")

    print(f"\n{len(notebooks) - failed}/{len(notebooks)} notebooks valid"
          + (" (strict)" if strict else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
