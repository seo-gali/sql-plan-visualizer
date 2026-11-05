-- Isolated local test container only; no real credentials or production data.
CREATE ROLE sqlpvi_reader LOGIN;
CREATE TABLE customers (id integer PRIMARY KEY, name text NOT NULL, active boolean NOT NULL);
CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer REFERENCES customers(id), amount numeric NOT NULL);
INSERT INTO customers SELECT n, 'Customer ' || n, n % 2 = 0 FROM generate_series(1, 500) n;
INSERT INTO orders SELECT n, n % 500 + 1, (n % 1000)::numeric FROM generate_series(1, 10000) n;
CREATE INDEX orders_customer_idx ON orders(customer_id);
ANALYZE;
GRANT CONNECT ON DATABASE sqlpvi TO sqlpvi_reader;
GRANT USAGE ON SCHEMA public TO sqlpvi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sqlpvi_reader;
ALTER ROLE sqlpvi_reader SET default_transaction_read_only = on;
