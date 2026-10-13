"""Partition scan events by event_time and maintain future monthly partitions."""

from alembic import op


revision = "003_partition_scan_event"
down_revision = "002_gate0_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE scan_item ADD COLUMN scan_event_time TIMESTAMPTZ;
        UPDATE scan_item si
        SET scan_event_time = se.timestamp
        FROM scan_event se
        WHERE se.id = si.scan_event_id;
        ALTER TABLE scan_item ALTER COLUMN scan_event_time SET NOT NULL;
        ALTER TABLE scan_item DROP CONSTRAINT IF EXISTS scan_item_scan_event_id_fkey;
        ALTER TABLE scan_event RENAME TO scan_event_legacy;
        ALTER TABLE scan_event_legacy RENAME COLUMN timestamp TO event_time;
        ALTER INDEX scan_event_pkey RENAME TO scan_event_legacy_pkey;
        ALTER INDEX scan_event_event_id_key RENAME TO scan_event_legacy_event_id_key;
        ALTER INDEX ix_scan_event_data_source RENAME TO scan_event_legacy_data_source;
        ALTER INDEX ix_scan_event_mission_timestamp RENAME TO scan_event_legacy_mission_timestamp;
        CREATE TABLE scan_event (
            id INTEGER NOT NULL,
            event_id UUID NOT NULL,
            mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
            drone_id INTEGER REFERENCES drone(id) ON DELETE SET NULL,
            event_time TIMESTAMPTZ NOT NULL,
            read_type readtype NOT NULL,
            symbology VARCHAR(50),
            value VARCHAR(255) NOT NULL,
            confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            location_tag VARCHAR(100),
            position_x DOUBLE PRECISION,
            position_y DOUBLE PRECISION,
            position_z DOUBLE PRECISION,
            position_frame VARCHAR(50),
            image_ref VARCHAR(500),
            bbox_x1 DOUBLE PRECISION,
            bbox_y1 DOUBLE PRECISION,
            bbox_x2 DOUBLE PRECISION,
            bbox_y2 DOUBLE PRECISION,
            event_status eventstatus NOT NULL DEFAULT 'active',
            data_source VARCHAR(20) NOT NULL DEFAULT 'production'
                CONSTRAINT ck_scan_event_data_source
                CHECK (data_source IN ('abid', 'barcode_ref', 'synthetic', 'production')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, event_time)
        ) PARTITION BY RANGE (event_time);
        CREATE INDEX ix_scan_event_event_id ON scan_event (event_id);
        CREATE INDEX ix_scan_event_mission_event_time ON scan_event (mission_id, event_time);
        CREATE INDEX ix_scan_event_data_source ON scan_event (data_source);
        CREATE TABLE scan_event_default PARTITION OF scan_event DEFAULT;
        CREATE OR REPLACE FUNCTION ensure_scan_event_partitions(months_ahead INTEGER DEFAULT 3)
        RETURNS VOID LANGUAGE plpgsql AS $$
        DECLARE
            month_start DATE := date_trunc('month', CURRENT_DATE)::date;
            i INTEGER;
            partition_name TEXT;
        BEGIN
            FOR i IN 0..GREATEST(months_ahead - 1, 0) LOOP
                partition_name := format(
                    'scan_event_%s',
                    to_char(month_start + (i || ' month')::interval, 'YYYY_MM')
                );
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF scan_event FOR VALUES FROM (%L) TO (%L)',
                    partition_name,
                    month_start + (i || ' month')::interval,
                    month_start + ((i + 1) || ' month')::interval
                );
            END LOOP;
        END;
        $$;
        SELECT ensure_scan_event_partitions(3);
        INSERT INTO scan_event (
            id, event_id, mission_id, drone_id, event_time, read_type,
            symbology, value, confidence, location_tag, position_x, position_y,
            position_z, position_frame, image_ref, bbox_x1, bbox_y1, bbox_x2,
            bbox_y2, event_status, data_source, created_at
        )
        SELECT id, event_id, mission_id, drone_id, event_time, read_type,
               symbology, value, confidence, location_tag, position_x, position_y,
               position_z, position_frame, image_ref, bbox_x1, bbox_y1, bbox_x2,
               bbox_y2, event_status, data_source, created_at
        FROM scan_event_legacy;
        ALTER TABLE scan_item
        ADD CONSTRAINT scan_item_scan_event_fk
        FOREIGN KEY (scan_event_id, scan_event_time)
        REFERENCES scan_event (id, event_time) ON DELETE CASCADE;
        DROP TABLE scan_event_legacy;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS ensure_scan_event_partitions(INTEGER)")
    op.execute("ALTER TABLE scan_item DROP CONSTRAINT IF EXISTS scan_item_scan_event_fk")
    op.execute(
        """
        CREATE TABLE scan_event_legacy (
            id INTEGER PRIMARY KEY,
            event_id UUID NOT NULL UNIQUE,
            mission_id INTEGER NOT NULL REFERENCES mission(id) ON DELETE CASCADE,
            drone_id INTEGER REFERENCES drone(id) ON DELETE SET NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            read_type readtype NOT NULL,
            symbology VARCHAR(50),
            value VARCHAR(255) NOT NULL,
            confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            location_tag VARCHAR(100),
            position_x DOUBLE PRECISION,
            position_y DOUBLE PRECISION,
            position_z DOUBLE PRECISION,
            position_frame VARCHAR(50),
            image_ref VARCHAR(500),
            bbox_x1 DOUBLE PRECISION,
            bbox_y1 DOUBLE PRECISION,
            bbox_x2 DOUBLE PRECISION,
            bbox_y2 DOUBLE PRECISION,
            event_status eventstatus NOT NULL DEFAULT 'active',
            data_source VARCHAR(20) NOT NULL DEFAULT 'production'
                CONSTRAINT ck_scan_event_data_source
                CHECK (data_source IN ('abid', 'barcode_ref', 'synthetic', 'production')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        INSERT INTO scan_event_legacy (
            id, event_id, mission_id, drone_id, timestamp, read_type, symbology,
            value, confidence, location_tag, position_x, position_y, position_z,
            position_frame, image_ref, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
            event_status, data_source, created_at
        )
        SELECT id, event_id, mission_id, drone_id, event_time, read_type,
               symbology, value, confidence, location_tag, position_x, position_y,
               position_z, position_frame, image_ref, bbox_x1, bbox_y1, bbox_x2,
               bbox_y2, event_status, data_source, created_at
        FROM scan_event;
        DROP TABLE scan_event CASCADE;
        ALTER TABLE scan_event_legacy RENAME TO scan_event;
        CREATE INDEX ix_scan_event_data_source ON scan_event (data_source);
        CREATE INDEX ix_scan_event_mission_timestamp ON scan_event (mission_id, timestamp);
        ALTER TABLE scan_item DROP COLUMN IF EXISTS scan_event_time;
        ALTER TABLE scan_item ADD CONSTRAINT scan_item_scan_event_id_fkey
            FOREIGN KEY (scan_event_id) REFERENCES scan_event(id) ON DELETE CASCADE;
        """
    )
