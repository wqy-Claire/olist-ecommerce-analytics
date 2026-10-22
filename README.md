# Olist E-commerce Analytics

GMV attribution, delivery-time cohort analysis, and GMV forecasting on 100k+ real
Brazilian e-commerce orders — SQL-first (DuckDB).

## Business questions

1. **GMV attribution**: when and why did GMV growth slow down / drop? Decompose into
   order volume × average order value × category/region structure, and locate the
   contributing segments.
2. **Delivery-time cohort (quasi-experiment)**: do customers in slow-delivery states
   repurchase significantly less within 30/90 days? Estimate the revenue impact of
   improving delivery speed.
3. **GMV forecasting**: forecast the next 3 months of GMV with prediction intervals
   and driver decomposition.

## Data

[Olist Brazilian E-Commerce public dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(~100k orders, 2016-09 to 2018-10). 9 raw tables imported as-is into DuckDB; raw CSVs
are not committed to this repo (public dataset, download from Kaggle).

| table | rows | content |
|---|---|---|
| orders | 99,441 | order timestamps & status (one row per order) |
| order_items | 112,650 | items per order (one-to-many, max 21 items/order) |
| order_payments | 103,886 | payments per order (max 29 payments/order) |
| order_reviews | 99,224 | review scores 1–5 |
| customers | 99,441 | customer unique ids & locations |
| geolocation | 1,000,163 | zip-code coordinates (avg ~52.6 rows per zip — heavy duplication) |
| products | 32,951 | product attributes & category (Portuguese) |
| sellers | 3,095 | seller ids & locations |
| category_translation | 71 | Portuguese → English category names |

Data profiling results (see `02_profile.py`): 2.98% of orders have no delivered
timestamp; review scores are polarized (57.78% five-star, 11.51% one-star).

## Tech stack

DuckDB (all extraction & aggregation in SQL) · pandas (analysis only) · matplotlib / statsmodels

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install duckdb pandas matplotlib statsmodels
python 01_load_sql.py    # builds olist.duckdb from the CSVs in olist_data/
python 02_profile.py     # data profiling queries
```

## Status

- [x] D1: data warehouse load + data profiling
- [ ] D2: dirty-data inventory + business question finalization
- [ ] Ch.1: GMV attribution
- [ ] Ch.2: delivery-time × repurchase cohort
- [ ] Ch.3: GMV forecasting
- [ ] README: results, AI usage statement, interview walkthroughs

## AI usage

(to be completed at project close — this project is built with AI-assisted tutoring:
code review by an AI assistant; all SQL and conclusions are written and verified by the author.)
