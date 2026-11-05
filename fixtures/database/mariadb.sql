-- Isolated loopback test container only.
CREATE USER 'sqlpvi_reader'@'%' IDENTIFIED BY '';
CREATE TABLE customers (id integer PRIMARY KEY, name varchar(100) NOT NULL, active boolean NOT NULL);
CREATE TABLE orders (id integer PRIMARY KEY, customer_id integer, amount decimal(12,2) NOT NULL, INDEX orders_customer_idx(customer_id));
INSERT INTO customers SELECT seq, CONCAT('Customer ', seq), MOD(seq,2)=0 FROM seq_1_to_500;
INSERT INTO orders SELECT seq, MOD(seq,500)+1, MOD(seq,1000) FROM seq_1_to_10000;
ANALYZE TABLE customers, orders;
GRANT SELECT ON sqlpvi.* TO 'sqlpvi_reader'@'%';
CREATE USER 'sqlpvi_schema_writer'@'%' IDENTIFIED BY '';
GRANT SELECT, UPDATE ON sqlpvi.* TO 'sqlpvi_schema_writer'@'%';
CREATE USER 'sqlpvi_table_writer'@'%' IDENTIFIED BY '';
GRANT SELECT ON sqlpvi.* TO 'sqlpvi_table_writer'@'%';
GRANT UPDATE ON sqlpvi.customers TO 'sqlpvi_table_writer'@'%';
CREATE USER 'sqlpvi_column_writer'@'%' IDENTIFIED BY '';
GRANT SELECT ON sqlpvi.* TO 'sqlpvi_column_writer'@'%';
GRANT UPDATE (active) ON sqlpvi.customers TO 'sqlpvi_column_writer'@'%';
CREATE USER 'sqlpvi_grantable'@'%' IDENTIFIED BY '';
GRANT SELECT ON sqlpvi.* TO 'sqlpvi_grantable'@'%' WITH GRANT OPTION;
