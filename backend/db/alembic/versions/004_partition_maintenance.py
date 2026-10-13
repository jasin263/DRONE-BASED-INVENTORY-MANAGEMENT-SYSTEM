"""Make monthly partition maintenance safe when the default partition is populated."""

from alembic import op


revision = "004_partition_maintenance"
down_revision = "003_partition_scan_event"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP FUNCTION IF EXISTS ensure_scan_event_partitions(INTEGER);
        CREATE OR REPLACE FUNCTION ensure_scan_event_partitions(months_ahead INTEGER DEFAULT 3)
        RETURNS JSONB LANGUAGE plpgsql AS $$
        DECLARE
            month_start DATE := date_trunc('month', CURRENT_DATE)::date;
            range_start DATE;
            range_end DATE;
            partition_name TEXT;
            created_partitions JSONB := '[]'::jsonb;
            default_rows BIGINT;
        BEGIN
            SELECT count(*) INTO default_rows FROM scan_event_default;
            IF default_rows > 0 THEN
                RAISE WARNING 'scan_event_default contains % rows before maintenance', default_rows;
                ALTER TABLE scan_event DETACH PARTITION scan_event_default;
            END IF;

            FOR i IN 0..GREATEST(months_ahead - 1, 0) LOOP
                range_start := month_start + (i || ' month')::interval;
                range_end := month_start + ((i + 1) || ' month')::interval;
                partition_name := format('scan_event_%s', to_char(range_start, 'YYYY_MM'));
                IF to_regclass(partition_name) IS NULL THEN
                    EXECUTE format(
                        'CREATE TABLE %I PARTITION OF scan_event FOR VALUES FROM (%L) TO (%L)',
                        partition_name, range_start, range_end
                    );
                    created_partitions := created_partitions || to_jsonb(partition_name);
                END IF;

                IF default_rows > 0 THEN
                    EXECUTE format(
                        'INSERT INTO %I SELECT * FROM scan_event_default WHERE event_time >= $1 AND event_time < $2',
                        partition_name
                    ) USING range_start, range_end;
                    EXECUTE
                        'DELETE FROM scan_event_default WHERE event_time >= $1 AND event_time < $2'
                        USING range_start, range_end;
                END IF;
            END LOOP;

            IF default_rows > 0 THEN
                ALTER TABLE scan_event ATTACH PARTITION scan_event_default DEFAULT;
                SELECT count(*) INTO default_rows FROM scan_event_default;
                IF default_rows > 0 THEN
                    RAISE WARNING 'scan_event_default retains % rows outside the maintenance horizon', default_rows;
                END IF;
            END IF;

            RETURN jsonb_build_object(
                'created_partitions', created_partitions,
                'default_rows_remaining', COALESCE(default_rows, 0)
            );
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP FUNCTION IF EXISTS ensure_scan_event_partitions(INTEGER);
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
        """
    )
