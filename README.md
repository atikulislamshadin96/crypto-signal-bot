# Automated Crypto Signal Bot

এটি একটি explainable, GitHub Actions-চালিত crypto market signal generation system। প্রতি ১৫ মিনিটে workflow চালু হয়ে configured crypto pairs-এর multi-timeframe OHLCV data সংগ্রহ করে, EMA/RSI/MACD/ATR/volume confluence বিশ্লেষণ করে, সাম্প্রতিক RSS crypto news-এর sentiment ও high-impact event filter প্রয়োগ করে এবং risk checks পাস করা setup হলে structured signal Telegram ও Discord-এ পাঠায়।

> **Disclaimer:** এটি আর্থিক পরামর্শ নয়; শুধুমাত্র বিশ্লেষণ-ভিত্তিক সিগন্যাল। কোনো trade নেওয়ার আগে নিজস্ব গবেষণা, paper trading এবং স্বাধীন risk assessment করুন। এই repository কোনো নির্দিষ্ট prop firm-এর API, rule বা challenge-এর সঙ্গে যুক্ত নয়।

## কী কী অন্তর্ভুক্ত আছে

| Component | Implementation |
| --- | --- |
| Market data | CCXT exchange adapter; default Binance spot public OHLCV |
| Timeframes | Configurable entry, confirmation এবং higher-timeframe bias |
| Strategy | EMA trend, RSI/MACD momentum, ATR exits, volume confirmation, breakout structure |
| News | RSS headlines, keyword sentiment, high-impact event suppression |
| Signal | Entry, stop loss, take profit, risk-reward, confidence, confluence এবং position size |
| Risk | Per-trade risk cap, daily loss lock, maximum drawdown pause, open-trade cap |
| Storage | Versioned JSONL signal log, CSV export, JSON trade state ও performance summary |
| Notifications | Telegram Bot API এবং Discord webhook; failure হলে scan চালু থাকে |
| Automation | `.github/workflows/signal_scan.yml`, ১৫ মিনিটের cron ও manual dispatch |
| Backtesting | `signalbot.backtest.run_backtest`-এর মাধ্যমে historical OHLCV replay |

## Project structure

```text
.
├── .github/workflows/signal_scan.yml
├── config.yaml
├── config.example.yaml
├── data/.gitkeep
├── requirements.txt
├── src/signalbot/
│   ├── backtest.py
│   ├── config.py
│   ├── formatters.py
│   ├── indicators.py
│   ├── market.py
│   ├── models.py
│   ├── news.py
│   ├── notifier.py
│   ├── risk.py
│   ├── runner.py
│   ├── storage.py
│   └── strategy.py
└── tests/
```

## GitHub setup

প্রথমে repository-তে `config.yaml`-এ symbols, timeframe, risk threshold এবং news feed নিজের প্রয়োজন অনুযায়ী সম্পাদনা করুন। কোনো API key, bot token, chat ID বা webhook URL config file-এ লিখবেন না। এরপর repository-এর **Settings → Secrets and variables → Actions → New repository secret** থেকে নিচের secrets যোগ করুন।

| Secret | Required | Purpose |
| --- | ---: | --- |
| `TELEGRAM_BOT_TOKEN` | Telegram চাইলে | Bot API token |
| `TELEGRAM_CHAT_ID` | Telegram চাইলে | Target chat/channel ID |
| `DISCORD_WEBHOOK_URL` | Discord চাইলে | Discord channel webhook |
| `EXCHANGE_API_KEY` | Public spot data-র জন্য নয় | Private exchange endpoints দরকার হলে |
| `EXCHANGE_API_SECRET` | Public spot data-র জন্য নয় | Private exchange endpoints দরকার হলে |
| `ACCOUNT_BALANCE` | Recommended | Position sizing-এর current account balance |
| `INITIAL_BALANCE` | Recommended | Drawdown baseline |
| `RISK_PER_TRADE_PCT` | Optional | Default `1.0`; সর্বোচ্চ configured cap-এর মধ্যে রাখুন |
| `DAILY_LOSS_LIMIT_PCT` | Optional | Default `5.0` |
| `MAX_DRAWDOWN_PCT` | Optional | Default `10.0` |
| `MAX_OPEN_TRADES` | Optional | Default `5` |
| `MIN_CONFIDENCE` | Optional | Default `65` |
| `MIN_CONFLUENCE` | Optional | Default `4` |

Binance public market data fetch করতে সাধারণত exchange credentials দরকার হয় না। Credentials ব্যবহার করলে withdrawal permission ছাড়া আলাদা read-only API key ব্যবহার করুন। এই bot কোনো order placement করে না।

## Telegram configuration

Telegram-এ BotFather দিয়ে bot তৈরি করে token নিন এবং bot-কে target chat বা channel-এ যুক্ত করুন। `TELEGRAM_BOT_TOKEN` ও `TELEGRAM_CHAT_ID` secret সেট করলেই notification সক্রিয় হবে। Discord-এর জন্য target channel-এ একটি webhook তৈরি করে `DISCORD_WEBHOOK_URL` secret সেট করুন। দুটিই না থাকলে scanner signal log লিখবে, কিন্তু external notification পাঠাবে না।

## Local run

Python 3.11 বা পরবর্তী সংস্করণ এবং একটি virtual environment ব্যবহার করুন।

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m signalbot.runner scan --config config.yaml
PYTHONPATH=src python -m signalbot.runner summary --config config.yaml
```

Local environment-এ secret দিতে হলে shell environment ব্যবহার করুন; `.env` file commit করবেন না। একটি scan cycle-এর সময় কোনো নির্দিষ্ট symbol-এর data বা news feed ব্যর্থ হলে সেই অংশটি log করে পরবর্তী symbol-এর scan চালিয়ে যায়।

## Strategy logic

প্রতিটি configured pair-এর জন্য entry timeframe, confirmation timeframe এবং higher-timeframe bias নেওয়া হয়। একটি candidate-এর জন্য সাধারণত নিচের explainable factors বিবেচনা করা হয়: higher-timeframe EMA trend, RSI ও MACD momentum, volume spike, এবং ২০-candle breakout/breakdown। `MIN_CONFLUENCE`-এর চেয়ে কম factor থাকলে signal তৈরি হয় না। ATR-এর ভিত্তিতে dynamic stop এবং target নির্ধারণ করা হয়; fixed pip বা black-box prediction ব্যবহার করা হয় না।

সাম্প্রতিক relevant headline-এ বিপরীত sentiment অথবা high-impact keyword থাকলে candidate suppress করা হয়। News integration conservative filter হিসেবে কাজ করে; এটি কোনো headline-এর সম্পূর্ণ অর্থ, market reaction বা causality বোঝার দাবি করে না।

## Risk management

`risk` section-এ initial balance, current balance, per-trade risk, daily loss limit, maximum drawdown এবং maximum open trades রাখা হয়েছে। Position size হিসাব হয়:

```text
risk_amount = current_balance × risk_per_trade_pct / 100
position_size = risk_amount / abs(entry - stop_loss)
```

Closed trade log-এর realized PnL থেকে daily loss এবং account equity থেকে drawdown হিসাব করা হয়। Daily loss limit পূর্ণ হলে UTC দিনের বাকি সময়ে নতুন signal বন্ধ থাকে। Maximum drawdown পূর্ণ হলে system pause mode-এ যায় এবং risk alert পাঠায়। এটি generic framework; exchange margin, fees, slippage, funding, leverage, liquidation বা tax হিসাব করে না।

## Logs and performance tracking

| File | Meaning |
| --- | --- |
| `data/signals.jsonl` | প্রতিটি accepted signal-এর structured record |
| `data/signals.csv` | Spreadsheet-friendly signal export |
| `data/trades.json` | OPEN, TP_HIT, SL_HIT বা CLOSED trade state |
| `data/performance.json` | Total signals, win rate, average R, total R এবং closed trade count |

প্রতি scheduled cycle-এ OPEN trade-গুলোর latest ticker দেখে TP বা SL touch হয়েছে কিনা update করা হয়। একই candle-এ উভয় level ছোঁয়া বা intrabar sequence নির্ণয় করা যায় না; live ticker polling-এর সীমাবদ্ধতার কারণে এটি conservative production accounting নয়।

## Backtesting

Backtest module strategy-এর সরল historical replay দেয়। CSV-তে `timestamp,open,high,low,close,volume` columns থাকলে:

```python
import pandas as pd
from signalbot.backtest import run_backtest
from signalbot.config import load_config

frame = pd.read_csv("historical_ohlcv.csv", parse_dates=["timestamp"]).set_index("timestamp")
result = run_backtest(frame, load_config("config.yaml"))
print(result)
```

Backtest-কে out-of-sample validation, fees/slippage modelling এবং paper trading দিয়ে যাচাই করুন। Past performance future result-এর নিশ্চয়তা নয়।

## GitHub Actions behavior

Workflow `workflow_dispatch`-এ manually চালানো যায় এবং `*/15 * * * *` cron-এ প্রতি ১৫ মিনিটে schedule করা হয়েছে। GitHub Actions scheduled workflows কিছুটা delay হতে পারে এবং public repositories-এ inactivity বা platform policy-র কারণে pause হতে পারে। এটি execution-critical trading বা guaranteed low-latency system হিসেবে ব্যবহার করবেন না। Workflow data artifact upload করে এবং পরিবর্তিত `data/` files commit করে। একই সময়ে দুটি scan overlap না করার জন্য workflow concurrency ব্যবহার করা হয়েছে।

## Tests

```bash
PYTHONPATH=src pytest -q
```

Tests deterministic helper logic, risk guards এবং indicator behavior cover করে। Live exchange, RSS, Telegram ও Discord integration আলাদা external systems হওয়ায় CI-তে mock করা হয়েছে; production credentials test suite-এ প্রয়োজন নেই।

## Safety and limitations

এই project signal তৈরি করে, order execute করে না এবং কোনো exchange account-এ funds move করে না। Market data stale হতে পারে, RSS feed unavailable হতে পারে, news classifier keyword-based হওয়ায় ভুল classification করতে পারে, এবং GitHub Actions-এর schedule low-latency guarantee দেয় না। Slippage, fees, latency, order-book depth, partial fill, exchange outage এবং concurrent positions-এর portfolio correlation model করা হয়নি। Live capital ব্যবহারের আগে দীর্ঘ paper-trading period, independent review এবং conservative limits আবশ্যক।

## References

[1]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule "GitHub Actions scheduled workflows"

[2]: https://github.com/ccxt/ccxt "CCXT exchange library"

[3]: https://core.telegram.org/bots/api "Telegram Bot API"

[4]: https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks "Discord webhooks"

[5]: https://www.binance.com/en/markets "Binance markets"
