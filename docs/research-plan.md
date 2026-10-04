# Research Plan — EXP-001 Daily Cross-Sectional Swing Ranking

Status: **design only; not yet trained**  
Protocol version: 1.0  
Research purpose only. No live order placement.

## Decision summary

EXP-001 will test whether medium-horizon, cross-sectional relative strength and reversal signals can rank liquid US stocks well enough to earn a positive return after an explicit 0.30% round-trip friction assumption.

This deliberately replaces a 5-minute starting point. With only three positions and 0.30% modeled round-trip friction, a short intraday system needs an implausibly large and repeatable edge relative to typical liquid-stock movement, and sparse IEX prints make execution modeling fragile. A five-session holding period gives the hypothesis more price dispersion and amortizes costs without turning the first experiment into a slow, multi-month strategy.

The experiment can fail. No model will be promoted unless its out-of-sample trading results, not merely its ML metrics, pass the criteria below.

## 1. Trading horizon

- Features are finalized after the regular session close on decision date **T**.
- Entry is the next regular-session open, **T+1 open**.
- Scheduled exit is the open five trading sessions after entry.
- Positions may exit early only for data-integrity or forced-universe events in EXP-001. Stops, profit targets, and trailing exits are excluded because they add execution dimensions and require intraday path data.
- Signals are evaluated once per trading day.
- Long only, no leverage.

The label timestamps must store the exact feature time, entry time, and exit time. Merely shifting rows by five is not acceptable when bars are missing.

## 2. Stock universe

At each decision date, a symbol is eligible only when all of the following are known from information through T:

- US common stock with usable daily OHLCV history;
- closing price at least $5;
- trailing 60-session median dollar volume at least $20 million;
- at least 252 prior valid daily bars;
- not already held;
- not a market/sector context ETF.

Do not select the universe using future liquidity, future price, or full-sample data coverage. Rank and liquidity filters are recalculated independently at every timestamp.

Future bar availability is not an eligibility input because it is unknowable at T. In historical research, a missing exact entry or exit bar makes that sample's target unavailable. In simulation, a missing entry cancels the order and a missing scheduled exit invokes the documented next-valid-open exception with a data-quality flag.

Initial target breadth is roughly 100–300 eligible stocks per day. If the available Alpaca symbol list is based only on currently listed assets, EXP-001 is explicitly a survivorship-biased discovery experiment. It must not be described as institutional-quality historical evidence. A later experiment must add point-in-time membership and delisted securities before any stronger claim.

Context assets:

- SPY
- QQQ
- IWM
- sector ETFs: XLK, XLC, XLY, XLF, XLE, XLV, XLI, XLP, XLU, XLRE, XLB

Sector-relative features require a versioned stock-to-sector mapping with an effective date. If only a present-day mapping is available, sector-relative results must be separately flagged as biased; they may not silently enter the core model.

## 3. Required data

Primary source: Alpaca historical US equity bars using the configured IEX feed.

Required fields:

- timestamp, symbol, open, high, low, close, volume, trade count, VWAP when available;
- asset metadata needed to exclude non-common-stock instruments;
- corporate-action information or an explicitly documented adjustment mode;
- the same daily fields for market and sector ETFs.

Download and store raw responses before transformation. Every processed dataset records:

- source/feed;
- request date;
- date range;
- adjustment setting;
- symbol list and symbol-list provenance;
- raw file hashes;
- pipeline version.

Preferred span is 2016-01-01 through 2026-09-30. If coverage is shorter, preserve the ordering of the validation blocks below and require at least six years of usable history. Do not silently fill missing OHLCV bars. Context values may be forward-filled only after confirming the missing date is not a trading session for the context asset.

## 4. Prediction targets

The primary learning target is a cross-sectional ranking target:

```text
gross_return_i = exit_open_i / entry_open_i - 1
market_return   = SPY_exit_open / SPY_entry_open - 1
beta_i          = trailing 126-session beta estimated through T
residual_return_i = gross_return_i - beta_i * market_return
```

The training target is the within-date percentile rank of `residual_return_i`. Beta is clipped to a documented range and calculated only from past data.

Two secondary diagnostics are retained:

- absolute gross forward return;
- net forward return after fixed modeled round-trip friction.

A ranking win is not automatically tradable: execution also requires a positive absolute-return gate estimated only from training/validation data. This prevents the strategy from buying a stock expected to outperform a falling market while still losing money.

The official EXP-001 horizon, entry, exit, target, and cost settings are immutable once the first validation fold is scored. Any change creates EXP-002 or later.

## 5. Feature groups

Only features with a stated hypothesis enter the first benchmark.

### Stock price structure

- close-to-close returns over 1, 2, 5, 10, 20, and 60 sessions;
- overnight gap and intraday return;
- true range and close location within the daily range;
- distance from trailing 20- and 60-session highs/lows.

Hypothesis: medium-horizon continuation and short-horizon reversal coexist and may be separable by regime and volatility.

### Trend and volatility

- close/EMA ratios for 10, 20, and 60 sessions;
- normalized EMA slopes;
- 10-, 20-, and 60-session realized volatility;
- ATR as a fraction of price;
- short/long volatility ratio.

Hypothesis: the same raw return has different meaning in stable and stressed conditions.

### Volume and liquidity

- log dollar volume;
- volume divided by its trailing 20-session median;
- causal volume z-score;
- turnover acceleration where the required denominator is available.

Hypothesis: price moves with unusual participation are more persistent, while illiquid observations are less executable.

### Market and cross-sectional context

- SPY, QQQ, and IWM returns and trend state;
- stock return minus SPY/QQQ/IWM return at matched horizons;
- rolling beta and correlation to SPY;
- causal cross-sectional percentile ranks for momentum, reversal, volatility, and relative volume;
- breadth: fraction of eligible stocks above their 20- and 60-session averages;
- cross-sectional dispersion.

Hypothesis: relative information is more stable than forecasting the market level, and signal behavior changes with breadth and dispersion.

### Sector context

Sector ETF trend and stock-minus-sector returns are an optional feature block. They are benchmarked separately and are excluded if the effective-dated mapping cannot be defended.

No centered windows, full-sample normalization, future membership, or same-date threshold contamination are allowed. All cross-sectional values for date T are computed as one batch using only data available by T.

## 6. Models and baselines

Models are compared in increasing complexity:

1. **No-ML baselines**
   - 20-session residual momentum rank;
   - 5-session reversal rank;
   - fixed 50/50 momentum–reversal composite.
2. **Regularized linear model**
   - Ridge or Elastic Net regression on the ranked residual target.
3. **Nonlinear tree model**
   - HistGradientBoostingRegressor.
4. **Diversity benchmark**
   - ExtraTreesRegressor with restrained depth and minimum leaf size.

A ranking-native model may become a later experiment, but EXP-001 should first establish whether simple tabular methods contain stable signal. Hyperparameter grids must be small and declared before scoring. The winning candidate is selected by validation-fold economic behavior plus ranking diagnostics, not minimum MSE alone.

Required model diagnostics:

- daily cross-sectional Spearman IC;
- median IC and IC by fold;
- return by score decile;
- monotonicity of decile returns;
- top 10%, 5%, 2%, and top-3 gross/net returns;
- calibration between predicted score and realized absolute return;
- feature stability and permutation importance computed only within validation folds.

## 7. Chronological validation

No random split is permitted.

Preferred schedule, conditional on coverage:

| Stage | Dates | Use |
|---|---:|---|
| Initial history | 2016–2020 | first training window |
| Walk-forward folds | 2021–2024 | expanding-window model and feature selection |
| Execution-tuning block | 2025 | choose at most two execution parameters |
| Frozen final test | 2026-01-01–2026-09-30 | evaluate once after artifacts are frozen |

For the 2021–2024 validation years, train only on earlier dates and generate predictions for the full next year. Refit at the start of each fold; do not refit using observations from inside the scored fold.

Because labels span five sessions, purge training observations whose label interval overlaps a validation boundary and apply a five-trading-session embargo. Rolling-feature warm-up rows are excluded, not imputed.

If the preferred date span is unavailable, create an equivalent ordered schedule with:

- at least three walk-forward validation blocks;
- a separate execution-tuning block;
- a final untouched block covering at least nine months;
- exact dates committed before training.

The frozen test may be run exactly once for EXP-001. Any design response to that result becomes a new experiment ID and a new future holdout.

## 8. Execution rule

At each decision time:

1. Score every eligible stock as one cross-sectional batch.
2. Exclude held symbols and symbols without valid next-open execution data.
3. Apply one frozen minimum expected-absolute-return gate.
4. Rank remaining candidates by model score.
5. Enter the highest-ranked names until no slot remains, with no more than one new position per symbol.
6. If no candidate passes the gate, hold cash.

Only two execution axes may be tuned on 2025:

- minimum expected absolute gross return;
- score percentile cutoff.

The portfolio still selects at most the top three available names. Neighboring settings must behave sensibly; an isolated optimum is rejected.

## 9. Backtest assumptions

- Starting cash: $10,000.
- Maximum open positions: 3.
- Maximum allocation: 20% of current marked-to-market equity per position.
- Maximum gross exposure: 60%.
- Long only; no leverage.
- Entry fill: next open increased by 0.05% slippage.
- Exit fill: scheduled exit open decreased by 0.05% slippage.
- Commission: 0.10% of notional on entry and 0.10% on exit.
- Official round-trip friction: approximately 0.30%.
- Integer-share sizing unless the configured broker/data assumptions explicitly support fractional shares.
- Cash and commissions are reserved at entry.
- Open positions are marked to market daily.
- Simultaneous candidates are ranked once; later symbols do not see portfolio state from a fictional serial signal calculation.
- No same-symbol duplicate position.
- No stop loss, take profit, or same-day re-entry in EXP-001.
- Missing entry data means no trade. Missing scheduled-exit data triggers the documented next-valid-open policy and a data-quality flag, never a fabricated fill.
- Gross and net ledgers are run from identical trades so the cost difference is exact.

A buy-and-hold SPY benchmark and an equal-weight eligible-universe benchmark are reported over the same calendar period, but they are not substitutes for the strategy's absolute after-cost profitability.

## 10. Expected sample and trade counts

With 100–300 eligible stocks over roughly ten years, the expected supervised dataset is approximately 250,000–750,000 symbol-date rows before exclusions.

Portfolio capacity, not prediction rows, limits realized trades. Three slots with a five-session hold imply a rough ceiling near 150 completed trades per year when continuously invested. The expected useful range is:

- 60–150 completed trades per year;
- 240+ trades across the four walk-forward validation years;
- roughly 50–120 trades in a nine-month frozen period.

These are planning estimates, not success metrics. If the strategy produces too few trades, uncertainty must be reported rather than hidden behind the large row count. Overlapping signals share market exposure, so the effective independent sample size is lower than the raw trade count.

## 11. Bias and leakage audit

The pipeline must fail loudly on:

- features timestamped after the decision close;
- entry at the same close used to compute features;
- row shifts that do not correspond to exact trading dates;
- duplicate symbol/timestamp rows;
- overlapping labels left unpurged at fold boundaries;
- normalization fitted outside the training fold;
- current-date predictions included in their own causal threshold history;
- universe eligibility based on future liquidity or coverage;
- current constituent lists presented as point-in-time history;
- sector mappings without effective-date provenance;
- corporate actions that create impossible returns;
- missing or non-positive prices;
- context joins that borrow future observations;
- NaN or infinite model inputs;
- model feature-order mismatch.

Additional known limitations:

- IEX is not the consolidated tape; liquidity and fill realism may differ from full-market data.
- Present-day symbol discovery can leave survivorship bias even with causal rolling liquidity filters.
- Daily-bar slippage is a coarse approximation.
- Cross-sectional samples and overlapping holdings are correlated.
- Trying multiple models creates selection bias; every serious configuration must be logged.

## 12. Why the edge might exceed 0.30%

The hypothesis is plausible, not proven.

A five-session cross-section has materially more return dispersion than a five-minute bar, so selecting only the extreme predicted tail can target gross moves comfortably larger than 0.30%. Relative momentum, short-term reversal, abnormal volume, market beta, breadth, and volatility regime have distinct economic rationales and may help identify that tail. Waiting for a top-ranked, positive-absolute-return opportunity also allows no-trade periods.

The required hurdle is stricter than merely beating costs. Before frozen testing, the selected validation configuration should show:

- average gross trade at least +0.60%;
- average modeled net trade at least +0.30%;
- net profit factor at least 1.20;
- positive net results in at least three of four validation years;
- a broadly monotonic score-bucket relationship.

If the estimated gross edge is only 0.35%, it is too fragile. Model and execution error can easily consume the remaining 0.05%.

## 13. Early abandonment criteria

Stop EXP-001 before frozen testing if any of the following holds after the planned validation runs:

- fewer than three valid walk-forward folds or unusable data coverage;
- median daily cross-sectional IC is non-positive;
- top-score buckets are not directionally monotonic in most folds;
- average gross trade is below 0.45%, leaving too little room for the official costs;
- average net trade is non-positive or net profit factor is below 1.10;
- fewer than 200 validation trades in total;
- one year, one symbol, one sector, or the best 5% of trades explains most profit;
- results depend on one narrow threshold while neighboring settings fail;
- net profitability disappears under a diagnostic 0.45% round-trip cost;
- the best model does not beat the predeclared no-ML baseline convincingly;
- leakage or universe bias cannot be bounded well enough to interpret the result.

Passing these screens means “worthy of one frozen test,” not “proven profitable.”

## 14. Exact implementation stages

1. **Repository protocol**
   - add dependency lock, configuration schema, deterministic seed policy, experiment registry, and immutable experiment IDs.
2. **Raw data acquisition**
   - implement chunked Alpaca downloads, retry/rate-limit handling, raw-response storage, manifest hashes, and context assets.
3. **Universe construction**
   - classify instruments, compute causal eligibility, and report daily coverage and turnover.
4. **Data validation**
   - enforce timestamp, price, duplicate, corporate-action, missing-bar, and context-join invariants.
5. **Feature pipeline**
   - generate causal stock, market, volume, volatility, and cross-sectional features with unit tests using hand-built toy data.
6. **Target pipeline**
   - resolve exact next-open and five-session exit timestamps; calculate gross, residual, and net targets; test gap and missing-session cases.
7. **Baseline research**
   - score the three no-ML rules and produce fold-level decile/IC diagnostics before fitting ML.
8. **Model benchmark**
   - run the predeclared linear and tree models through the same expanding-window harness and log every attempted configuration.
9. **Prediction ledger**
   - persist only out-of-fold predictions with model version, training cutoff, feature version, and target timestamps.
10. **Event-driven portfolio engine**
    - simulate cash, positions, simultaneous signals, fills, costs, scheduled exits, and mark-to-market equity; reconcile every ledger entry.
11. **Validation report**
    - report gross/net return, annualized return, trades, win rate, average/median trade, gross/net profit factor, drawdown, Sharpe, monthly and yearly performance, stock/sector/regime concentration, deciles, and modeled costs.
12. **Execution tuning**
    - freeze the model, use only the designated 2025 block, tune the two declared axes, and require a stable parameter neighborhood.
13. **Freeze**
    - save model, feature order, hyperparameters, training cutoffs, execution config, code commit SHA, data-manifest hashes, and report template under an immutable EXP-001 artifact directory.
14. **Final test**
    - run the frozen 2026 period once, write the result whether good or bad, and do not alter EXP-001 afterward.
15. **Decision**
    - reject, replicate on better point-in-time data, or define EXP-002 with a new untouched evaluation period.

## Required reports for every serious portfolio run

At minimum:

- total and annualized return;
- gross and net return from identical trades;
- completed trades and average holding period;
- win rate;
- gross and net profit factor;
- average and median gross/net trade;
- maximum drawdown;
- Sharpe ratio with the stated periodicity and risk-free assumption;
- positive months, median month, worst month, best month;
- total commission, slippage, and combined modeled costs;
- results by year, symbol, sector, market regime, and score bucket;
- exposure, cash utilization, and turnover;
- concentration and outlier-removal diagnostics;
- bootstrap confidence interval using a date-block method that respects dependence.

## Promotion rule

EXP-001 is “promising” only if the frozen test is positive after costs, has profit factor above 1, positive average trade and Sharpe, acceptable drawdown, adequate trade count, no severe concentration, and behavior consistent with the prior folds. Strong classification or regression metrics cannot override a failed trading result.
