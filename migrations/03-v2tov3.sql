
CREATE TABLE IF NOT EXISTS public.version (
    version INTEGER NOT NULL,
    PRIMARY KEY (version)
);
GRANT SELECT ON TABLE version TO projects;

DO $$
BEGIN
IF EXISTS (SELECT 1 FROM version WHERE version=2) THEN

    ALTER TABLE projects ADD COLUMN last_maintenance timestamp without time zone;

    UPDATE version SET version=3;
END IF;
END $$;