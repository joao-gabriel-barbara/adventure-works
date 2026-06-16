CREATE VIEW IF NOT EXISTS vw_sales_summary AS
WITH base AS (
    SELECT
        s.order_number,
        s.line_item,
        s.quantity,
        p.product_price,
        p.product_cost,
        p.category_name,
        p.subcategory_name,
        p.product_name,
        c.year,
        c.quarter,
        c.month,
        c.month_name,
        t.region,
        t.country,
        t.continent,
        cu.occupation,
        cu.annual_income,
        cu.gender,
        cu.education_level,
        s.quantity * p.product_price                    AS revenue,
        s.quantity * p.product_cost                     AS cost,
        (s.quantity * p.product_price)
        - (s.quantity * p.product_cost)                 AS gross_profit
    FROM fact_sales s
    JOIN dim_product  p  ON s.product_key    = p.product_key
    JOIN dim_calendar c  ON s.order_date_key = c.date_key
    JOIN dim_territory t ON s.territory_key  = t.territory_key
    JOIN dim_customer cu ON s.customer_key   = cu.customer_key
)
SELECT
    *,
    ROUND(gross_profit / NULLIF(revenue, 0) * 100, 2)  AS gross_margin_pct
FROM base;

SELECT COUNT(*) FROM vw_sales_summary;

SELECT * FROM vw_sales_summary LIMIT 3;