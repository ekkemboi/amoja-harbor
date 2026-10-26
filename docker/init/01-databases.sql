-- Runs once, on first initialisation of the volume.
-- POSTGRES_DB already created harbor_dev; tests get their own database so a
-- stray pytest run can never touch development data.
create database harbor_test;
