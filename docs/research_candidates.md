# Advanced Strategy Research Candidates

> **Research phase only.** These candidates are not connected to the production scanner or Telegram/Discord notification pipeline. All candidates are **not yet tested** in this repository and must not be described as advanced, high-accuracy, or live-capital ready.

| Candidate | Why it might work | Main trap/risk | Required evidence before promotion |
|---|---|---|---|
| Funding-rate mean reversion | Extreme funding or cross-venue funding spreads may normalize as leveraged positioning rebalances. | Funding payments, fees, borrow, spread reversal and forced exits can overwhelm the apparent edge. | Point-in-time funding panel, venue-specific cost model, ablation, untouched holdout and frozen paper phase. |
| Denoised multi-level order-flow imbalance | Persistent depth imbalance may proxy short-horizon supply-demand pressure. | Flicker quotes, spoofing, latency, adverse selection and snapshot leakage can create false edge. | Event-time archive, latency/slippage simulation, denoising comparison, out-of-sample test and robustness by venue. |
| Regime-conditional momentum | Momentum may be stronger in persistent broad-market UP states than in transitions or DOWN states. | Regime definition can be optimized after seeing outcomes; unconditional carry-through is not justified. | Pre-registered regime definition, cross-asset panel, regime-conditioned ablation and final holdout. |
| Cross-exchange spread / arbitrage-adjacent signal | Temporary synchronized-venue price or funding spreads may mean-revert. | Transfer/inventory risk, venue outages, fees, latency, borrow and imperfect synchronization. | Synchronized multi-venue archive, executable spread after all costs, inventory constraints and paper execution. |

## Implementation status

Candidate feature generators live in `src/signalbot/research_candidates.py`. The module is intentionally not imported by `runner.py`, `strategy.py`, or the notification path. It only produces lagged research features and a registry that marks every candidate `production_enabled: false` and `status: not yet tested`.

External rationale sources are recorded in [`research_sources.md`](research_sources.md). Their findings motivate hypotheses only; they are not evidence that any candidate is profitable in this repository.

## Promotion gate

A candidate can be considered for any production experiment only after point-in-time data construction, cost-aware backtesting, feature ablation, multiple-testing control, an untouched holdout, and a frozen paper-trading period. Until then, all candidate outputs remain research artifacts and must not generate notifications.
