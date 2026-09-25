-- Create listmonk database
-- Run this manually on the PostgreSQL server before starting Listmonk:
-- docker exec -i prod_postgres psql -U mond -d monddb < init-listmonk-db.sql

CREATE DATABASE listmonk_db OWNER mond;
