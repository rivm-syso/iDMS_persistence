
CREATE TABLE IF NOT EXISTS public.version (
    version INTEGER NOT NULL,
    PRIMARY KEY (version)
);
GRANT SELECT ON TABLE version TO projects;

DO $$
BEGIN
IF EXISTS (SELECT 1 FROM version WHERE version=5) THEN

    ALTER TABLE projects ADD COLUMN department varchar(32);

    UPDATE version SET version=6;
END IF;
END $$;
