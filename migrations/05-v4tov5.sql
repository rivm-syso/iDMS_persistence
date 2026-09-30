
CREATE TABLE IF NOT EXISTS public.version (
    version INTEGER NOT NULL,
    PRIMARY KEY (version)
);
GRANT SELECT ON TABLE version TO projects;

DO $$
BEGIN
IF EXISTS (SELECT 1 FROM version WHERE version=4) THEN

    ALTER TABLE referencedata ADD COLUMN category varchar(255);

    UPDATE version SET version=5;
END IF;
END $$;
