# train-studio-notebooks
Notebooks published by Train Studio for one-click Open in Colab.

This repo is **empty by design** — Train Studio generates and publishes
notebooks here. Nothing is committed by hand except publishing tooling.

## Publishing checklist

1. Export the notebook as nbformat 4 (`.ipynb`).
2. Make sure the first markdown cell contains the Open in Colab badge:
   `https://colab.research.google.com/github/jaykk99/train-studio-notebooks/blob/main/<notebook>.ipynb`
3. Run the validator before pushing:
   ```bash
   python3 scripts/validate_notebooks.py --strict .
   ```
   CI runs the same check on every push. A notebook that fails validation
   (bad JSON, wrong nbformat, missing cell sources, empty code cells) will
   break at open time for the user — don't ship it.

## Validator

`scripts/validate_notebooks.py` (stdlib only, no dependencies) checks every
`*.ipynb` in the repo: JSON parses, nbformat 4, required top-level keys,
valid cell types, code-cell `outputs`/`execution_count` shapes, at least one
non-empty code cell, and kernelspec/language consistency. Exit code is
non-zero when any notebook is invalid; `--strict` also fails on warnings.
