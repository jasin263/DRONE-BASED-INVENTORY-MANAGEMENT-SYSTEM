CREATE TABLE IF NOT EXISTS site (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drone (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(100) NOT NULL UNIQUE,
    model VARCHAR(100),
    firmware_version VARCHAR(50),
    site_id INTEGER NOT NULL REFERENCES site(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'IDLE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mission (
    id SERIAL PRIMARY KEY,
    mission_id VARCHAR(100) NOT NULL UNIQUE,
    drone_id INTEGER REFERENCES drone(id) ON DELETE SET NULL,
    site_id INTEGER NOT NULL REFERENCES site(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'RECEIVING',
    coverage_pct FLOAT DEFAULT 0.0,
    total_scans INTEGER DEFAULT 0,
    total_bins_visited INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(mission_id)
);

CREATE TABLE IF NOT EXISTS "location" (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES site(id) ON DELETE CASCADE,
    zone_code VARCHAR(100),
    aisle_code VARCHAR(50),
    rack_id VARCHAR(50),
    level_code VARCHAR(50),
    bin_code VARCHAR(50) NOT NULL,
    label_code VARCHAR(50),
    polygon TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(site_id, bin_code)
);

CREATE TABLE IF NOT EXISTS sku (
    id SERIAL PRIMARY KEY,
    gtin VARCHAR(50) UNIQUE,
    epc_prefix VARCHAR(50),
    description VARCHAR(500),
    uom VARCHAR(50) DEFAULT 'each',
    unit_value FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(gtin)
);

CREATE TABLE IF NOT EXISTS raw_payload (
    id SERIAL PRIMARY KEY,
    mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    payload_json JSON NOT NULL,
    schema_version VARCHAR(50) NOT NULL,
    stored_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scan_event (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL UNIQUE,
    mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
    drone_id INTEGER REFERENCES drone(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    read_type VARCHAR(20) NOT NULL,
    symbology VARCHAR(50),
    value VARCHAR(255) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    location_tag VARCHAR(100),
    position_x FLOAT,
    position_y FLOAT,
    position_z FLOAT,
    position_frame VARCHAR(50),
    image_ref VARCHAR(500),
    bbox_x1 FLOAT,
    bbox_y1 FLOAT,
    bbox_x2 FLOAT,
    bbox_y2 FLOAT,
    event_status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scan_item (
    id SERIAL PRIMARY KEY,
    scan_event_id INTEGER NOT NULL REFERENCES scan_event(id) ON DELETE CASCADE,
    sku_id INTEGER REFERENCES sku(id) ON DELETE SET NULL,
    lot VARCHAR(100),
    serial VARCHAR(100),
    expiry DATE,
    location_id INTEGER REFERENCES "location"(id) ON DELETE SET NULL,
    map_method VARCHAR(50) DEFAULT 'label_fallback',
    is_duplicate BOOLEAN DEFAULT FALSE,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bin_count (
    id SERIAL PRIMARY KEY,
    mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES "location"(id) ON DELETE CASCADE,
    sku_id INTEGER REFERENCES sku(id) ON DELETE SET NULL,
    lot VARCHAR(100),
    serial VARCHAR(100),
    count INTEGER DEFAULT 1,
    confidence_score FLOAT DEFAULT 0.0,
    method VARCHAR(50) DEFAULT 'label',
    image_coverage_ratio FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(mission_id, location_id, sku_id, lot, serial)
);

CREATE TABLE IF NOT EXISTS book_snapshot (
    id SERIAL PRIMARY KEY,
    mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
    sku_id INTEGER REFERENCES sku(id) ON DELETE SET NULL,
    location_id INTEGER REFERENCES "location"(id) ON DELETE SET NULL,
    lot VARCHAR(100),
    booked_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(mission_id, sku_id, location_id, lot)
);

CREATE TABLE IF NOT EXISTS recon_result (
    id SERIAL PRIMARY KEY,
    mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
    sku_id INTEGER REFERENCES sku(id) ON DELETE SET NULL,
    location_id INTEGER REFERENCES "location"(id) ON DELETE SET NULL,
    lot VARCHAR(100),
    outcome VARCHAR(50) NOT NULL,
    variance INTEGER,
    confidence FLOAT,
    details JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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