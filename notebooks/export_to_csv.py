# %%
import pandas as pd
from sqlalchemy import create_engine
import os

# %%
DB_PATH     = "../database/adventureworks.db"
EXPORT_DIR  = "../powerbi/data"

os.makedirs(EXPORT_DIR, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}")

tables = [
    "dim_calendar",
    "dim_customer",
    "dim_product",
    "dim_territory",
    "fact_sales",
    "fact_returns",
    "vw_sales_summary",
]

for table in tables:
    df = pd.read_sql(f"SELECT * FROM {table}", engine)
    path = os.path.join(EXPORT_DIR, f"{table}.csv")
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"✓ {table}: {len(df)} linhas → {path}")

print("\n✓ Export concluído.")
# %%
