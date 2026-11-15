# Verification

Executed 2026-11-15 on Python 3.12.

- 8 automated tests passed.
- Fresh Kaggle download passed fixed SHA-256 validation.
- Full analysis rerun produced byte-identical report outputs.
- Binomial z-test cross-checked against independent Pearson chi-square calculation in tests.
- Generated SQL metrics and Python summaries inspected.
- Successful execution and tests do not establish the causal assumptions or data provenance beyond the cited source and checksum.

## Independent verification (2026-11-15)

The repository was re-verified independently of the original run, starting from
commit `226e5d5` in a fresh virtual environment built from the pinned
`requirements.txt` (Python 3.12.3):

- Fresh dataset download passed the fixed SHA-256 check
  (`0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece`).
- `python -m pytest -q`: 8 passed.
- Full rerun of `python -m src.analysis`: every regenerated file under
  `reports/` (CSV, JSON, Markdown and both PNG figures) is byte-identical to
  the committed version.
- Independent recomputation with a separate script (not `src/` code):
  - Group sizes, purchase counts and conversion rates match
    (21,306/122/0.5726%; 21,307/267/1.2531%; 21,387/189/0.8837%).
  - Pearson chi-square p-values equal the reported two-proportion z-test
    p-values (Mens 1.5232e-13; Womens 1.5711e-04).
  - Hand-computed Newcombe 95% intervals match the reported intervals
    ([0.501, 0.864] and [0.150, 0.475] percentage points).
  - SRM chi-square = 0.2025 on 2 df, p = 0.903693, as reported.
  - Welch t-test p-values for spend match the exploratory revenue table
    (Mens 1.1638e-07; Womens 1.1294e-03); bootstrap intervals are consistent.
  - SQL metrics (`sql/metrics.sql`) reproduce the Python group summary to
    full printed precision.
  - Maximum absolute baseline standardized difference is 0.0137
    (`zip_code_Rural`, Mens vs control).
- Data checks confirmed directly on the raw CSV: 64,000 rows, 12 columns,
  0 missing values, 6,562 rows repeating an earlier complete profile
  (retained; no customer ID exists to prove they are the same person).

This verification covers numerical reproducibility and internal consistency.
It does not independently establish the causal assumptions listed in
`docs/methodology.md` (faithful randomization, complete tracking, no
interference), which rest on the original source's description.
