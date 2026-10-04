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

The first deliverable is the [research plan](docs/research-plan.md). Code comes after the design and data invariants are fixed.
