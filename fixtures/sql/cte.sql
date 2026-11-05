WITH totals AS (
    SELECT o.customer_id, SUM(o.amount) AS total_amount
    FROM orders o
    GROUP BY o.customer_id
)
SELECT t.customer_id, t.total_amount
FROM totals t
WHERE t.total_amount > 100;
