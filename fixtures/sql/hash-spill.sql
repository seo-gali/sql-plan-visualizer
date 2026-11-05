SELECT SUM(o.amount + p.amount) AS total_amount
FROM orders AS o
JOIN orders AS p ON o.customer_id = p.customer_id;
