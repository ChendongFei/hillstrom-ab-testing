# Verification

Checks run on 2026-11-15 (Python 3.12, fresh virtual environment built from
the pinned `requirements.txt`), starting from a clean checkout:

- Fresh download of the dataset passed the SHA-256 check in
  `src/download.py` (`0e589332…aece`, matching the hash pinned in
  `src/analysis.py`).
- `python -m pytest -q`: 8 passed.
- `python -m src.analysis` re-run end to end: every regenerated file under
  `reports/` (tables, JSON, results summary, both figures) is byte-identical
  to the committed version.
- Cross-checks done independently of the analysis code:
  - Group sizes, purchase counts and conversion rates recomputed from the
    raw CSV (21,306/122, 21,307/267, 21,387/189).
  - Pearson chi-square p-values for the two primary tables agree with the
    reported two-proportion z-test p-values (1.5232e-13 and 1.5711e-04).
  - Newcombe intervals recomputed by hand from Wilson score intervals match
    the reported intervals.
  - SRM statistic recomputed: chi-square 0.2025 on 2 df, p = 0.903693.
  - The SQL in `sql/metrics.sql` reproduces the Python group summary.
  - Largest absolute baseline standardized difference: 0.0137.
- Raw-data checks: 64,000 rows, 12 columns, no missing values, 6,562 rows
  repeating an earlier complete profile (kept; see `docs/methodology.md`).

Passing these checks shows the numbers are reproducible and internally
consistent. It does not verify the causal assumptions behind them (faithful
randomization, complete tracking, no interference), which rest on the
original source's description of the experiment.
