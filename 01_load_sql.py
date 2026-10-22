"""Step 01: build the DuckDB data warehouse from raw Olist CSVs.

Run:  .venv/bin/python 01_load_sql.py
Creates olist.duckdb with all 9 raw tables imported as-is (no cleaning here —
cleaning decisions belong to the analysis chapters, where they can be justified).
"""

from pathlib import Path

import duckdb

DATA_DIR = Path(__file__).parent / "olist_data"
DB_PATH = Path(__file__).parent / "olist.duckdb"

# table name -> csv file; column sets/types are intentionally left to
# read_csv_auto so we can SEE the dirty types in the data-profiling step.
TABLES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

con = duckdb.connect(DB_PATH)
for table, csv in TABLES.items():
    path = DATA_DIR / csv
    con.execute(f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT * FROM read_csv_auto('{path}', header=true)
    """)
    n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"{table:20s} {n:>10,} rows")

print(f"\nDone. Database at {DB_PATH}")
con.close()
