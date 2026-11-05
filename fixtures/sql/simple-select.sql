SELECT c.id, c.name AS customer_name
FROM customers AS c
WHERE c.active = true;
