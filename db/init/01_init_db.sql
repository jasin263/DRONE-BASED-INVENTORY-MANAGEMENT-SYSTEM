#!/usr/bin/env psql
-- Create the drims user and database
CREATE USER drims WITH PASSWORD 'drims_password';
CREATE DATABASE drims OWNER drims;

-- Grant permissions for Keycloak
CREATE USER keycloak WITH PASSWORD 'keycloak_password';
GRANT ALL PRIVILEGES ON DATABASE drims TO keycloak;
GRANT ALL PRIVILEGES ON SCHEMA public TO keycloak;