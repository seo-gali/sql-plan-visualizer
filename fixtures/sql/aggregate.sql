SELECT o.customer_id, SUM(o.amount) AS total_amount, COUNT(*) AS order_count
FROM orders AS o
GROUP BY o.customer_id
HAVING SUM(o.amount) > 1000;
