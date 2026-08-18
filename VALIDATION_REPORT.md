# Validation Report — Automated Crypto Signal Bot

**Validation date:** 2026-08-18 10:30 UTC

**Repository:** [`atikulislamshadin96/crypto-signal-bot`](https://github.com/atikulislamshadin96/crypto-signal-bot)

**Validation scope:** Setup, automated tests, reproducible OHLCV backtest, factor co-occurrence analysis, confidence-score calibration এবং repository-তে উপস্থিত forward-test evidence।

> **Finance disclaimer:** আমি licensed financial advisor নই—এটি strategy validation, guaranteed investment advice নয়। Cryptocurrency trading-এ মূলধন হারানোর ঝুঁকি রয়েছে।

## Executive conclusion

**বর্তমান strategy live capital-এর জন্য trade-worthy বলে pass করা হচ্ছে না।** এটি গবেষণা ও paper-trading-এর জন্য যথেষ্ট deterministic এবং reproducible, কিন্তু live deployment-এর আগে আরও tuning, friction-aware validation এবং forward testing প্রয়োজন।

বাস্তব ৫টি USDT pair-এর ৬০ দিনের OHLCV replay-এ out-of-sample ফলাফল ছিল **142টি signal, 34.51% win rate, +5.0R net এবং 17.0R maximum drawdown**। Strategy-র configured payoff প্রায় 2R winner বনাম 1R loser হওয়ায় theoretical break-even win rate প্রায় 33.3%—অতএব out-of-sample edge মাত্র প্রায় 1.2 percentage points, এবং এই হিসাবের মধ্যে fees, slippage, funding, spread বা execution latency নেই। এই friction যোগ হলে সামান্য positive result সহজেই শূন্য বা negative হতে পারে।

সবচেয়ে গুরুত্বপূর্ণভাবে, repository-তে এখনো কোনো live forward-test record পাওয়া যায়নি। Confidence score-ও calibrated নয়: সব accepted signal একই `90–100` bucket-এ পড়েছে। তাই এই score-কে probability বা reliable ranking হিসেবে ব্যবহার করা যাবে না। **বর্তমান verdict: paper-trade only; live capital নয়।**

## 1. Setup ও test status summary

| Check | Evidence / command | Status | Interpretation |
|---|---|---:|---|
| Repository structure | `scripts/validate.py` | PASS | Required config, workflow ও README উপস্থিত। |
| Configuration loading | `PYTHONPATH=src python scripts/validate.py` | PASS | `config.yaml` load হয়েছে এবং expected risk/timeframe values যাচাই হয়েছে। |
| Unit tests | `PYTHONPATH=src pytest -q` | PASS — **4 passed** | Sentiment, high-impact news block, indicators এবং daily-loss guard cover হয়েছে। |
| Python compilation | `PYTHONPATH=src python -m compileall -q src tests` | PASS | Source ও tests compile হয়েছে। |
| Dependency installation | `sudo pip3 install -r requirements.txt` | PASS | CCXT, pandas, NumPy, PyYAML, requests ও pytest install হয়েছে। |
| GitHub Actions workflow | `.github/workflows/signal_scan.yml` | PRESENT / ACTIVE | ১৫ মিনিটের schedule ও manual dispatch আছে; repository history-তে successful scheduled run-এর evidence নেই। |
| Secrets setup | GitHub secret values | **NOT VERIFIED** | এই validation-এ কোনো secret value পড়া বা inspect করা হয়নি। |
| Forward-test logs | `data/signals.jsonl`, `data/trades.json` | **NO RECORDS** | Repository-তে validation-এর আগে live signal/trade outcome record ছিল না। |

এই status summary operational readiness এবং trading validity-কে আলাদা করে। Code ও test pass করা মানে strategy profitable বা production-ready প্রমাণিত হওয়া নয়।

## 2. Validation methodology

Validation run-টি [`scripts/validation_analysis.py`](scripts/validation_analysis.py) দিয়ে করা হয়েছে। এটি Binance public OHLCV data CCXT adapter-এর মাধ্যমে সংগ্রহ করেছে এবং পাঁচটি configured pair ব্যবহার করেছে: BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT এবং XRP/USDT। Data source ও exchange adapter-এর implementation [`src/signalbot/market.py`](src/signalbot/market.py)-তে রয়েছে।

| Item | Value |
|---|---|
| Data source | Binance public OHLCV via CCXT |
| Evaluation window | 2026-06-19 10:30 UTC → 2026-08-18 10:30 UTC |
| In-sample split | 2026-06-19 10:30 UTC → 2026-07-31 10:30 UTC |
| Out-of-sample split | 2026-07-31 10:30 UTC → 2026-08-18 10:30 UTC |
| Symbols | BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT |
| Entry timeframe | 15m |
| Confirmation timeframe | 1h |
| Trend-bias timeframe | 4h |
| Forward evaluation horizon | সর্বোচ্চ 96টি entry candle, অর্থাৎ প্রায় 24 ঘণ্টা |
| Exit model | 1.5 ATR stop, 3.0 ATR target; target hit = +2R, stop hit = −1R |
| News in backtest | **না** |
| Fees, spread, slippage, funding | **না** |
| Position sizing / daily-loss lock in replay | **না**; ফলাফল raw signal R এবং live risk guard-এর সমতুল্য নয় |

> **Important:** এই replay strategy implementation-এর rule behavior যাচাই করে; এটি executable order backtest নয়। [`src/signalbot/backtest.py`](src/signalbot/backtest.py)-এর lightweight backtest helper এবং validation script-এর multi-timeframe replay একে অপরের পূর্ণ বিকল্প নয়।

## 3. Backtest metrics — in-sample বনাম out-of-sample

`R` হলো configured stop distance-এর সমান এক risk unit। Win rate-এর দুটি view রাখা হয়েছে: closed-only এবং all generated signals। Timeout signal-কে win হিসেবে ধরা হয়নি।

| Metric | In-sample | Out-of-sample | Change / reading |
|---|---:|---:|---|
| Total signals | 281 | 142 | OOS sample ছোট, তবে শূন্য নয়। |
| Closed trades | 278 | 142 | IS-এ 3টি timeout; OOS-এ timeout নেই। |
| Wins / losses | 97 / 181 | 49 / 93 | উভয় split-এই losses বেশি। |
| Win rate, closed only | 34.89% | 34.51% | −0.38 pp; nominally stable, কিন্তু low edge। |
| Win rate, all signals | 34.52% | 34.51% | প্রায় অপরিবর্তিত। |
| Net result | +13.0R | +5.0R | Positive, কিন্তু OOS edge সীমিত। |
| Average result per signal | +0.046R | +0.035R | OOS-এ expectancy কমেছে। |
| Maximum drawdown | 38.0R | 17.0R | Large path risk; live guard replay-এ enforce হয়নি। |
| Target / stop payoff | +2R / −1R | +2R / −1R | Fees ও slippage বাদে break-even win rate প্রায় 33.3%। |

In-sample থেকে out-of-sample-এ win rate প্রায় একই থাকলেও net expectancy **0.046R থেকে 0.035R**-এ নেমেছে। OOS positive থাকা আশাব্যঞ্জক নয় বলার কারণ হলো margin খুব কম: 34.51% win rate একটি 2:1 payoff-এর theoretical break-even-এর সামান্য ওপরে, এবং বাস্তব trading friction model করা হয়নি।

আরও একটি risk warning হলো 17R OOS maximum drawdown। Configured risk যদি প্রতিটি signal-এ 1% হয়, raw replay path-এর 17R drawdown প্রায় 17% risk-unit movement বোঝাতে পারে; বাস্তব live risk guard আগে system pause করতে পারে, তাই এই backtest drawdown এবং live account drawdown সরাসরি এক জিনিস নয়।

## 4. Factor contribution analysis

নিচের analysis **factor co-occurrence**, causal contribution নয়। বর্তমান strategy-তে accepted signal-এর জন্য কমপক্ষে চারটি factor একসঙ্গে থাকতে হয়; তাই একই signal একাধিক row-তে গণনা হয়েছে। কোনো factor সরিয়ে পুনরায় backtest করা হয়নি, সুতরাং এই table থেকে কোনো indicator “কতটা profit তৈরি করেছে” এমন দাবি করা যাবে না।

| Factor present in signal | IS signals | IS win rate | OOS signals | OOS win rate |
|---|---:|---:|---:|---:|
| Higher-timeframe downtrend | 196 | 36.73% | 67 | 37.31% |
| Negative RSI/MACD momentum | 196 | 36.73% | 67 | 37.31% |
| 20-candle breakdown | 196 | 36.73% | 67 | 37.31% |
| Higher-timeframe uptrend | 85 | 29.41% | 75 | 32.00% |
| Positive RSI/MACD momentum | 85 | 29.41% | 75 | 32.00% |
| 20-candle breakout | 85 | 29.41% | 75 | 32.00% |
| Volume confirmation | 281 | 34.52% | 142 | 34.51% |

### Interpretation

Short-side/downtrend/breakdown cluster এই sample-এ long-side/uptrend/breakout cluster-এর চেয়ে ভালো করেছে: OOS win rate যথাক্রমে **37.31% বনাম 32.00%**। এটি একটি tuning hypothesis হতে পারে, কিন্তু regime-specific sample এবং low margin-এর কারণে স্থায়ী asymmetry হিসেবে গ্রহণ করা যাবে না।

Volume confirmation সব signal-এ উপস্থিত, কারণ এটি বর্তমান conjunction rule-এর অংশ হিসেবে effectively universal gate হয়েছে। তাই 34.51% OOS win rate-এর বাইরে volume-এর independent incremental value প্রমাণিত হয়নি। Proper ablation test দরকার: একই data split-এ volume বাদ দিয়ে, প্রতিটি factor বাদ দিয়ে এবং factor order randomize করে ফলাফল তুলনা করতে হবে।

## 5. Confidence বনাম win-rate analysis

বর্তমান implementation-এ confidence হিসাব হয় `50 + (confluence_count × 10)` এবং accepted signal-এর minimum confluence 4। ফলে এই validation-এ প্রত্যেক accepted signal-এর confidence `90`, এবং সব signal `90–100` bucket-এ পড়েছে। এই design-এর কারণে confidence score এখন **calibrated probability নয়** এবং confidence-vs-winrate curve তৈরি করা যায়নি।

| Confidence bucket | In-sample signals | IS win rate | Out-of-sample signals | OOS win rate |
|---|---:|---:|---:|---:|
| 65–69 | 0 | N/A | 0 | N/A |
| 70–79 | 0 | N/A | 0 | N/A |
| 80–89 | 0 | N/A | 0 | N/A |
| 90–100 | 281 | 34.52% | 142 | 34.51% |

এই ফলাফল সরাসরি দেখায় যে `90/100` label-কে “90% probability” বা even high-quality ranking হিসেবে ব্যাখ্যা করা যাবে না। Confidence calibration-এর জন্য continuous score দরকার—যেমন factor strength, distance from EMA, normalized volume, RSI distance এবং news state-এর out-of-sample calibrated mapping—তারপর confidence bucket-ভিত্তিক পর্যাপ্ত sample-এ reliability test দরকার। বর্তমান score কেবল rule-count label।

## 6. Forward-test log

Validation run-এর আগে repository-তে কেবল `data/.gitkeep` ছিল। `data/signals.jsonl`, `data/signals.csv`, `data/trades.json` বা `data/performance.json`-এ কোনো live/forward-test record পাওয়া যায়নি।

| Forward-test field | Observed value |
|---|---|
| Live signal records | 0 |
| Closed live trades | 0 |
| Live TP/SL outcomes | 0 |
| Live win rate | N/A |
| Live average R | N/A |
| Telegram delivery evidence | N/A |
| Discord delivery evidence | N/A |
| Earliest available live timestamp | N/A |
| Forward-test conclusion | শুরু হয়নি / evidence unavailable |

GitHub Actions workflow file repository-তে active এবং scheduled trigger সংজ্ঞায়িত আছে, কিন্তু workflow active থাকা scheduled execution সফল হয়েছে—এমন কোনো run artifact বা committed log এই validation snapshot-এ নেই। তাই code configuration দেখে forward performance অনুমান করা হয়নি।

## 7. Known limitations and risk register

| Limitation / risk | Why it matters | Required follow-up |
|---|---|---|
| Short 60-day sample | Market regime coverage সীমিত; trend বা volatility regime বদলালে ফল পাল্টাতে পারে। | অন্তত কয়েকটি bull, bear এবং range regime জুড়ে multi-year walk-forward test। |
| Only five pairs | Cross-sectional robustness কম। | Predefined universe ও top-volume selection-এর ওপর broader test; selection bias track করা। |
| No fees or slippage | 1.2 pp OOS edge friction-এ হারিয়ে যেতে পারে। | Maker/taker fees, spread, slippage, funding এবং latency যুক্ত করা। |
| News disabled in replay | Live strategy-এর news suppression benefit বা harm মাপা হয়নি। | Timestamp-aligned historical news dataset দিয়ে news-on বনাম news-off ablation। |
| Confidence not calibrated | `90/100` label risk ranking বা probability নয়। | Continuous score, calibration curve এবং out-of-sample reliability bins। |
| Factor contribution is not causal | সব factors একই signal-এ co-occur করে। | One-factor-at-a-time ablation, permutation test এবং bootstrap confidence intervals। |
| Simplified intrabar exits | একই candle-এ SL ও TP উভয় touch হলে ordering uncertainty থাকে। | Tick/lowertimeframe execution model এবং explicit priority rule। |
| Live risk state differs from replay | Backtest daily loss, max drawdown pause ও portfolio correlation enforce করেনি। | Event-driven portfolio backtest with account equity, open positions and risk locks। |
| Correlation / concentration | BTC, ETH এবং altcoin signals একসঙ্গে একই crypto regime exposure দিতে পারে। | Portfolio-level exposure cap, correlated-risk aggregation এবং max concurrent directional risk। |
| Operational dependencies | Exchange/RSS/GitHub/Telegram/Discord outage signal miss করতে পারে। | Retry, alert-on-failure, stale-data guard এবং external uptime monitoring। |
| No paper-trading period | Implementation errors বা live data timing issues ধরা পড়েনি। | Minimum 4–8 weeks paper forward test before any capital decision। |
| No uncertainty intervals | Point estimates sample noise-এর সঙ্গে report হয়েছে। | Bootstrap confidence intervals, parameter perturbation এবং multiple-split validation। |

## 8. Recommended next validation gates

Live capital বিবেচনা করার আগে অন্তত চারটি gate পূরণ করা উচিত। প্রথমত, fees, spread, slippage এবং funding সহ out-of-sample replay-এ positive expectancy বজায় রাখতে হবে। দ্বিতীয়ত, confidence score calibration ও factor ablation সম্পন্ন করতে হবে। তৃতীয়ত, অন্তত 4–8 সপ্তাহের paper forward-test-এ timestamped signal, notification delivery, outcome update এবং risk pause evidence সংগ্রহ করতে হবে। চতুর্থত, portfolio-level drawdown এবং correlated exposure যুক্ত করে risk limits পুনরায় যাচাই করতে হবে।

এই gates-এর কোনোটি pass না করলে strategy-কে live trade-worthy বলা উচিত নয়। বিশেষভাবে, বর্তমানে observed OOS result positive হলেও **statistical and execution margin যথেষ্ট নয়**।

## Final verdict

**Verdict: আরও tuning ও validation দরকার; বর্তমানে live trade-worthy নয়।**

Strategy code modular, explainable এবং automated scan-এর জন্য operationally testable। কিন্তু backtest-এ দেখা edge ছোট, friction বাদ দেওয়া, confidence score degenerate, factor contribution causal নয় এবং forward-test evidence শূন্য। অতএব বর্তমান repository-কে research/paper-trading system হিসেবে রাখা যুক্তিযুক্ত; real-money deployment বা aggressive risk নেওয়া এই evidence দিয়ে সমর্থনযোগ্য নয়।

## References

[1]: [Repository strategy implementation](src/signalbot/strategy.py) "EMA, momentum, volume and breakout signal logic"

[2]: [Repository backtest helper](src/signalbot/backtest.py) "Lightweight historical strategy replay"

[3]: [Reproducible validation analysis](scripts/validation_analysis.py) "Multi-timeframe Binance OHLCV validation script"

[4]: https://github.com/ccxt/ccxt "CCXT exchange integration library"

[5]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule "GitHub Actions scheduled workflows"
