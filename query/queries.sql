WITH tb_revenue_anual AS (

SELECT
    c.year,
    p.category_name,
    SUM(s.quantity * p.product_price)        AS total_revenue,
    SUM(s.quantity)                          AS total_units,
    ROUND(
        SUM(s.quantity * p.product_price)
        / SUM(s.quantity), 2
    )                                        AS avg_ticket
FROM fact_sales s
JOIN dim_calendar c  ON s.order_date_key = c.date_key
JOIN dim_product  p  ON s.product_key    = p.product_key
GROUP BY c.year, p.category_name
ORDER BY c.year, total_revenue DESC

),

tb_venda_inicial_final AS (

SELECT
    MIN(full_date) AS primeira_venda,
    MAX(full_date) AS ultima_venda,
    COUNT(DISTINCT order_number) AS total_pedidos
FROM fact_sales s
JOIN dim_calendar c ON s.order_date_key = c.date_key

),

tb_monthly_revenue AS (
    SELECT
        c.year,
        c.month,
        c.month_name,
        ROUND(SUM(s.quantity * p.product_price), 2) AS revenue
    FROM fact_sales s
    JOIN dim_calendar c ON s.order_date_key = c.date_key
    JOIN dim_product  p ON s.product_key    = p.product_key
    GROUP BY c.year, c.month, c.month_name
),

tb_growth_pct AS (
SELECT
    year,
    month,
    month_name,
    revenue,
    LAG(revenue) OVER (ORDER BY year, month)  AS prev_month_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY year, month))
        / LAG(revenue) OVER (ORDER BY year, month) * 100
    , 2)                                       AS mom_growth_pct
FROM tb_monthly_revenue
ORDER BY year, month

),

tb_search_july AS (
SELECT
    c.year,
    c.month,
    p.category_name,
    ROUND(SUM(s.quantity * p.product_price), 2) AS revenue
FROM fact_sales s
JOIN dim_calendar c ON s.order_date_key = c.date_key
JOIN dim_product  p ON s.product_key    = p.product_key
WHERE c.year = 2016 AND c.month BETWEEN 6 AND 8
GROUP BY c.year, c.month, p.category_name
ORDER BY c.month, revenue DESC

),

tb_product_revenue AS (
    SELECT
        p.product_name,
        p.category_name,
        p.subcategory_name,
        ROUND(SUM(s.quantity * p.product_price), 2) AS total_revenue,
        SUM(s.quantity)                              AS total_units
    FROM fact_sales s
    JOIN dim_product p ON s.product_key = p.product_key
    GROUP BY p.product_name, p.category_name, p.subcategory_name
),

tb_top_products AS(

SELECT
    RANK() OVER (ORDER BY total_revenue DESC) AS ranking,
    product_name,
    category_name,
    subcategory_name,
    total_revenue,
    total_units,
    ROUND(total_revenue / SUM(total_revenue) OVER () * 100, 2) AS revenue_share_pct
FROM tb_product_revenue
ORDER BY ranking
LIMIT 10
),

sales_by_product AS (
    SELECT
        product_key,
        SUM(quantity) AS units_sold
    FROM fact_sales
    GROUP BY product_key
),

returns_by_product AS (
    SELECT
        product_key,
        SUM(return_quantity) AS units_returned
    FROM fact_returns
    GROUP BY product_key
)

SELECT
    p.category_name,
    p.subcategory_name,
    SUM(s.units_sold)                                    AS units_sold,
    COALESCE(SUM(r.units_returned), 0)                   AS units_returned,
    ROUND(
        COALESCE(SUM(r.units_returned), 0) * 100.0
        / SUM(s.units_sold)
    , 2)                                                 AS return_rate_pct
FROM sales_by_product s
JOIN dim_product p ON s.product_key = p.product_key
LEFT JOIN returns_by_product r ON s.product_key = r.product_key
GROUP BY p.category_name, p.subcategory_name
ORDER BY return_rate_pct DESC