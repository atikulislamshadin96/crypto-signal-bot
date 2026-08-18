# STATUS_TODAY

**As of:** 2026-08-18T11:36:50Z
**Repository:** [atikulislamshadin96/crypto-signal-bot](https://github.com/atikulislamshadin96/crypto-signal-bot)
**Paper version:** `v1.0-paper`
**Mode:** Paper-trade only; no order placement

> **PAPER-TRADE ONLY — NOT VALIDATED — DO NOT USE REAL CAPITAL.** No strategy in this repository is currently validated for live capital.

## 1. Paper-trading instrumentation

| Check | Status | Evidence / honest caveat |
|---|---|---|
| Frozen paper version configured | **PASS** | `config.yaml` sets `paper_trading.enabled: true` and version `v1.0-paper`; the version is tagged in Git. |
| Signal logging path wired | **PASS** | Runner writes timestamped signal rows to `data/signals.jsonl`. |
| Paper disclaimer on every signal | **PASS** | Formatter/runner/config carry the mandatory paper-only disclaimer. |
| Automatic TP/SL/timeout tracker | **PASS** | Runner evaluates subsequent closed candles and records `TP_HIT`, `SL_HIT` or `TIMEOUT`. |
| Daily/weekly summary generation | **PASS** | Summary persistence is wired for daily and weekly paper-trade summaries. |
| First signal timestamp | **NOT AVAILABLE YET** | No `data/signals.jsonl` exists in this checkout, so no signal has been observed or timestamped yet. This is not treated as a successful forward test. |
| Observed forward-test sample | **0** | Instrumentation is enabled, but the repository has not yet accumulated a runtime sample. |

## 2. Public pre-publish checklist

| Check | Status | Evidence |
|---|---|---|
| Secrets scan | **PASS** | Current tree and Git history contain no tracked `.env`, key, certificate, credential or webhook-secret file; no real token was found by the repository scan. |
| `config.yaml` hygiene | **PASS** | Contains generic placeholder/risk values only; no personal account identifier, bot token or webhook URL is stored. |
| `.env` / local secret files | **PASS** | No tracked local secret file is present in the current tree or scanned history. |
| README disclaimer at top | **PASS** | README begins with paper-trade-only, not-validated and no-real-capital warning, plus financial-advice disclaimer. |
| Explicit license | **PASS** | `LICENSE` contains the MIT License. |
| Repository public | **PASS** | GitHub visibility is `PUBLIC` after the checklist passed. |

## 3. Feature archive collection

| Check | Status | Evidence / gap |
|---|---|---|
| Append-only archive code | **PASS** | Each scan can append a timestamped context snapshot to `data/feature_archive.jsonl`. |
| Required context fields | **PASS** | Funding, open interest, order-book metrics, BTC dominance and stablecoin-supply context are captured when available. |
| Missing/error provenance | **PASS** | Provider availability, endpoint error and missing values are persisted without fabricated imputation. |
| Collection enabled | **PASS — code/config enabled** | The archive path is wired and paper mode is active. |
| Archive rows collected so far | **NOT AVAILABLE YET** | No `data/feature_archive.jsonl` exists in this checkout; the first scheduled runtime cycle has not been observed here. Historical backfill is not claimed. |

## 4. Advanced-strategy research candidates

All candidates below are **research phase only**, are not imported by the production runner, and have **no backtest numbers yet**. Their status is explicitly **not yet tested**.

| Candidate module | Research logic | Production status | Validation status |
|---|---|---|---|
| Funding-rate mean reversion | Test whether extreme funding or cross-venue funding spreads normalize after costs. | Not connected | **Not yet tested** |
| Denoised multi-level order-flow imbalance | Test whether persistent depth imbalance predicts short-horizon movement after latency and slippage. | Not connected | **Not yet tested** |
| Regime-conditional momentum | Allow momentum only after pre-defined persistent broad-market UP states. | Not connected | **Not yet tested** |
| Cross-exchange spread / arbitrage-adjacent signal | Test synchronized venue spreads after fees, latency, inventory and execution constraints. | Not connected | **Not yet tested** |

The candidate feature generators are in `src/signalbot/research_candidates.py`; supporting rationale and sources are in `docs/research_candidates.md` and `docs/research_sources.md`. No candidate sends notifications or changes the production signal path.

## Bottom line

Paper-trading instrumentation is **implemented and enabled**, but the first signal, archive rows and forward-test sample are **not yet observed** in this checkout. The repository is public only after the checklist passed. The research candidates are hypotheses, not validated strategies. No live-capital use is justified.
