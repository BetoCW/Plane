# Probabilistic Reverse Engineering of Stochastic Multipliers

This project infers the probabilistic model behind a stochastic process that generates positive multipliers (\u2265 1) with heavy tails, using only observed outputs grouped in sessions. It validates i.i.d. assumptions, computes the empirical survival function S(x)=P(X\u2265x), fits candidate distributions (Exponential, Pareto, Truncated Exponential), and provides probabilities, expectations, and simulations.

## Quick Start

1. Create a Python venv and install deps:

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
```

Note: This workflow uses manual data entry and file merging; OCR support has been removed to keep the project lightweight.

2. Run with example data:

```bash
python -m plane.cli fit --data examples/sessions.csv --column multiplier
```

## CLI Overview

- `fit`: Load sessions, validate i.i.d., compute survival, fit models, show summary.
- `prob`: Report P(X\u2265x) for thresholds using best model.
- `simulate`: Generate synthetic rounds from the fitted model.
- `add`: Append manually provided multipliers to a CSV/JSON.
- `merge`: Merge multiple CSV/JSON files into a single dataset.

## Manual Data Ops

Append values to a file:

```bash
python -m plane.cli add --out c:\Users\BetoCW´s\Documents\Plane\data\session1.csv --values 1.98 2.46 8.17 1.79 --session S1
```

Merge many files:

```bash
python -m plane.cli merge --inputs c:\Users\BetoCW´s\Documents\Plane\data\file1.csv c:\Users\BetoCW´s\Documents\Plane\data\file2.json --out c:\Users\BetoCW´s\Documents\Plane\data\all.csv
```

## Data Format

CSV with at least one numeric column of multipliers (\u2265 1). Optionally a `session_id` column to separate sessions.

Values should be provided as numeric multipliers (\u2265 1). Use `add` to accumulate datasets over time and `merge` before fitting.

## Notes

- We never predict a single round; we estimate probabilities and expectations under i.i.d. assumptions.
- Diagnostics include autocorrelation checks and KS tests.

## Examples

Add values and fit:

```bash
python -m plane.cli add --out c:\Users\BetoCW´s\Documents\Plane\examples\sessions.csv --values 1.98 2.46 8.17 1.79 --session NEW
python -m plane.cli fit --data c:\Users\BetoCW´s\Documents\Plane\examples\sessions.csv --column multiplier --session session_id --plot
```
# Plane
