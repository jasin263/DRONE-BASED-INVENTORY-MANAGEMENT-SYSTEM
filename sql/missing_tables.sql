CREATE TABLE IF NOT EXISTS app_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'Viewer',
    site_id INTEGER REFERENCES site(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_role (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, role)
);

CREATE TABLE IF NOT EXISTS discrepancy_case (
    id SERIAL PRIMARY KEY,
    mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
    sku_id INTEGER REFERENCES sku(id) ON DELETE SET NULL,
    location_id INTEGER REFERENCES "location"(id) ON DELETE SET NULL,
    lot VARCHAR(100),
    outcome VARCHAR(50) NOT NULL,
    variance_value INTEGER,
    threshold_value FLOAT,
    status VARCHAR(50) DEFAULT 'open',
    assigned_to INTEGER REFERENCES app_user(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_comment (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES discrepancy_case(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES app_user(id) ON DELETE SET NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS adjustment (
    id SERIAL PRIMARY KEY,
    case_id INTEGER REFERENCES discrepancy_case(id) ON DELETE SET NULL,
    sku_id INTEGER REFERENCES sku(id) ON DELETE SET NULL,
    location_id INTEGER REFERENCES "location"(id) ON DELETE SET NULL,
    adjustment_type VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    reason VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    posted_to_erp BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS setting (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value JSON NOT NULL,
    description VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values JSON,
    new_values JSON,
    user_id INTEGER REFERENCES app_user(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);