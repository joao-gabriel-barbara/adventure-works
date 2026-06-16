# %%
import pandas as pd
from sqlalchemy import create_engine
import os

# %%
# ── Configuração ──────────────────────────────────────────────
DATA_DIR = "../data"
DB_PATH  = "../database/adventureworks.db"

os.makedirs("../database", exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}")

# ── Helpers ───────────────────────────────────────────────────
def to_date_key(series: pd.Series) -> pd.Series:
    """Converte datetime para int YYYYMMDD — padrão de date_key em Star Schema."""
    return series.dt.strftime("%Y%m%d").astype(int)

def read(filename: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, filename), encoding='latin1')

# ═══════════════════════════════════════════════════════════════
# dim_calendar
# ═══════════════════════════════════════════════════════════════
print("Processando dim_calendar...")

cal = read("AdventureWorks_Calendar.csv")
cal["Date"] = pd.to_datetime(cal["Date"])

dim_calendar = pd.DataFrame({
    "date_key"   : to_date_key(cal["Date"]),
    "full_date"  : cal["Date"].dt.date,
    "year"       : cal["Date"].dt.year,
    "quarter"    : cal["Date"].dt.quarter,
    "month"      : cal["Date"].dt.month,
    "month_name" : cal["Date"].dt.strftime("%B"),
    "week"       : cal["Date"].dt.isocalendar().week.astype(int),
    "day_name"   : cal["Date"].dt.strftime("%A"),
})

dim_calendar.to_sql("dim_calendar", engine, if_exists="replace", index=False)
print(f"  ✓ {len(dim_calendar)} linhas")

# ═══════════════════════════════════════════════════════════════
# dim_territory
# ═══════════════════════════════════════════════════════════════
print("Processando dim_territory...")

terr = read("AdventureWorks_Territories.csv")
terr.columns = ["territory_key", "region", "country", "continent"]

terr.to_sql("dim_territory", engine, if_exists="replace", index=False)
print(f"  ✓ {len(terr)} linhas")

# ═══════════════════════════════════════════════════════════════
# dim_product  (colapsa Products + Subcategories + Categories)
# ═══════════════════════════════════════════════════════════════
print("Processando dim_product...")

prod     = read("AdventureWorks_Products.csv")
subcat   = read("AdventureWorks_Product_Subcategories.csv")
cat      = read("AdventureWorks_Product_Categories.csv")

# JOIN: product → subcategory → category
prod = (prod
        .merge(subcat, on="ProductSubcategoryKey", how="left")
        .merge(cat,    on="ProductCategoryKey",    how="left"))

dim_product = prod[[
    "ProductKey", "ProductSKU", "ProductName", "ModelName",
    "ProductDescription", "ProductColor", "ProductSize",
    "ProductStyle", "ProductCost", "ProductPrice",
    "SubcategoryName", "CategoryName"
]].copy()

dim_product.columns = [
    "product_key", "product_sku", "product_name", "model_name",
    "description", "product_color", "product_size",
    "product_style", "product_cost", "product_price",
    "subcategory_name", "category_name"
]

# Nulos em product_color → "Unknown"
dim_product["product_color"] = dim_product["product_color"].fillna("Unknown")

dim_product.to_sql("dim_product", engine, if_exists="replace", index=False)
print(f"  ✓ {len(dim_product)} linhas")

# ═══════════════════════════════════════════════════════════════
# dim_customer
# ═══════════════════════════════════════════════════════════════
print("Processando dim_customer...")

cust = read("AdventureWorks_Customers.csv")

dim_customer = cust[[
    "CustomerKey", "Prefix", "FirstName", "LastName",
    "BirthDate", "MaritalStatus", "Gender",
    "AnnualIncome", "TotalChildren", "EducationLevel",
    "Occupation", "HomeOwner"
]].copy()

dim_customer.columns = [
    "customer_key", "prefix", "first_name", "last_name",
    "birth_date", "marital_status", "gender",
    "annual_income", "total_children", "education_level",
    "occupation", "home_owner"
]

# Nulos → "Unknown" (padrão para dimensões em BI)
dim_customer["prefix"] = dim_customer["prefix"].fillna("Unknown")
dim_customer["gender"] = dim_customer["gender"].fillna("Unknown")

income_order = {
    "$10,000":  1,
    "$20,000":  2,
    "$25,000":  3,
    "$30,000":  4,
    "$40,000":  5,
    "$50,000":  6,
    "$60,000":  7,
    "$70,000":  8,
    "$80,000":  9,
    "$90,000":  10,
    "$100,000": 11,
    "$110,000": 12,
    "$120,000": 13,
    "$130,000": 14,
    "$150,000": 15,
    "$160,000": 16,
    "$170,000": 17,
}
dim_customer["income_sort"] = (
    dim_customer["annual_income"]
    .str.strip()
    .map(income_order)
    .fillna(99)
    .astype(int)
)

dim_customer.to_sql("dim_customer", engine, if_exists="replace", index=False)
print(f"  ✓ {len(dim_customer)} linhas")

sem_mapeamento = dim_customer[dim_customer["income_sort"] == 99]["annual_income"].unique()
if len(sem_mapeamento) > 0:
    print(f"  ⚠ Faixas sem mapeamento: {sem_mapeamento}")
else:
    print("  ✓ Todas as faixas mapeadas")

print(dim_customer[["annual_income", "income_sort"]].drop_duplicates().sort_values("income_sort"))
# ═══════════════════════════════════════════════════════════════
# fact_sales  (empilha 2015 + 2016 + 2017)
# ═══════════════════════════════════════════════════════════════
print("Processando fact_sales...")

sales = pd.concat([
    read("AdventureWorks_Sales_2015.csv"),
    read("AdventureWorks_Sales_2016.csv"),
    read("AdventureWorks_Sales_2017.csv"),
], ignore_index=True)

sales["OrderDate"] = pd.to_datetime(sales["OrderDate"])
sales["StockDate"] = pd.to_datetime(sales["StockDate"])

fact_sales = pd.DataFrame({
    "order_number"    : sales["OrderNumber"],
    "line_item"       : sales["OrderLineItem"],
    "order_date_key"  : to_date_key(sales["OrderDate"]),
    "stock_date_key"  : to_date_key(sales["StockDate"]),
    "customer_key"    : sales["CustomerKey"],
    "product_key"     : sales["ProductKey"],
    "territory_key"   : sales["TerritoryKey"],
    "quantity"        : sales["OrderQuantity"],
})

fact_sales.to_sql("fact_sales", engine, if_exists="replace", index=False)
print(f"  ✓ {len(fact_sales)} linhas")

# ═══════════════════════════════════════════════════════════════
# fact_returns
# ═══════════════════════════════════════════════════════════════
print("Processando fact_returns...")

ret = read("AdventureWorks_Returns.csv")
ret["ReturnDate"] = pd.to_datetime(ret["ReturnDate"])

fact_returns = pd.DataFrame({
    "return_date_key" : to_date_key(ret["ReturnDate"]),
    "territory_key"   : ret["TerritoryKey"],
    "product_key"     : ret["ProductKey"],
    "return_quantity" : ret["ReturnQuantity"],
})

fact_returns.to_sql("fact_returns", engine, if_exists="replace", index=False)
print(f"  ✓ {len(fact_returns)} linhas")

# ═══════════════════════════════════════════════════════════════
# Validação rápida
# ═══════════════════════════════════════════════════════════════
print("\n── Validação ──")
for table in ["dim_calendar", "dim_territory", "dim_product",
              "dim_customer", "fact_sales", "fact_returns"]:
    count = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", engine).iloc[0,0]
    print(f"  {table}: {count} linhas")

print("\n✓ ETL concluído. Banco salvo em:", DB_PATH)
# %%
