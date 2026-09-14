# NCA Normal Run Implementation Progress — 2026-09-14

Status: **NR0-NR6 IMPLEMENTED IN BRANCH / RUNTIME VERIFICATION PENDING**

Repository: `toootakeooot-bit/noda-chart-annotator`  
Specification baseline branch: `feature/live-draw-baseline-v1`  
Implementation branch: `feature/normal-run-v1`

## NR0 — baseline isolation

PASS.

- implementation branch created from `feature/live-draw-baseline-v1`;
- baseline branch was not modified by implementation work;
- baseline/merge-base commit: `b332b4612c52597292bd86afd8636a11a4beddc7`.

## NR1 — user-initiated Normal Run input

IMPLEMENTED, MT4 COMPILE/RUNTIME CHECK PENDING.

Added `mt4/NCA_NormalRun_Exporter.mq4`:

- one-shot MT4 Script;
- no timer;
- no continuous monitoring;
- exports only closed bars (`shift >= 1`);
- D1 / H4 / H1 / M15;
- default 600 bars per timeframe;
- writes to MT4 Common Files `noda_draw/live_input`.

## NR2 — XM symbol generalization

IMPLEMENTED, MULTI-SYMBOL RUNTIME CHECK PENDING.

- exact MT4 `Symbol()` value is canonical identity;
- no USDJPY/GOLD/US100/JP225 allowlist in the new Normal Run path;
- filesystem-safe symbol fragments are used only for file names;
- exact XM symbol remains unchanged inside state/snapshot data.

## NR3 — chronological History Rebuild

IMPLEMENTED IN PYTHON, PERFORMANCE/REFERENCE-RUN CHECK PENDING.

Added `tools/live_draw/normal_run.py`:

- every Normal Run starts from an empty lifecycle state;
- historical closed-bar prefixes are evaluated chronologically;
- existing detector/geometry/selector logic is reused;
- intervening TL generations can therefore advance lifecycle state;
- final `previous` is derived from reconstructed history rather than prior persisted Normal Run state;
- no prior state file is loaded as authority.

Important: v1 intentionally favors correctness/auditability over speed and currently performs prefix replay. Optimization is deferred until measured.

## NR4 — Safe Snapshot

IMPLEMENTED IN PYTHON, WINDOWS/MT4 FILE-LOCK CHECK PENDING.

Added validated temporary snapshot publication:

1. rebuild state;
2. write temporary snapshot;
3. validate header, symbol, timeframe, role, object-id uniqueness and numeric prices;
4. publish with `os.replace` only after PASS;
5. on failure, the previous published snapshot is left untouched.

The rebuilt JSON state is evidence/output only and is not reused as next-run `previous` authority.

## NR5 — production renderer boundary

IMPLEMENTED AS ONE-SHOT SCRIPT, MT4 COMPILE/RUNTIME CHECK PENDING.

Added `mt4/NCA_NormalRun_Renderer.mq4`:

- production ownership prefix = `NCA_DRAW__`;
- exact current `Symbol()` + current D1/H4/H1/M15 chart timeframe filter;
- two-pass check before owned-object deletion;
- only `NCA_DRAW__` objects are deleted/replaced;
- user/manual MT4 objects are untouched;
- no timer / continuous polling / trade function.

## NR6 — one-shot local launcher / symbol auto-detection

PARTIALLY IMPLEMENTED.

Added:

- `tools/run_normal.py`
  - rebuilds all four timeframes;
  - can accept exact `--symbol`;
  - if omitted, auto-detects the symbol from the most recent MT4 Normal Run export-status file;
  - publishes state/audit/snapshot only through the Normal Run path.
- `setup/run_normal.ps1`
  - runs the Python Normal Run against MT4 Common Files.
- `setup/install_normal_run_v1.ps1`
  - installs Exporter/Renderer into an explicitly supplied MT4 DataFolder `MQL4/Scripts` directory.

Still not implemented as a literal single-click end-to-end MT4 action. Current practical sequence remains:

1. run `NCA_NormalRun_Exporter` on the desired chart;
2. run `setup/run_normal.ps1`;
3. run `NCA_NormalRun_Renderer` on each desired D1/H4/H1/M15 chart.

## Tests added

`tests/selftest_normal_run.py` added for:

- symbol filename safety;
- chronological rebuild entry point;
- rebuilt-state validation;
- generation adjacency where previous exists;
- safe validated snapshot publication.

Automated execution has not yet been performed in this connector environment.

## NR7 — regression / multi-symbol runtime verification

PENDING. Requires actual MT4/Python host execution.

Required order:

1. USDJPY# — compare with existing known-good drawing;
2. GOLD#;
3. US100Cash#;
4. JP225Cash#;
5. at least one additional XM MT4 symbol to prove no initial-symbol hard-code remains.

Also verify:

- current + true previous behavior after a long gap;
- CH follows each TL generation;
- manual line protection;
- failure keeps last valid drawing;
- acceptable Normal Run elapsed time with 600 bars x 4 TF.

## NR8 — HL / direction arrow

NOT STARTED.

Deliberately deferred until TL/CH Normal Run regression passes. Boundary scope remains unchanged; this is an implementation gap only.

## Safety boundaries preserved

No implementation in this branch introduces:

- TC dependency;
- ChatGPT runtime dependency;
- NODA Engine write-back;
- order send/close/modify;
- SL/TP/lot/ticket authority.

Existing NCA detector/selection semantics were reused rather than rewritten.
