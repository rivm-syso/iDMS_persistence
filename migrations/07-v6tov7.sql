
CREATE TABLE IF NOT EXISTS public.version (
    version INTEGER NOT NULL,
    PRIMARY KEY (version)
);
GRANT SELECT ON TABLE version TO projects;

DO $$
BEGIN
IF EXISTS (SELECT 1 FROM version WHERE version=6) THEN

    ALTER TABLE processes2 ADD COLUMN compatible_clusters JSON;
    ALTER TABLE processes2 ADD COLUMN required_memory INTEGER DEFAULT 0;

    UPDATE version SET version=7;
END IF;
END $$;
