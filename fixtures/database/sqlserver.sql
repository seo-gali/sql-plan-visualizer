-- Public credentials and synthetic data for the loopback fixture only.
-- Create missing objects; never delete or reset an existing database.
IF DB_ID('sqlpvi') IS NULL CREATE DATABASE sqlpvi;
GO
USE sqlpvi;
GO
SET XACT_ABORT ON;
BEGIN TRANSACTION;
IF OBJECT_ID('dbo.customers', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.customers (
        id int NOT NULL CONSTRAINT PK_customers PRIMARY KEY,
        name nvarchar(100) NOT NULL,
        active bit NOT NULL
    );
    WITH n AS (
        SELECT 1 AS id UNION ALL SELECT id + 1 FROM n WHERE id < 500
    )
    INSERT dbo.customers SELECT id, CONCAT('Customer ', id), id % 2 FROM n OPTION (MAXRECURSION 0);
END;
IF OBJECT_ID('dbo.orders', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.orders (
        id int NOT NULL CONSTRAINT PK_orders PRIMARY KEY,
        customer_id int REFERENCES dbo.customers(id),
        amount decimal(12,2) NOT NULL
    );
    WITH n AS (
        SELECT 1 AS id UNION ALL SELECT id + 1 FROM n WHERE id < 10000
    )
    INSERT dbo.orders SELECT id, id % 500 + 1, id % 1000 FROM n OPTION (MAXRECURSION 0);
    CREATE INDEX orders_customer_idx ON dbo.orders(customer_id);
END;
COMMIT;
GO
IF SUSER_ID('sqlpvi_reader') IS NULL
    CREATE LOGIN sqlpvi_reader WITH PASSWORD = 'Sqlpvi-Fixture-2026!';
IF USER_ID('sqlpvi_reader') IS NULL CREATE USER sqlpvi_reader FOR LOGIN sqlpvi_reader;
GRANT SHOWPLAN TO sqlpvi_reader;
GRANT SELECT ON SCHEMA::dbo TO sqlpvi_reader;
GO
IF SUSER_ID('sqlpvi_writer') IS NULL
    CREATE LOGIN sqlpvi_writer WITH PASSWORD = 'Sqlpvi-Fixture-2026!';
IF USER_ID('sqlpvi_writer') IS NULL CREATE USER sqlpvi_writer FOR LOGIN sqlpvi_writer;
GRANT SHOWPLAN TO sqlpvi_writer;
GRANT SELECT, UPDATE ON SCHEMA::dbo TO sqlpvi_writer;
GO
IF SUSER_ID('sqlpvi_column_writer') IS NULL
    CREATE LOGIN sqlpvi_column_writer WITH PASSWORD = 'Sqlpvi-Fixture-2026!';
IF USER_ID('sqlpvi_column_writer') IS NULL CREATE USER sqlpvi_column_writer FOR LOGIN sqlpvi_column_writer;
GRANT SHOWPLAN TO sqlpvi_column_writer;
GRANT SELECT ON SCHEMA::dbo TO sqlpvi_column_writer;
GRANT UPDATE (active) ON dbo.customers TO sqlpvi_column_writer;
GO
IF SUSER_ID('sqlpvi_no_showplan') IS NULL
    CREATE LOGIN sqlpvi_no_showplan WITH PASSWORD = 'Sqlpvi-Fixture-2026!';
IF USER_ID('sqlpvi_no_showplan') IS NULL CREATE USER sqlpvi_no_showplan FOR LOGIN sqlpvi_no_showplan;
GRANT SELECT ON SCHEMA::dbo TO sqlpvi_no_showplan;
GO
IF SUSER_ID('sqlpvi_grantable') IS NULL
    CREATE LOGIN sqlpvi_grantable WITH PASSWORD = 'Sqlpvi-Fixture-2026!';
IF USER_ID('sqlpvi_grantable') IS NULL CREATE USER sqlpvi_grantable FOR LOGIN sqlpvi_grantable;
GRANT SHOWPLAN TO sqlpvi_grantable;
GRANT SELECT ON SCHEMA::dbo TO sqlpvi_grantable WITH GRANT OPTION;
GO
