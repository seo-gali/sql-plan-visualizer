SELECT c.id, o.id AS order_id, o.amount
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.id
WHERE o.amount > 100;
