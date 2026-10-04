# quant-bot-2

Research-only quantitative trading project. It does **not** place real-money trades.

The project is being developed under a strict research protocol:

- optimize for credible after-cost performance, not headline ML metrics;
- preserve causal feature and execution timing;
- use chronological, purged validation;
- keep final test periods frozen;
- apply 0.10% commission and 0.05% slippage per side;
- allow the strategy to make no trade;
- report failures honestly.

The first deliverable is the [research plan](docs/research-plan.md). The repository now includes the Phase-2 configuration, causal universe/target utilities, Alpaca daily-bar downloader, and strict data validation tests.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e .
cp .env.example .env.local
```

Add Alpaca credentials to `.env.local`. Never commit that file.

## Validate before downloading

```bash
python -m quant_bot validate-config
python -m unittest discover -s tests -v
python -m quant_bot init-dirs
```

Then download the predeclared candidate universe and context assets:

```bash
python -m quant_bot download-bars
```

This does not train a model. Training remains blocked until download coverage, exact target timestamps, and dataset integrity pass their checks.
