# Advanced Architecture and Deep Validation Report

**Repository:** `atikulislamshadin96/crypto-signal-bot`
**Report date:** 2026-08-18 UTC
**Author:** Manus AI
**Purpose:** নতুন multi-layer crypto-signal redesign-এর implementation coverage, data feasibility, runtime behavior, statistical validity এবং remaining production gates-এর honest assessment।

## Executive conclusion

The redesign is now implemented as a **context-gated research architecture**, not as a proven trading system. It adds current derivatives, order-book and slow macro context; records source provenance and missingness; exposes bounded explainable feature contributions; includes a local logistic-model trainer and chronological ablation utility; and refuses to treat a current provider snapshot as historical predictive evidence.

The previous indicator-only baseline remains weak. Its latest 90-day aggregate validation contained **238 out-of-sample trades, 73 wins, 164 losses and −18.0R net** from the existing frozen-parameter harness. The redesign has **not** yet produced a point-in-time historical orthogonal-feature panel, so it has no defensible new OOS win-rate or expectancy claim. A live smoke test confirmed that several current providers respond, but that only establishes operational availability at one timestamp; it does not establish predictive power.

> **Current verdict:** The redesigned system is suitable for **paper-trading instrumentation and research data collection only**. It is **not trade-worthy for live capital**. The previous verdict has not improved because the new context layers have not yet passed a friction-aware, time-ordered holdout test.

## Section A — Data-source feasibility and cadence

### What was tested

The feasibility audit checked whether each proposed layer has a public or affordable runtime path, whether its cadence is compatible with a 15-minute GitHub Actions scan, whether endpoint failure can be represented as missing data, and whether the source has an honest point-in-time historical path. Official provider documentation was used for endpoint and access claims [1] [2] [3] [4].

### Result

| Layer | Runtime implementation | 15-minute suitability | Historical OOS suitability | Result |
|---|---|---|---|---|
| Binance Futures funding/OI | Implemented in `context.py` with nullable fields and error capture | Funding/OI snapshot is operationally suitable | No complete point-in-time panel bundled | **Current context only** |
| Exchange order book | Implemented through the configured CCXT exchange | A bounded snapshot is feasible | No historical L2 archive | **Current microstructure only** |
| CoinGecko global context | Implemented as slow macro context | Suitable as low-frequency context, not precise 15m alpha | Free/demo historical cadence is not a clean 15m panel | **Macro context only** |
| DefiLlama stablecoin supply | Implemented as aggregate supply and 7-day change | Slow context only | Not wallet-level flow or event attribution | **Aggregate context only** |
| FRED/DXY | Optional and disabled by default | Daily release cadence requires careful alignment | Historical series exists, but release-time alignment is untested | **Not production-enabled** |
| Wallet netflow / whale labels | Not implemented | Provider/indexing burden is material | No defensible free default panel | **Explicitly out of scope** |
| Production ML model | Research trainer implemented; no trained artifact shipped | Runtime scoring is inexpensive | Requires real labelled, point-in-time data | **Research-only** |

### Gap

The system has provider access, but provider access is not the same as a validated research dataset. In particular, no historical funding/OI/order-book feature archive is currently stored with point-in-time timestamps, symbol mapping, endpoint status and publication-time semantics. Until that archive exists, the new orthogonal layers cannot be assigned an OOS edge.

## Section B — Derivatives context

### What was tested

The redesigned runtime requested current Binance Futures funding and open interest for `BTC/USDT`. It also attempted open-interest history and global long/short ratio endpoints. Each request was treated as nullable and endpoint errors were retained rather than converted into neutral or bullish values.

### Result

The 2026-08-18 smoke run returned:

| Field | Measured result | Interpretation |
|---|---:|---|
| Funding rate | `0.00007045` | Current snapshot available; not a historical signal result |
| Open interest | `106119.42` | Current snapshot available; unit/contract semantics remain exchange-specific |
| Open-interest history | HTTP error | Historical derivative replay unavailable in this run |
| Global long/short ratio | JSON decoding error | Endpoint availability is not reliable enough to treat as mandatory |
| Missingness handling | Passed | Errors remain visible under `errors`; no fabricated values inserted |

### Gap

The implementation can **observe** current derivatives context, but cannot yet determine whether a funding/OI configuration has incremental predictive value after fees, funding payments, slippage and selection effects. The timestamped feature archive, funding settlement treatment and exchange-specific contract normalization are still required.

## Section C — Order-book and microstructure context

### What was tested

The scanner requested a bounded 50-level order-book snapshot and calculated best bid/ask, spread, bid/ask depth, imbalance and wall-ratio features. The smoke run returned a live snapshot:

| Measure | Value | Caveat |
|---|---:|---|
| Levels | `50` | Snapshot depth, not persistent L2 history |
| Best bid | `64349.99` | Current venue quote |
| Best ask | `64350.00` | Current venue quote |
| Spread | `0.001554 bps` | Exchange snapshot; not execution slippage |
| Imbalance | `0.7345` | Side-relative snapshot metric |
| Bid depth | `23.47684` | Venue and unit dependent |
| Ask depth | `3.59303` | Venue and unit dependent |

### Result

The order-book layer is operationally integrated and explainable. It degrades gracefully when depth data is unavailable and records the timestamp and source. The strategy does not claim that a wall ratio is a durable signal; it is a current context feature that must be validated against subsequent returns.

### Gap

There is no historical order-book event stream, queue-position model, cancellation/replenishment analysis, latency model or fill simulator. A snapshot cannot support claims about order-flow toxicity, spoofing resistance, adverse selection or actual executable edge. This layer is therefore **not validated as alpha**.

## Section D — Macro and aggregate on-chain context

### What was tested

The smoke run queried CoinGecko global context and DefiLlama aggregate stablecoin supply. FRED/DXY remained disabled because the exact series, release-time alignment and access path were not configured.

| Macro field | Measured result | Correct use |
|---|---:|---|
| BTC dominance | `56.5629%` | Slow market-structure context |
| Global market-cap change, 24h | `+0.4768%` | Slow risk-appetite context |
| Aggregate stablecoin supply | `$306.43B` | Broad liquidity context |
| Aggregate stablecoin supply change, 7d | `+0.3345%` | Slow context, not intraday flow |
| DXY/FRED | Disabled | No unverified macro substitution |

### Result

The macro layer is implemented with a conservative interpretation: it can supply broad context, but it is not presented as a 15-minute predictive trigger. Aggregate stablecoin supply is not treated as wallet-labelled exchange netflow, whale movement, mint/burn attribution or causal liquidity evidence.

### Gap

The repository does not contain point-in-time historical macro features aligned to candle close and release availability. DXY and other macro series must be aligned using information available at the decision timestamp, not merely by joining a later revised value. No claim of macro-factor predictive power is made.

## Section E — Fusion model and feature-level research

### What was implemented

`src/signalbot/fusion.py` now provides a bounded, interpretable feature layer. It normalizes context into side-relative features, records feature contributions, computes feature coverage, and labels the active model source. The default runtime is explicitly `heuristic_untrained`; no production-trained model or fabricated labels are committed.

The following research utilities were added:

| Utility | Purpose | Safety behavior |
|---|---|---|
| `scripts/train_fusion_model.py` | Fit a small logistic model from a real labelled feature CSV | Requires at least 20 complete rows and both classes; creates no rows |
| `scripts/feature_ablation.py` | Chronological baseline-plus-one-feature ablation | Requires a real time-ordered panel and a final holdout; reports log loss, Brier and AUC |
| `scripts/architecture_validation.py` | Compare old baseline evidence with new architecture status | Explicitly marks new OOS as `not_tested` without a feature panel |
| `scripts/context_smoke_test.py` | Probe current provider availability | Current snapshots are marked `current_context_only` |

### Result

The model path is more auditable than a black-box score because each feature and contribution can be logged. However, explainability is not evidence of profitability. The current runtime score is a **research heuristic**, not a calibrated probability. The old validation showed all observed signals concentrated in the 90–100 confidence bucket, which is a warning against interpreting the integer confidence field as a reliable probability scale.

### Gap

No real labelled feature panel exists in the repository. Therefore there is no honest feature-by-feature out-of-sample contribution table for funding, OI, order-book imbalance, stablecoin supply or macro context. There is also no calibration curve, probability-integral score, nested model-selection procedure or multiple-testing correction for the new feature family.

## Section F — Strategy integration and safety gates

### What was implemented

The runtime flow now collects macro context once per scan and derivatives/order-book context per symbol, then passes these records to the redesigned strategy. The legacy OHLCV candidate is no longer sufficient by itself when `fusion.require_context=true`; minimum feature coverage and minimum fusion score are configured gates. Notifications include context coverage, model source, feature contributions and provenance caveats.

The implementation preserves the existing risk controls: per-trade risk cap, daily-loss lock, maximum drawdown pause, open-trade cap, TP/SL state tracking and no order-placement path. Provider failures do not automatically become positive signals.

### Result

The redesign improves **observability and conservative gating**. It does not prove that the legacy indicator candidate was repaired. The architecture is best described as **hybrid context-gated research instrumentation**.

### Gap

No portfolio-level risk simulation was run for the new context score. The existing historical baseline showed high cross-symbol return correlation, with pairwise mean correlation about `0.825`, so five symbols should not be treated as five independent bets. Funding, spread, partial fills, exchange outages and simultaneous signal concentration remain operational risks.

## Section G — Deep validation and operational readiness

### Tested evidence

The following checks passed after implementation:

| Check | Result |
|---|---:|
| Unit tests | **6 passed** |
| Repository validator | **Passed** |
| Python compile check | **Passed** |
| Markdown/YAML diff hygiene | **Passed** |
| Current provider smoke test | **Passed with nullable endpoint errors recorded** |
| Architecture validation harness | **Passed; new OOS correctly marked not tested** |
| Existing 90-day indicator baseline | **Tested, but weak: 238 OOS trades and −18.0R** |
| New-feature OOS backtest | **Not available** |
| New-feature ablation | **Not available** |
| Final untouched holdout | **Not run** |
| Live/paper forward test | **Not started** |

### Baseline evidence that must not be over-interpreted

The old frozen-parameter validation is useful as a negative baseline, not as proof of the redesign. Its aggregate result was `−18.0R` over 238 OOS trades. Bootstrap uncertainty was wide, with a reported 95% win-rate interval of approximately `24.79%–36.55%` and net-result interval of `−60R–+24R`. Monte Carlo diagnostics reported a historical maximum drawdown of `40R`, a P95 maximum drawdown of `44R` and a P95 maximum loss streak of `18` trades. These results support caution; they do not support live deployment.

### Operational smoke result

The runtime path successfully obtained current derivatives, order-book and macro context on 2026-08-18. The same run also demonstrated why nullable handling is necessary: open-interest history returned an HTTP error and the long/short endpoint produced a JSON decoding error. The scanner preserved those failures and did not silently impute a bullish or bearish state.

### Remaining validation gates

1. Build a point-in-time feature panel containing OHLCV, funding, OI, order-book snapshots, macro fields, endpoint availability and decision timestamps.
2. Freeze the feature definitions and thresholds before a time-ordered walk-forward run.
3. Replay fees, spread, slippage, funding payments, latency, missed fills and same-bar TP/SL ambiguity.
4. Run one-factor-at-a-time and nested feature-selection ablations on an untouched final holdout.
5. Calibrate the confidence score and report reliability, Brier score and confidence-bucket sample sizes.
6. Run a frozen-parameter paper test for at least 4–8 weeks and 30–50 closed trades, with no discretionary override.
7. Run portfolio-level exposure and correlation stress tests before considering any live capital.

## Updated risk register

| Risk | Current impact | Mitigation implemented | Residual risk / required gate |
|---|---|---|---|
| Data-source outage or endpoint schema change | Missing context can block or alter signals | Nullable fields, source provenance, error capture and conservative `require_context` gate | Provider contract tests, alerting and historical replay still required |
| Historical-feature leakage | Artificially optimistic new-feature performance | No trained artifact shipped; real-panel-only scripts; explicit timestamp language | Point-in-time archive and final holdout remain required |
| Order-book snapshot is not executable liquidity | Spread/depth may overstate fill quality | Bounded snapshot and caveat logging | L2 history, latency and fill simulator required |
| Funding/OI semantics vary by venue | Cross-venue feature misinterpretation | Source and symbol metadata retained | Contract normalization and funding settlement replay required |
| Macro revision and release timing | Look-ahead through revised data | DXY disabled by default; slow macro labelled as context | Release-vintage alignment required |
| Confidence is not calibrated probability | High score may create false certainty | Model source and coverage exposed; no production model claimed | Calibration curve and untouched holdout required |
| Feature crowding / retail-trap exposure | Generic indicators may produce crowded, non-durable edge | Retail-trap audit and orthogonal layer separation documented | Incremental OOS contribution must be positive after friction |
| Correlated positions | Multiple symbols can lose together | Existing open-trade cap and correlation diagnostics | Portfolio risk budget and factor-level exposure limit required |
| GitHub Actions scheduling delay | Signal arrives late | Workflow warning and no order execution | Low-latency scheduler required for execution-critical use |
| News classifier error | False suppression or missed event | Keyword-based classifier is conservative and logged | Event-time dataset and precision/recall evaluation required |
| Same-candle TP/SL ambiguity | Backtest/live accounting can be biased | Limitation documented; no claim of execution accuracy | Tick or lower-timeframe replay required |
| Operational secret/configuration error | Notifications may fail or unsafe limits may load | Secrets separated from config; environment overrides documented | Deployment checklist and canary run required |

## Retail-trap audit

### Generic or crowded components

The legacy EMA trend, RSI/MACD momentum, volume confirmation and 20-candle breakout/breakdown stack is generic and widely accessible. It is easy to describe, easy to optimize, and vulnerable to regime dependence and parameter crowding. The previous validation’s concentration of signals in a single high-confidence bucket and its weak aggregate OOS result are consistent with a score that can look selective without being calibrated. Funding-rate direction, simple order-book imbalance and broad market-cap change are also common features; their presence alone is not differentiation.

### Potentially differentiated components

The more defensible contribution is not a single secret indicator. It is the engineering discipline around **source-aware context fusion**: current context is separated from historical evidence, provider missingness is preserved, slow macro data is not mislabeled as high-frequency alpha, and a feature cannot silently become positive merely because an endpoint failed. The offline model trainer and ablation utilities also create a path toward falsifiable research rather than an opaque hand-tuned score.

This is a process and architecture differentiation, not demonstrated market differentiation. It becomes genuine only if the new context features improve an untouched holdout after friction, remain stable across symbols and regimes, and survive a frozen paper test. Until then, the system should be described as better-instrumented—not as better-performing.

## Final updated verdict

The verdict is **unchanged and more strongly qualified**. The redesign is useful and technically more complete, but it is not currently trade-worthy. The old indicator baseline is negative on the latest aggregate OOS test, while the new orthogonal layers have only passed a current-data availability smoke test. No improvement claim is justified.

The system may be used for research logging and paper trading after configuration review. It should not be used to size live positions, promise win rate, or infer that `confidence` is a probability. The minimum decision gate for reconsidering live use is: a real point-in-time feature archive; friction-aware walk-forward and final holdout; calibrated confidence; positive and stable incremental contribution from orthogonal features; portfolio stress testing; and at least 4–8 weeks of frozen-parameter paper evidence with 30–50 closed trades.

## References

[1]: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data "Binance USDⓈ-M Futures market-data documentation"

[2]: https://docs.coingecko.com/demo/reference/endpoint-overview "CoinGecko Demo API endpoint overview"

[3]: https://api-docs.defillama.com/ "DefiLlama API documentation"

[4]: https://fred.stlouisfed.org/ "Federal Reserve Economic Data (FRED)"

[5]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule "GitHub Actions scheduled workflows"

[6]: https://github.com/ccxt/ccxt "CCXT exchange library"
