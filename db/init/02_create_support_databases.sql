-- Development-only databases. Alembic remains the only DRIMS schema source.
SELECT 'CREATE DATABASE keycloak OWNER ' || current_user
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec
SELECT 'CREATE DATABASE drims_test OWNER ' || current_user
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'drims_test')\gexec
