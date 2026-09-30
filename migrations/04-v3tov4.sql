
CREATE TABLE IF NOT EXISTS public.version (
    version INTEGER NOT NULL,
    PRIMARY KEY (version)
);
GRANT SELECT ON TABLE version TO projects;

DO $$
BEGIN
IF EXISTS (SELECT 1 FROM version WHERE version=3) THEN

    ALTER TABLE projects ADD COLUMN uuid uuid DEFAULT gen_random_uuid();

    UPDATE version SET version=4;
END IF;
END $$;