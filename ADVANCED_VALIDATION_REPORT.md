# Advanced Validation Report — Institutional-Rigor and Anti-Retail-Trap Audit

**Validation snapshot:** 2026-08-18 10:45 UTC
**Repository:** [`atikulislamshadin96/crypto-signal-bot`](https://github.com/atikulislamshadin96/crypto-signal-bot)
**Baseline:** Previous report commit `d105de4`
**Scope:** Master Prompt #3-এর Section A–G, expanded risk register, retail-trap audit এবং updated trade-worthiness verdict।

> **Finance disclaimer:** আমি licensed financial advisor নই—এটি strategy validation, guaranteed investment advice নয়। Cryptocurrency trading-এ মূলধন হারানোর ঝুঁকি রয়েছে।

## Executive summary

এই advanced run-এ previous report-এর ৬০ দিনের static result পুনরাবৃত্তি না করে একটি নতুন ৯০ দিনের market-data window, fixed-parameter walk-forward stability check, bootstrap uncertainty, Monte Carlo trade-sequence randomization, Binance/Kraken data cross-check, missing-candle/outlier audit এবং pair-correlation analysis চালানো হয়েছে।

সবচেয়ে গুরুত্বপূর্ণ ফলাফল হলো latest ৩০ দিনের fixed-parameter out-of-sample segment-এ **238টি signal, 73টি win, 164টি loss এবং −18.0R net result**। Bootstrap 95% interval-এ win rate **24.79%–36.55%** এবং net result **−60R–+24R** এসেছে। Monte Carlo sequence randomization-এ maximum drawdown-এর 95th percentile **44R** এবং loss-streak-এর 95th percentile **18টি consecutive loss** হয়েছে।

Previous report-এর `+5R` OOS ফলাফলের সঙ্গে এই result সরাসরি তুলনীয় নয় [5]: আগের run-এর sample window, split এবং timestamp আলাদা ছিল। নতুন run-এর ফলাফল আগের optimistic-looking positive result-কে confirm করেনি; বরং wider recent validation আরও সতর্ক conclusion সমর্থন করে। **Updated verdict: আগের “paper-trade only” verdict বদলে যায়নি; confidence আরও কমেছে। Strategy বর্তমানে live capital-এর জন্য trade-worthy নয়।**

---

## Validation status at a glance

| Area | Status | Evidence | Remaining gap |
|---|---|---|---|
| A. Statistical rigor | Partial | Bootstrap, fixed-window walk-forward এবং Monte Carlo চালানো হয়েছে। | True three-way holdout, tuned rolling walk-forward এবং multiple-testing correction নেই। |
| B. Anti-retail-trap design | Mostly not tested | Existing code review হয়েছে। | Liquidity-aware stop, retest confirmation, order-book/funding/OI filter implement বা test করা হয়নি। |
| C. Data integrity/regime | Partial | Binance 15m gap/outlier audit, Binance/Kraken return cross-check, regime classification। | Regime-by-regime strategy PnL এবং longer multi-year/delisted-universe test নেই। |
| D. Portfolio risk | Partial | 1h cross-pair return correlation matrix। | Concurrent positions, directional cap এবং portfolio equity curve নেই। |
| E. Circuit breakers | Code gap identified | Daily loss, max drawdown, open-trade cap ও cooldown existing। | Loss-streak, volatility-spike, drift ও stale-data guards নেই। |
| F. News sophistication | Code/test gap identified | Keyword filter ও high-impact blocking unit-tested। | Historical news replay, source credibility ও event relevance weighting নেই। |
| G. Paper protocol | Not started | Repository-তে live/paper records শূন্য। | Frozen version, 4–8 weeks এবং 30–50 closed-trade protocol চালু হয়নি। |

---

## Section A — Statistical Rigor ও Overfitting Discipline

### কী টেস্ট করা হয়েছে

Advanced run-এ বর্তমান পাঁচটি pair—BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT এবং XRP/USDT—এর জন্য Binance public OHLCV data ব্যবহার করা হয়েছে। Entry timeframe 15m, confirmation 1h এবং bias timeframe 4h। Run window ছিল 2026-05-20 10:45 UTC থেকে 2026-08-18 10:45 UTC পর্যন্ত; প্রথম ৬০ দিন fixed-parameter research/stability অংশ হিসেবে এবং শেষ প্রায় ৩০ দিন OOS segment হিসেবে replay করা হয়েছে। Reproducible script হলো [`scripts/advanced_validation.py`](scripts/advanced_validation.py) [4]।

### ফলাফল: latest OOS replay

| Metric | Result |
|---|---:|
| OOS signals | 238 |
| Wins / losses | 73 / 164 |
| Net result | **−18.0R** |
| Win rate | 30.67% |
| Historical maximum drawdown | 40.0R |
| Fees, slippage, funding | Not included |
| Portfolio overlap/correlation | Not included in this R replay |

এখানে `R` হলো configured stop distance-এর এক risk unit। Exit model ছিল 1.5 ATR stop এবং 3.0 ATR target; তাই friction বাদ দিলে target/stop payoff 2:1। Raw OOS win rate 30.67% এই payoff-এর theoretical 33.3% break-even-এর নিচে। বাস্তব fees, spread, slippage, funding এবং latency যোগ করলে result আরও খারাপ হওয়ার ঝুঁকি আছে।

### Walk-forward stability check

এটি একটি **fixed-parameter, four-window stability check**; window অনুযায়ী parameter re-tuning করা হয়নি। তাই এটি true rolling/expanding walk-forward optimizer নয়, কিন্তু performance-এর time stability পরীক্ষা করে।

| Window | Period role | Signals | Wins / losses | Win rate | Net result | Symbol-level DD sum* |
|---|---|---:|---:|---:|---:|---:|
| W1 | Early window | 205 | 77 / 128 | 37.56% | +26R | 39R |
| W2 | Middle window 1 | 156 | 58 / 98 | 37.18% | +18R | 32R |
| W3 | Middle window 2 | 120 | 46 / 73 | 38.33% | +19R | 39R |
| W4 | Most recent window | 172 | 56 / 113 | 32.56% | **−1R** | 48R |

`*` Symbol-level drawdowns যোগ করা portfolio drawdown নয়; concurrent portfolio simulation না থাকায় এটি কেবল diagnostic sum। W4-এর deterioration এবং latest OOS aggregate-এর negative result stability concern তৈরি করে। Pair-level range-ও uneven: একই fixed rule-এ SOL W3/W4-এ −12R/−17R, ETH প্রথম দুই window-এ −6R/−5R, কিন্তু BTC পরের তিন window-এ positive ছিল।

### Bootstrap confidence intervals

Latest OOS-এর 238টি trade result থেকে seed 42-এ 10,000 i.i.d. bootstrap resample চালানো হয়েছে। এটি point estimate-এর uncertainty দেখায়, কিন্তু serial dependence, pair correlation, overlapping exposure বা regime clustering ঠিক করে না।

| Statistic | Point estimate | Bootstrap 95% interval |
|---|---:|---:|
| Win rate | 30.67% | **24.79%–36.55%** |
| Net result | −18R | **−60R–+24R** |

Interval-এর width দেখায় যে sample-টি edge প্রমাণ করার জন্য যথেষ্ট precise নয়। Net-R interval একই সঙ্গে বড় negative ও positive outcome cover করে; তাই result-টি statistically robust positive expectancy হিসেবে report করা যাবে না।

### Monte Carlo trade-sequence randomization

Observed OOS R outcomes randomize করে seed 42-এ 10,000 sequence simulation চালানো হয়েছে। এটি historical order-এর path-dependence পরীক্ষা করে; এটি নতুন price path, correlation, liquidity বা execution simulation নয়।

| Statistic | Historical path | Monte Carlo P50 | Monte Carlo P95 |
|---|---:|---:|---:|
| Maximum drawdown | 40R | 32R | **44R** |
| Maximum consecutive loss streak | Not used as a predictive estimate | 12 | **18** |

এই result বর্তমান daily-loss বা max-drawdown guard-এর বাইরে repeated halt/restart behavior তৈরি করতে পারে—বিশেষত যদি signals একাধিক correlated pair-এ একসঙ্গে আসে।

### Multiple-testing awareness

EMA/RSI/MACD/volume/breakout factor combinations এবং prior reports-এর repeated evaluation-এর ফলে data-snooping ও selection bias-এর ঝুঁকি আছে। এই run-এ **Bonferroni/FDR correction, permutation-based null test বা deflated Sharpe-style multiple-testing correction চালানো হয়নি**। Bootstrap এবং Monte Carlo এই সমস্যার substitute নয়। একটি clean research registry, pre-registered hypotheses এবং untouched final holdout ছাড়া positive-looking slice selection-এর ঝুঁকি রয়ে গেছে।

### Gap

Prompt-এর অর্থে true three-way split—`in-sample` tuning, `validation` parameter check এবং একেবারে শেষে একবার touch করা **never-seen final holdout**—এখনো তৈরি হয়নি। এই advanced report নিজেই latest data touch করেছে, তাই এই data-কে future final holdout বলা যাবে না। কোনো নতুন tuning-এর আগে একটি versioned freeze এবং future-only final holdout দরকার।

---

## Section B — Market Microstructure ও Anti-Retail-Trap Design

### কী টেস্ট করা হয়েছে

বর্তমান strategy code review করে signal construction এবং stop/target placement পরীক্ষা করা হয়েছে। [`src/signalbot/strategy.py`](src/signalbot/strategy.py)-তে signal-এর প্রধান ingredients [1] হলো higher-timeframe EMA trend, RSI/MACD momentum, volume spike এবং 20-candle breakout/breakdown। Stop এবং target যথাক্রমে fixed ATR multiples থেকে নির্ধারিত হয়।

| Requirement | Current behavior | Result / gap |
|---|---|---|
| Liquidity-aware stop | `price ± 1.5 × ATR` | **Not implemented.** Swing high/low, round number বা visible liquidity pool থেকে buffer নেই। |
| False-breakout filter | Current candle close level cross করলেই breakout/breakdown factor | **Not implemented.** Post-break close confirmation, retest বা wick-only rejection নেই। |
| Illiquidity filter | Volume ratio threshold আছে | Partial only. Absolute dollar volume, spread, market depth বা minimum market-cap filter নেই। |
| Order-book depth | No order-book snapshot or historical depth | **Not tested.** |
| Funding / open interest | Configured market type spot | **Not applicable to current spot implementation; not available as a tested futures filter.** |
| Retail-trap avoidance | No explicit stop-hunt/liquidity-hunt model | **Gap.** Generic breakout signals may enter where crowd positioning is obvious. |

### ফলাফল

Anti-trap feature-এর কোনো performance test চালানো যায়নি, কারণ code-এ এই features implement করা নেই এবং historical order-book/funding/open-interest dataset repository-তে নেই। Volume confirmation-কে liquidity defense হিসেবে treat করা যাবে না: high volume breakout একই সঙ্গে genuine participation এবং stop-hunt উভয়ই হতে পারে।

### Gap

পরবর্তী version-এ অন্তত recent swing liquidity-এর বাইরে volatility-adjusted buffer, candle-close-plus-retest confirmation, wick/body ratio filter, spread/depth threshold এবং spot বনাম futures-এর জন্য আলাদা market-data contract দরকার। এগুলোর প্রত্যেকটির ablation ও out-of-sample test ছাড়া “anti-retail-trap” দাবি করা যাবে না।

---

## Section C — Data Integrity ও Regime Awareness

### Multi-exchange cross-check

Binance এবং Kraken-এর 1h close-return data BTC/USDT এবং ETH/USDT-এর জন্য cross-check করা হয়েছে [6]। Kraken-এর symbol mapping যেখানে `/USDT` available ছিল না, সেখানে equivalent `/USD` market ব্যবহার করা হয়েছে; এই cross-check strategy replay নয়, data sanity check।

| Pair | Binance rows | Kraken rows | Aligned returns | Return correlation | Median absolute close spread | P95 absolute close spread |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 2,160 | 721 | 720 | 0.992646 | 0.0136% | 0.0478% |
| ETH | 2,160 | 721 | 720 | 0.986951 | 0.0181% | 0.0928% |

Cross-exchange return correlation এবং low median spread major price path-এর জন্য reassuring, কিন্তু এটি Binance-only execution-এর spread, fill এবং wick risk eliminate করে না। Altcoin pairs-এর second-exchange validation এই run-এ করা হয়নি।

### Data gap ও outlier audit

প্রতিটি পাঁচটি pair-এর 15m validation frame-এ 8,641টি observed row-এর expected row count-ও 8,641 ছিল; এই defined interval-এ missing candle count **0** এবং simple outlier count **0**। Outlier threshold ছিল `max(10 × median absolute return, 5%)`।

এই audit-এর অর্থ হলো large gaps বা 5%-এর বেশি single-candle moves এই sample-এ ধরা পড়েনি; এটি exchange downtime, subtle bad ticks, duplicate semantics, timezone issues বা smaller flash-wicks-এর সম্পূর্ণ প্রমাণ নয়। Data source public OHLCV; raw checksum, exchange status feed এবং independent tick audit নেই।

### Regime classification

15m data-তে EMA(50)-EMA(200) absolute spread এবং 96-bar realized volatility প্রতিটির sample median threshold দিয়ে চারটি descriptive regime classify করা হয়েছে। এটি regime distribution test; strategy PnL-by-regime এখনো implement করা হয়নি।

| Pair | Trending/high-vol | Trending/low-vol | Ranging/high-vol | Ranging/low-vol |
|---|---:|---:|---:|---:|
| BTC | 32.36% | 17.65% | 17.65% | 32.35% |
| ETH | 33.11% | 16.90% | 16.90% | 33.10% |
| BNB | 36.36% | 13.65% | 13.65% | 36.35% |
| SOL | 36.10% | 13.90% | 13.90% | 36.09% |
| XRP | 35.08% | 14.92% | 14.92% | 35.07% |

### Survivorship bias

Universe-এ active/listed liquid-looking pairs manually configured। Delisted, suspended, failed বা untradeable tokens নেই। ফলে selection/survivorship bias থেকে results optimistic হতে পারে। এই report-এ delisted-universe reconstruction করা হয়নি।

### Gap

একটি defensible regime analysis-এর জন্য প্রতিটি signal-এর entry-time regime label রেখে regime-wise TP/SL, net R, drawdown, coverage এবং friction-adjusted expectancy report করতে হবে। Cross-exchange coverage অন্তত সব configured symbols-এ বাড়াতে হবে; longer history এবং exchange outage metadata-ও দরকার।

---

## Section D — Portfolio-Level ও Correlated Risk

### Correlation matrix

Five-pair 1h close-return correlation matrix চালানো হয়েছে। নিচের matrix একই underlying crypto risk factor-এর repeated exposure বোঝাতে সাহায্য করে; এটি trade-signal correlation নয়।

|  | BTC | ETH | BNB | SOL | XRP |
|---|---:|---:|---:|---:|---:|
| **BTC** | 1.000 | 0.887 | 0.790 | 0.857 | 0.842 |
| **ETH** | 0.887 | 1.000 | 0.776 | 0.869 | 0.844 |
| **BNB** | 0.790 | 0.776 | 1.000 | 0.772 | 0.750 |
| **SOL** | 0.857 | 0.869 | 0.772 | 1.000 | 0.863 |
| **XRP** | 0.842 | 0.844 | 0.750 | 0.863 | 1.000 |

Off-diagonal pairwise mean correlation **0.825**, minimum **0.750** এবং maximum **0.887**। তাই পাঁচটি signal-কে পাঁচটি independent risk unit হিসেবে count করা যাবে না।

### Current implementation এবং gap

Config-এ `max_open_trades: 5` আছে, কিন্তু same-direction notional cap, pair-correlation adjustment, BTC-beta aggregation বা portfolio-level equity curve নেই। বর্তমান OOS `R` replay individual signal ফল যোগ করেছে; overlapping trades, actual position sizing, simultaneous capital usage এবং correlated loss একসঙ্গে simulate করেনি।

**Not tested:** max concurrent directional exposure, portfolio equity curve, risk-of-ruin, capital reservation এবং signal de-duplication across symbols। পরবর্তী gate হলো portfolio-level event simulator, যেখানে capital, open positions, entry/exit timestamps, overlap এবং correlation-adjusted exposure একসঙ্গে model হবে।

---

## Section E — Additional Circuit Breakers

### Existing controls

বর্তমান risk module-এ daily-loss limit, maximum drawdown, maximum open trades এবং cooldown configuration আছে [2]। এই controls unit-tested/implementation-reviewed হয়েছে; কিন্তু advanced replay-এ live account state-এর সঙ্গে এগুলো enforce করে portfolio outcome তৈরি করা হয়নি।

| Requested breaker | Current status | Risk implication |
|---|---|---|
| Consecutive-loss halt | **Missing** | Monte Carlo P95 loss streak 18; system repeated low-quality signals পাঠাতে পারে। |
| Volatility-spike halt | **Missing** | ATR regime abnormal হলে fixed 1.5 ATR stop/3 ATR target unreliable হতে পারে। |
| Model/strategy drift detection | **Missing** | Rolling live win rate backtest baseline থেকে সরে গেলেও automatic alert নেই। |
| Data-staleness guard | **Missing** | Frozen exchange/news feed-এ stale price দিয়ে signal তৈরির ঝুঁকি। |
| Daily loss / max drawdown | Present, not fully replay-validated | Existing limits বাস্তব concurrent portfolio path-এ কীভাবে behave করে তা অজানা। |

### Gap

Circuit breaker যোগ করলেই edge তৈরি হবে না; এগুলো loss containment এবং operational safety controls। Implementation-এর পরে breaker-triggered versus untriggered performance আলাদা করে paper-test করতে হবে। Loss-streak halt-এর threshold arbitrary করা যাবে না; pre-registered policy, cooldown এবং human review path দরকার।

---

## Section F — News/Sentiment Sophistication

### কী টেস্ট করা হয়েছে

News layer RSS headline-এ keyword matching ব্যবহার করে positive/negative sentiment এবং high-impact block নির্ধারণ করে [3]। Existing unit test high-impact keyword block behavior cover করে; keyword classifier-এর historical predictive value test করা হয়নি।

| Requested capability | Current status | Finding |
|---|---|---|
| Context-aware sentiment | **Missing** | Negation, sarcasm, ambiguity এবং headline context বোঝে না। |
| Source credibility weighting | **Missing** | CoinDesk, Cointelegraph, Decrypt-এর জন্য আলাদা reliability score নেই। |
| Routine/noise vs market-moving event | Partial keyword gate | `hack`, `ETF`, `SEC`, `Fed` ইত্যাদি keyword block আছে; event severity, novelty, confirmation ও asset relevance নেই। |
| Historical news replay | **Not tested** | Backtest-এ `news_in_backtest: false`। |
| News delivery staleness | **Not tested** | RSS publication delay, duplicate headline এবং feed outage model করা হয়নি। |

### Gap

Keyword filter-কে alpha বা robust event filter বলা যাবে না। Source-tier metadata, duplicate clustering, event taxonomy, asset/entity linking, publication timestamp alignment এবং historical replay দরকার। News guard-এর ভালো দিক হলো high-impact headline এ conservative suppression; কিন্তু false positive-এর কারণে valid signal miss এবং false negative-এর কারণে dangerous signal pass—উভয়ই quantify করা হয়নি।

---

## Section G — Strict Paper-Trading Protocol

### Current status

Repository-র `data/` directory-তে validation snapshot-এর আগে কোনো `signals.jsonl`, `trades.json` বা performance record ছিল না। অর্থাৎ live/paper forward test **শুরু হয়নি**। GitHub Actions workflow present থাকা বা schedule configured থাকা successful paper execution-এর evidence নয়।

### Required protocol

| Protocol item | Current status | Required gate |
|---|---|---|
| Parameter freeze/tag | **Not done** | Paper start-এর আগে immutable `v1.0-frozen` বা equivalent commit/tag। |
| No tuning during paper run | **Not enforceable** | Protected config hash এবং change log দরকার। |
| Per-trade timestamp | Signal model-এ planned fields আছে | Actual paper record শূন্য; live verification বাকি। |
| Entry / SL / TP | Signal model-এ planned fields আছে | Actual outcome record শূন্য। |
| Slippage assumption / realized slippage | **Missing** | প্রতিটি paper trade-এ assumed ও observed slippage field দরকার। |
| Duration | 0 weeks | Minimum 4–8 weeks। |
| Closed trades | 0 | Minimum 30–50 closed trades। |
| Live-capital decision | **Blocked** | Above gates pass না হওয়া পর্যন্ত real-money execution নয়। |

Paper test চলাকালীন strategy parameter, factor definition, symbol universe, risk limit বা notification semantics বদলানো যাবে না। Change হলে নতুন version এবং নতুন paper cohort শুরু করতে হবে; পুরনো cohort-কে নতুন parameters-এর evidence হিসেবে reuse করা যাবে না।

---

## Retail-trap audit

### Generic / crowded components

Strategy-র trend ও momentum core—EMA fast/slow relationship, RSI(14), MACD histogram, volume spike এবং 20-candle breakout/breakdown—সাধারণ technical-analysis vocabulary। Fixed ATR stop/target এবং 2:1 nominal payoff-ও widely used pattern। এই elements-এর combination code-এ explainable হলেও market-level differentiation প্রমাণ করে না; crowded rules-এর বিরুদ্ধে obvious breakout entries এবং visible liquidity zones-এ stop clustering-এর ঝুঁকি থাকে।

| Component | Retail-crowding assessment | Why |
|---|---|---|
| EMA trend filter | High | Textbook trend-following signal। |
| RSI/MACD momentum | High | Common lagging confirmation pair। |
| Volume spike | High | Breakout confirmation হিসেবে broadly used। |
| 20-candle breakout/breakdown | High | Obvious level-following behavior। |
| 1.5 ATR SL / 3 ATR TP | Medium–high | Common volatility-normalized risk template; liquidity-aware নয়। |
| Confidence score | High risk of false precision | Factor count থেকে `90` label; probability calibration নেই। |

### Genuine differentiation কোথায় আছে

কিছু operational differentiation আছে, কিন্তু এখনো **genuine trading alpha** হিসেবে প্রমাণিত নয়। Multi-timeframe data alignment, signal ID/deduplication, explainable factor list, high-impact RSS suppression, JSONL/CSV logging, risk guard এবং Telegram/Discord structured delivery retail script-এর তুলনায় better engineering hygiene। এগুলো reproducibility ও operational safety উন্নত করে; crowded entry logic-এর expected return আলাদা করে প্রমাণ করে না।

বর্তমানে genuine anti-trap differentiation নেই: recent swing liquidity offset, round-number avoidance, false-break retest, order-book imbalance, funding/OI crowding বা liquidity-depth-aware position sizing implement করা হয়নি। তাই system-কে “smart-money”, “institutional” বা “market-maker-resistant” বলা evidence-supported নয়।

### Honest retail-trap conclusion

Strategy-টি generic indicator stack থেকে কিছুটা ভালোভাবে packaged, কিন্তু strategy logic নিজে এখনো generic/crowded। High-impact news suppression এবং risk controls crowding risk কমাতে পারে, কিন্তু তারা predictable breakout entry বা fixed ATR exit-এর structural weakness সমাধান করে না। Retail-trap audit-এর ফলাফল **fail / not demonstrated**, pass নয়।

---

## Updated risk register

এটি previous report-এর limitations table-এর extension। Severity এবং status ইচ্ছাকৃতভাবে conservative রাখা হয়েছে।

| Risk | Severity | Evidence/status | Mitigation gate |
|---|---|---|---|
| Latest OOS negative expectancy | Critical | 238 trades, −18R, 30.67% win rate | Rebuild after friction-aware testing; no live capital। |
| True holdout contamination | Critical | Never-seen final holdout এখনো নেই | Pre-register three-way split and touch final holdout once। |
| Multiple-testing/data snooping | High | No FDR/Bonferroni/permutation correction | Research registry, null test, correction and independent replication। |
| Bootstrap dependence assumption | High | i.i.d. trade resample only | Block/bootstrap by time, pair and regime। |
| Monte Carlo under-modeling | High | Sequence shuffle; no price/liquidity simulation | Portfolio and microstructure-aware simulation। |
| Retail-crowded entry | High | EMA/RSI/MACD/volume/breakout stack | Retest, wick, liquidity-pool and crowding filters with ablation। |
| Fixed ATR stop liquidity exposure | High | No swing/round-number buffer | Liquidity-aware stop placement and execution test। |
| No order-book/funding/OI filter | High for futures; Medium for spot | Not available/tested | Either remain spot-only explicitly or add data-backed filters। |
| Correlated multi-pair risk | Critical | Mean 1h return correlation 0.825 | Directional cap, beta aggregation and concurrent portfolio simulator। |
| Regime fragility | High | W4 aggregate net −1R; SOL W3/W4 negative | Regime-wise PnL and regime-conditional policy। |
| Fees/slippage/funding omitted | Critical | All advanced R results gross | Friction model and paper realized slippage। |
| Data-quality blind spots | Medium–high | Zero defined gaps/outliers, but limited rule | Multi-source checks, raw audit, outage/status metadata। |
| Survivorship bias | High | Active configured pairs only | Historical universe including delisted/suspended assets। |
| News false positives/negatives | High | Keyword-only, no historical replay | Source/event taxonomy, entity linking and replay। |
| Missing circuit breakers | High | No loss-streak, vol-spike, drift, stale guards | Implement, unit-test, paper-test and alert। |
| No forward evidence | Critical | 0 live/paper records | 4–8 weeks, 30–50 closed trades, frozen parameters। |
| Operational schedule delay | Medium | GitHub Actions cron is not execution-grade | Paper monitor, stale-run alert and non-execution-critical positioning। |
| False confidence label | High | All accepted signals in 90–100 bucket | Continuous calibrated score and reliability curve। |
| No real-money execution guardrail | Critical | No order placement logic, but notifications may influence trades | Keep execution disabled; require separate reviewed system and confirmation process। |

---

## Final updated verdict

### Verdict change

**Previous verdict:** paper-trade only; live capital নয়।
**Updated verdict:** verdict formally বদলায়নি; বরং আরও negative evidence যুক্ত হয়েছে। Latest 30-day OOS replay **−18R**, bootstrap net-R interval **−60R–+24R**, Monte Carlo P95 drawdown **44R**, confidence score degenerate এবং anti-retail-trap design unproven। তাই live trade-worthy হওয়ার কোনো defensible basis এখনো নেই।

এটি investment recommendation নয়; এটি repository evidence-এর উপর technical validation conclusion। Past positive slice বা nominal 2:1 payoff-এর ওপর ভর করে live deployment করা উচিত নয়।

### Remaining gates before any live-capital consideration

| Gate | Pass condition |
|---|---|
| Statistical design | Untouched three-way final holdout, parameter freeze এবং clean future-only test। |
| Robustness | Proper rolling/expanding walk-forward, block/bootstrap uncertainty, multiple-testing correction এবং independent replication। |
| Trading friction | Fees, spread, slippage, funding, latency ও partial-fill model-এর পরে positive net expectancy। |
| Anti-trap design | Liquidity-aware SL, false-break retest, wick filter এবং relevant depth/crowding tests-এর পরে OOS improvement। |
| Regime evidence | Trending/ranging/high-vol/low-vol-এর প্রতিটিতে separate performance এবং failure policy। |
| Portfolio risk | Correlation-aware concurrent position cap, portfolio equity curve এবং drawdown/risk-of-ruin analysis। |
| Safety controls | Loss-streak, volatility-spike, drift এবং stale-data circuit breakers implemented ও paper-tested। |
| News quality | Source credibility, event taxonomy এবং historical news replay-এর পরে measurable benefit বা safe suppression। |
| Paper protocol | Frozen version, 4–8 weeks, অন্তত 30–50 closed trades, timestamped outcomes এবং realized/assumed slippage। |

**Final decision:** বর্তমান system-কে research এবং strictly paper-trading tool হিসেবে রাখা যায়। Above gates pass না করা পর্যন্ত **real-money execution বা live-capital signal-following অনুমোদনযোগ্য নয়**।

---

## Reproducibility and references

Advanced numerical outputs `advanced_validation.json`-এ generated হয় এবং artifactটি `.gitignore`-এ রাখা হয়েছে। Re-run করার script হলো [`scripts/advanced_validation.py`](scripts/advanced_validation.py); report content validation-এর জন্য আগের [`scripts/validate_report.py`](scripts/validate_report.py) pattern ব্যবহার করা হয়েছে।

[1]: [Strategy signal construction](src/signalbot/strategy.py) "EMA, RSI/MACD, volume, breakout and ATR stop/target logic"

[2]: [Risk controls](src/signalbot/risk.py) "Daily loss, drawdown, open-trade and cooldown logic"

[3]: [News classifier and filter](src/signalbot/news.py) "RSS keyword sentiment and high-impact suppression"

[4]: [Advanced validation script](scripts/advanced_validation.py) "Walk-forward, bootstrap, Monte Carlo, data, correlation and cross-exchange checks"

[5]: [Previous validation report](VALIDATION_REPORT.md) "Earlier evidence baseline and original paper-only verdict"

[6]: https://github.com/ccxt/ccxt "CCXT exchange integration library"

[7]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule "GitHub Actions scheduled workflow behavior"
