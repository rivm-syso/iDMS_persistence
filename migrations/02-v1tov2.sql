
CREATE TABLE IF NOT EXISTS public.version (
    version INTEGER NOT NULL,
    PRIMARY KEY (version)
);
GRANT SELECT ON TABLE version TO projects;

DO $$
BEGIN
IF EXISTS (SELECT 1 FROM version WHERE version=1) THEN

    ALTER TABLE IF EXISTS ONLY public.contacts DROP CONSTRAINT IF EXISTS contacts_project_id_fkey;
    ALTER TABLE contacts RENAME COLUMN project_id TO entity_id;
    ALTER TABLE contacts ADD COLUMN entity_type character varying(50);
    
    UPDATE contacts SET entity_type = 'Project';
    ALTER TABLE contacts ALTER COLUMN entity_type SET NOT NULL;

    ALTER TABLE IF EXISTS ONLY public.notifications DROP CONSTRAINT IF EXISTS notifications_projectid_fkey;
    ALTER TABLE notifications RENAME COLUMN projectid TO entity_id;
    ALTER TABLE notifications ADD COLUMN entity_type character varying(50);

    UPDATE notifications SET entity_type = 'Project';
    ALTER TABLE notifications ALTER COLUMN entity_type SET NOT NULL;

    UPDATE version SET version=2;
END IF;
END $$;