SELECT s.customer_id
FROM (SELECT o.customer_id FROM orders o) s
WHERE EXISTS (SELECT 1 FROM customers c WHERE c.id = s.customer_id);
