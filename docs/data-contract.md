# EXP-001 Data Contract

## Decision timestamp

Daily features for session T become usable only after that regular session has completed. The earliest permitted fill is the next canonical market session's open.

## Required bar columns

| Column | Rule |
|---|---|
| symbol | non-empty, normalized uppercase string |
| timestamp | timezone-aware and unique within symbol |
| open/high/low/close | finite and strictly positive |
| volume | finite and non-negative |
| trade_count | optional source diagnostic |
| vwap | optional source diagnostic |

Rows must be ordered by symbol and timestamp before downstream processing. Duplicate symbol/timestamp rows, invalid ranges, non-finite values, and impossible OHLC relationships are fatal.

## Canonical sessions

Target timestamps are resolved against a canonical session index and then joined to exact symbol/session bars. Per-symbol row shifting is prohibited: a missing bar must produce an unavailable target, never a shorter or longer accidental horizon.

For EXP-001:

- feature session: T;
- entry: canonical session T+1 open;
- exit: five canonical sessions after entry, T+6 open.

## Eligibility versus labels

Universe eligibility at T uses only data through T: price, trailing dollar volume, available history, instrument classification, and context exclusions. Whether a future entry or exit bar exists cannot affect eligibility at T.

During historical research, a missing exact entry or exit bar makes the target unavailable. During simulation, a missing entry bar cancels the order; a missing scheduled exit follows the separately documented next-valid-open exception and raises a data-quality flag.

## Credentials and raw data

Alpaca credentials belong in environment variables or `.env.local`. They must never be written to manifests, logs, reports, or commits. Raw API pages are stored under ignored `data/raw/` paths and hashed in a manifest before transformation.

