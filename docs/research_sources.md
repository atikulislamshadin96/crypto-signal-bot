# Research Source Notes

This file records external evidence used only to frame research candidates. It does not constitute proof of profitability for this repository.

## Funding-rate / cross-venue mean reversion

Zhivkov, “The Two-Tiered Structure of Cryptocurrency Funding Rate Markets,” *Mathematics* 14(2), 346 (2026), DOI: https://doi.org/10.3390/math14020346. The article studies a high-frequency panel across exchanges and reports that funding-rate spreads and cross-venue fragmentation can create apparent arbitrage opportunities, while transaction costs, spread reversals and forced exits materially reduce realized profitability. Candidate implication: study funding-rate z-score/term-spread mean reversion only with venue-specific fees, latency, borrow/funding settlement and execution-cost controls. Status in this repository: research-only; not yet tested.

## Cross-sectional statistical arbitrage

Fischer, Krauss and Deinert, “Statistical Arbitrage in Cryptocurrency Markets,” *Journal of Risk and Financial Management* 12(1), 31 (2019), DOI: https://doi.org/10.3390/jrfm12010031. The paper evaluates cross-sectional prediction across a basket and explicitly discusses transaction costs and limits to arbitrage. Candidate implication: a cross-sectional relative-strength/mean-reversion module may be more defensible than a single-pair indicator alert, but it requires a point-in-time universe, borrow/short constraints, turnover controls and a fresh out-of-sample test. Status in this repository: research-only; not yet tested.

## Regime-conditional momentum

Hsieh, Huang and Liu, “State transitions and momentum effect in cryptocurrency market,” *Finance Research Letters* (2025), DOI: https://doi.org/10.1016/j.frl.2025.108356. The article reports momentum concentrated in persistent UP–UP states and largely absent in other state transitions. Candidate implication: test a regime gate that permits trend signals only when consecutive broad-market states remain positive; do not assume unconditional momentum. Status in this repository: research-only; not yet tested.

## Order-book imbalance with interpretable baselines

Wang, “Exploring Microstructural Dynamics in Cryptocurrency Limit Order Books: Better Inputs Matter More Than Stacking Another Hidden Layer,” arXiv:2506.05764v2 (2025), https://arxiv.org/html/2506.05764v2. The study emphasizes raw LOB preprocessing, multi-level imbalance features, latency and out-of-sample robustness, and reports that simpler models can match or exceed more complex models after careful feature engineering. Candidate implication: test denoised multi-level order-book imbalance with logistic regression before any deep model, using event-time leakage controls and realistic latency/slippage. Status in this repository: research-only; not yet tested.

## Research guardrails

These sources motivate hypotheses, not trading instructions. No candidate is connected to the production notification path. Each candidate must pass point-in-time feature construction, cost-aware backtest, ablation, untouched holdout, and frozen paper-trading gates before any live-capital consideration.
