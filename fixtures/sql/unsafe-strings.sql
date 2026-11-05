SELECT '<script>window.sqlpviInjected = true</script></script><script>alert(1)</script>' AS "한글 & <>"
FROM customers c
WHERE c.name = 'Unicode 한글 < > & " '' ';
