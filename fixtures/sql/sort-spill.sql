SELECT o.id, o.amount, c.id AS customer_id
FROM orders AS o
CROSS JOIN customers AS c
WHERE c.id <= 10
ORDER BY o.amount, o.id, c.id;
