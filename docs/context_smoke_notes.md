# Context smoke-test notes

**Run:** 2026-08-18 11:15–11:16 UTC
**Command:** `PYTHONPATH=src python scripts/context_smoke_test.py --config config.yaml --symbol BTC/USDT`

| Layer | Result | Measured evidence | Gap |
|---|---|---|---|
| Binance Futures funding | Available | `lastFundingRate=0.00007045` | Current snapshot only; no complete repository history |
| Binance Futures open interest | Available | `openInterest=106119.42` | `openInterestHist` returned HTTP error in this run |
| Global long/short ratio | Unavailable | Endpoint response was not valid JSON in this run | Region/endpoint availability must be treated as nullable |
| Exchange order book | Available | Spread `0.001554 bps`; imbalance `0.7345`; 50 levels returned | Snapshot is not historical L2 data; wall ratios are venue-specific |
| CoinGecko global | Available | BTC dominance `56.5629%`; 24h market-cap change `0.4768%` | Low-frequency/cached macro context, not 15m alpha |
| DefiLlama stablecoin aggregate | Available | Supply `$306.43B`; 7-day change `0.3345%` | Aggregate daily context, not wallet-level flow |
| FRED/DXY | Disabled | No DXY feature was used in this run | Must choose and configure exact series before production use |

**Interpretation:** The feasible runtime layer is operational for current funding, current OI, order-book snapshot, BTC dominance, market-cap change and aggregate stablecoin supply. Historical orthogonal feature data is still **not available in the repository**, so no honest new-feature OOS performance claim is made from this smoke test. Missing endpoints are preserved as missing; they are not imputed as positive evidence.
