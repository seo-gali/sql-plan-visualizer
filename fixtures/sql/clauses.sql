SELECT DISTINCT c.name
FROM customers c
WHERE c.active = true
ORDER BY c.name
LIMIT 10 OFFSET 2;
