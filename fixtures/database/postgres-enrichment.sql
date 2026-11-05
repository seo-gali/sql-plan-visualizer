CREATE SCHEMA alternate;
CREATE TABLE alternate.customers (id integer PRIMARY KEY, name text);
INSERT INTO alternate.customers VALUES (1, 'Alternate fixture');
CREATE TABLE public.restricted_fixture (id integer);
CREATE TABLE public.unanalyzed_fixture (id integer) WITH (autovacuum_enabled = false);
GRANT USAGE ON SCHEMA alternate TO sqlpvi_reader;
GRANT SELECT ON alternate.customers, public.unanalyzed_fixture TO sqlpvi_reader;
ANALYZE alternate.customers;
