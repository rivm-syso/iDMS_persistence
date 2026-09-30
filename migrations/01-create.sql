--
-- PostgreSQL database dump
--

-- Dumped from database version 14.18
-- Dumped by pg_dump version 14.18

-- SET statement_timeout = 0;
-- SET lock_timeout = 0;
-- SET idle_in_transaction_session_timeout = 0;
-- SET client_encoding = 'UTF8';
-- SET standard_conforming_strings = on;
-- SELECT pg_catalog.set_config('search_path', '', false);
-- SET check_function_bodies = false;
-- SET xmloption = content;
-- SET client_min_messages = warning;
-- SET row_security = off;

CREATE TABLE IF NOT EXISTS public.version (
    version INTEGER NOT NULL,
    PRIMARY KEY (version)
);
GRANT ALL ON TABLE version TO projects;

-- Create version 1 tables
DO $$
BEGIN
IF NOT EXISTS (SELECT version FROM version) THEN

    ALTER TABLE IF EXISTS ONLY public.referencedataimport DROP CONSTRAINT IF EXISTS referencedataimport_referenceid_fkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion DROP CONSTRAINT IF EXISTS refdataversion_referenceid_fkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2processref DROP CONSTRAINT IF EXISTS refdataversion2processref_supersedingversionid_fkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2processref DROP CONSTRAINT IF EXISTS refdataversion2processref_processrefid_fkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2processref DROP CONSTRAINT IF EXISTS refdataversion2processref_processdefaultid_fkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2process DROP CONSTRAINT IF EXISTS refdataversion2process_referencedataversionid_fkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2process DROP CONSTRAINT IF EXISTS refdataversion2process_referencedataid_fkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2process DROP CONSTRAINT IF EXISTS refdataversion2process_processid_fkey;
    ALTER TABLE IF EXISTS ONLY public.processref DROP CONSTRAINT IF EXISTS processref_processid_fkey;
    ALTER TABLE IF EXISTS ONLY public.processref DROP CONSTRAINT IF EXISTS processref_processgroupid_fkey;
    ALTER TABLE IF EXISTS ONLY public.processgroup DROP CONSTRAINT IF EXISTS processgroup_projectid_fkey;
    ALTER TABLE IF EXISTS ONLY public.processes DROP CONSTRAINT IF EXISTS processes_projectid_fkey;
    ALTER TABLE IF EXISTS ONLY public.processdependencies DROP CONSTRAINT IF EXISTS processdependencies_processrefid_fkey;
    ALTER TABLE IF EXISTS ONLY public.processdependencies DROP CONSTRAINT IF EXISTS processdependencies_depends_on_fkey;
    ALTER TABLE IF EXISTS ONLY public.notifications DROP CONSTRAINT IF EXISTS notifications_projectid_fkey;
    ALTER TABLE IF EXISTS ONLY public.notifications DROP CONSTRAINT IF EXISTS notifications_contactid_fkey;
    ALTER TABLE IF EXISTS ONLY public.contacts DROP CONSTRAINT IF EXISTS contacts_project_id_fkey;
    ALTER TABLE IF EXISTS ONLY public.referencedataimport DROP CONSTRAINT IF EXISTS referencedataimport_referenceid_key;
    ALTER TABLE IF EXISTS ONLY public.referencedataimport DROP CONSTRAINT IF EXISTS referencedataimport_pkey;
    ALTER TABLE IF EXISTS ONLY public.referencedata DROP CONSTRAINT IF EXISTS referencedata_pkey;
    ALTER TABLE IF EXISTS ONLY public.referencedata DROP CONSTRAINT IF EXISTS referencedata_name_key;
    ALTER TABLE IF EXISTS ONLY public.refdataversion DROP CONSTRAINT IF EXISTS refdataversion_referenceid_version_uc;
    ALTER TABLE IF EXISTS ONLY public.refdataversion DROP CONSTRAINT IF EXISTS refdataversion_pkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion DROP CONSTRAINT IF EXISTS refdataversion_dataset_id_uc;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2processref DROP CONSTRAINT IF EXISTS refdataversion2processref_pkey;
    ALTER TABLE IF EXISTS ONLY public.refdataversion2process DROP CONSTRAINT IF EXISTS refdataversion2process_pkey;
    ALTER TABLE IF EXISTS ONLY public.projects DROP CONSTRAINT IF EXISTS projects_pkey;
    ALTER TABLE IF EXISTS ONLY public.processref DROP CONSTRAINT IF EXISTS processref_pkey;
    ALTER TABLE IF EXISTS ONLY public.processgroup DROP CONSTRAINT IF EXISTS processgroup_pkey;
    ALTER TABLE IF EXISTS ONLY public.processes DROP CONSTRAINT IF EXISTS processes_pkey;
    ALTER TABLE IF EXISTS ONLY public.processes2 DROP CONSTRAINT IF EXISTS processes2_pkey;
    ALTER TABLE IF EXISTS ONLY public.processdependencies DROP CONSTRAINT IF EXISTS processdependencies_pkey;
    ALTER TABLE IF EXISTS ONLY public.notifications DROP CONSTRAINT IF EXISTS notifications_pkey;
    ALTER TABLE IF EXISTS ONLY public.contacts DROP CONSTRAINT IF EXISTS contacts_pkey;
    ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;


    --
    -- Name: contacts; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.contacts (
        id integer NOT NULL,
        project_id integer NOT NULL,
        name character varying(128) NOT NULL,
        email character varying(128) NOT NULL,
        "primary" integer,
        notify_data integer DEFAULT 0,
        notify_pipeline integer DEFAULT 0,
        notify_errors integer DEFAULT 0,
        notify_config_changes integer DEFAULT 0
    );


    ALTER TABLE public.contacts OWNER TO projects;

    --
    -- Name: contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.contacts_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.contacts_id_seq OWNER TO projects;

    --
    -- Name: contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.contacts_id_seq OWNED BY public.contacts.id;


    --
    -- Name: notifications; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.notifications (
        id integer NOT NULL,
        messagetime timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
        contactid integer,
        projectid integer,
        author character varying(50),
        objecttype character varying(50),
        objectname character varying(50),
        message character varying(4000),
        sendtime timestamp without time zone
    );


    ALTER TABLE public.notifications OWNER TO projects;

    --
    -- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.notifications_id_seq
        AS integer
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.notifications_id_seq OWNER TO projects;

    --
    -- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


    --
    -- Name: processdependencies; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.processdependencies (
        id integer NOT NULL,
        creation_date timestamp without time zone DEFAULT now() NOT NULL,
        processrefid integer,
        dependency_type character varying(32),
        depends_on integer
    );


    ALTER TABLE public.processdependencies OWNER TO projects;

    --
    -- Name: processdependencies_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.processdependencies_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.processdependencies_id_seq OWNER TO projects;

    --
    -- Name: processdependencies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.processdependencies_id_seq OWNED BY public.processdependencies.id;


    --
    -- Name: processes; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.processes (
        id integer NOT NULL,
        creation_date timestamp without time zone DEFAULT now() NOT NULL,
        projectid integer,
        name character varying(64) NOT NULL,
        description character varying(250),
        output_prefix character varying(500),
        next_projectid integer,
        next_processid integer,
        distribution integer,
        modify_in_place integer,
        restartable integer,
        repo character varying(512),
        tag character varying(64),
        lsf_queue character varying(64),
        omit_staging integer,
        omit_bringonline integer,
        processid character varying(64),
        concurrency_limit integer DEFAULT 0,
        max_runtime integer DEFAULT 0
    );


    ALTER TABLE public.processes OWNER TO projects;

    --
    -- Name: processes2; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.processes2 (
        id integer NOT NULL,
        creation_date timestamp without time zone DEFAULT now() NOT NULL,
        name character varying(64) NOT NULL,
        description character varying(250),
        output_prefix character varying(500),
        distribution integer,
        modify_in_place integer,
        restartable integer,
        omit_staging integer,
        repo character varying(512),
        omit_bringonline integer,
        manager_group character varying(64),
        concurrency_limit integer DEFAULT 0,
        max_runtime integer DEFAULT 0
    );


    ALTER TABLE public.processes2 OWNER TO projects;

    --
    -- Name: processes2_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.processes2_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.processes2_id_seq OWNER TO projects;

    --
    -- Name: processes2_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.processes2_id_seq OWNED BY public.processes2.id;


    --
    -- Name: processes_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.processes_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.processes_id_seq OWNER TO projects;

    --
    -- Name: processes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.processes_id_seq OWNED BY public.processes.id;


    --
    -- Name: processgroup; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.processgroup (
        id integer NOT NULL,
        creation_date timestamp without time zone DEFAULT now() NOT NULL,
        projectid integer,
        name character varying(64),
        description character varying(250)
    );


    ALTER TABLE public.processgroup OWNER TO projects;

    --
    -- Name: processgroup_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.processgroup_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.processgroup_id_seq OWNER TO projects;

    --
    -- Name: processgroup_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.processgroup_id_seq OWNED BY public.processgroup.id;


    --
    -- Name: processref; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.processref (
        id integer NOT NULL,
        creation_date timestamp without time zone DEFAULT now() NOT NULL,
        processgroupid integer,
        processid integer,
        tag character varying(64),
        input integer,
        lsf_queue character varying(64),
        name character varying(64) NOT NULL
    );


    ALTER TABLE public.processref OWNER TO projects;

    --
    -- Name: processref_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.processref_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.processref_id_seq OWNER TO projects;

    --
    -- Name: processref_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.processref_id_seq OWNED BY public.processref.id;


    --
    -- Name: projects; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.projects (
        id integer NOT NULL,
        name character varying(128) NOT NULL,
        description character varying(250),
        creation_date timestamp without time zone DEFAULT now(),
        service_account character varying(32),
        default_collection character varying(250),
        user_group character varying(64),
        manager_group character varying(64),
        owner character varying(32),
        last_updated timestamp without time zone DEFAULT now(),
        last_verified timestamp without time zone,
        public integer DEFAULT 0,
        pipelines integer DEFAULT 1
    );


    ALTER TABLE public.projects OWNER TO projects;

    --
    -- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.projects_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.projects_id_seq OWNER TO projects;

    --
    -- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


    --
    -- Name: refdataversion; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.refdataversion (
        id integer NOT NULL,
        referenceid integer,
        creation_date timestamp without time zone DEFAULT now() NOT NULL,
        version integer NOT NULL,
        version_name character varying(100),
        dataset_id character varying(36) NOT NULL,
        is_valid integer DEFAULT 1
    );


    ALTER TABLE public.refdataversion OWNER TO projects;

    --
    -- Name: refdataversion2process; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.refdataversion2process (
        id integer NOT NULL,
        referencedataid integer,
        referencedataversionid integer,
        processid integer,
        creation_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
        label character varying(255) NOT NULL
    );


    ALTER TABLE public.refdataversion2process OWNER TO projects;

    --
    -- Name: refdataversion2process_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.refdataversion2process_id_seq
        AS integer
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.refdataversion2process_id_seq OWNER TO projects;

    --
    -- Name: refdataversion2process_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.refdataversion2process_id_seq OWNED BY public.refdataversion2process.id;


    --
    -- Name: refdataversion2processref; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.refdataversion2processref (
        id integer NOT NULL,
        processrefid integer,
        supersedingversionid integer,
        processdefaultid integer,
        creation_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
    );


    ALTER TABLE public.refdataversion2processref OWNER TO projects;

    --
    -- Name: refdataversion2processref_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.refdataversion2processref_id_seq
        AS integer
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.refdataversion2processref_id_seq OWNER TO projects;

    --
    -- Name: refdataversion2processref_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.refdataversion2processref_id_seq OWNED BY public.refdataversion2processref.id;


    --
    -- Name: refdataversion_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.refdataversion_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.refdataversion_id_seq OWNER TO projects;

    --
    -- Name: refdataversion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.refdataversion_id_seq OWNED BY public.refdataversion.id;


    --
    -- Name: referencedata; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.referencedata (
        id integer NOT NULL,
        creation_date timestamp without time zone DEFAULT now() NOT NULL,
        name character varying(100) NOT NULL,
        synchronize_command character varying(250),
        update_frequency integer,
        synchronization_frequency integer,
        owner character varying(64),
        is_active integer DEFAULT 1,
        repository character varying(512),
        tag character varying(100),
        description character varying,
        precheck_command character varying(250),
        execution_environment character varying(50)
    );


    ALTER TABLE public.referencedata OWNER TO projects;

    --
    -- Name: referencedata_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.referencedata_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.referencedata_id_seq OWNER TO projects;

    --
    -- Name: referencedata_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.referencedata_id_seq OWNED BY public.referencedata.id;


    --
    -- Name: referencedataimport; Type: TABLE; Schema: public; Owner: projects
    --

    CREATE TABLE IF NOT EXISTS public.referencedataimport (
        id integer NOT NULL,
        referenceid integer,
        last_task_pid character varying(64),
        current_version integer,
        dataset_id character varying(36),
        last_task_changed integer,
        last_task character varying(64),
        last_task_message character varying,
        error_count integer,
        last_updated integer,
        last_synchronized integer,
        last_prechecked integer
    );


    ALTER TABLE public.referencedataimport OWNER TO projects;

    --
    -- Name: referencedataimport_id_seq; Type: SEQUENCE; Schema: public; Owner: projects
    --

    CREATE SEQUENCE IF NOT EXISTS public.referencedataimport_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;


    ALTER TABLE public.referencedataimport_id_seq OWNER TO projects;

    --
    -- Name: referencedataimport_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: projects
    --

    ALTER SEQUENCE public.referencedataimport_id_seq OWNED BY public.referencedataimport.id;


    --
    -- Name: contacts id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.contacts ALTER COLUMN id SET DEFAULT nextval('public.contacts_id_seq'::regclass);


    --
    -- Name: notifications id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


    --
    -- Name: processdependencies id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processdependencies ALTER COLUMN id SET DEFAULT nextval('public.processdependencies_id_seq'::regclass);


    --
    -- Name: processes id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processes ALTER COLUMN id SET DEFAULT nextval('public.processes_id_seq'::regclass);


    --
    -- Name: processes2 id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processes2 ALTER COLUMN id SET DEFAULT nextval('public.processes2_id_seq'::regclass);


    --
    -- Name: processgroup id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processgroup ALTER COLUMN id SET DEFAULT nextval('public.processgroup_id_seq'::regclass);


    --
    -- Name: processref id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processref ALTER COLUMN id SET DEFAULT nextval('public.processref_id_seq'::regclass);


    --
    -- Name: projects id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


    --
    -- Name: refdataversion id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion ALTER COLUMN id SET DEFAULT nextval('public.refdataversion_id_seq'::regclass);


    --
    -- Name: refdataversion2process id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2process ALTER COLUMN id SET DEFAULT nextval('public.refdataversion2process_id_seq'::regclass);


    --
    -- Name: refdataversion2processref id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2processref ALTER COLUMN id SET DEFAULT nextval('public.refdataversion2processref_id_seq'::regclass);


    --
    -- Name: referencedata id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.referencedata ALTER COLUMN id SET DEFAULT nextval('public.referencedata_id_seq'::regclass);


    --
    -- Name: referencedataimport id; Type: DEFAULT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.referencedataimport ALTER COLUMN id SET DEFAULT nextval('public.referencedataimport_id_seq'::regclass);


    --
    -- Name: contacts contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.contacts
        ADD CONSTRAINT contacts_pkey PRIMARY KEY (id);


    --
    -- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.notifications
        ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


    --
    -- Name: processdependencies processdependencies_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processdependencies
        ADD CONSTRAINT processdependencies_pkey PRIMARY KEY (id);


    --
    -- Name: processes2 processes2_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processes2
        ADD CONSTRAINT processes2_pkey PRIMARY KEY (id);


    --
    -- Name: processes processes_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processes
        ADD CONSTRAINT processes_pkey PRIMARY KEY (id);


    --
    -- Name: processgroup processgroup_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processgroup
        ADD CONSTRAINT processgroup_pkey PRIMARY KEY (id);


    --
    -- Name: processref processref_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processref
        ADD CONSTRAINT processref_pkey PRIMARY KEY (id);


    --
    -- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.projects
        ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


    --
    -- Name: refdataversion2process refdataversion2process_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2process
        ADD CONSTRAINT refdataversion2process_pkey PRIMARY KEY (id);


    --
    -- Name: refdataversion2processref refdataversion2processref_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2processref
        ADD CONSTRAINT refdataversion2processref_pkey PRIMARY KEY (id);


    --
    -- Name: refdataversion refdataversion_dataset_id_uc; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion
        ADD CONSTRAINT refdataversion_dataset_id_uc UNIQUE (dataset_id);


    --
    -- Name: refdataversion refdataversion_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion
        ADD CONSTRAINT refdataversion_pkey PRIMARY KEY (id);


    --
    -- Name: refdataversion refdataversion_referenceid_version_uc; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion
        ADD CONSTRAINT refdataversion_referenceid_version_uc UNIQUE (referenceid, version);


    --
    -- Name: referencedata referencedata_name_key; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.referencedata
        ADD CONSTRAINT referencedata_name_key UNIQUE (name);


    --
    -- Name: referencedata referencedata_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.referencedata
        ADD CONSTRAINT referencedata_pkey PRIMARY KEY (id);


    --
    -- Name: referencedataimport referencedataimport_pkey; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.referencedataimport
        ADD CONSTRAINT referencedataimport_pkey PRIMARY KEY (id);


    --
    -- Name: referencedataimport referencedataimport_referenceid_key; Type: CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.referencedataimport
        ADD CONSTRAINT referencedataimport_referenceid_key UNIQUE (referenceid);


    --
    -- Name: contacts contacts_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.contacts
        ADD CONSTRAINT contacts_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


    --
    -- Name: notifications notifications_contactid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.notifications
        ADD CONSTRAINT notifications_contactid_fkey FOREIGN KEY (contactid) REFERENCES public.contacts(id);


    --
    -- Name: notifications notifications_projectid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.notifications
        ADD CONSTRAINT notifications_projectid_fkey FOREIGN KEY (projectid) REFERENCES public.projects(id);


    --
    -- Name: processdependencies processdependencies_depends_on_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processdependencies
        ADD CONSTRAINT processdependencies_depends_on_fkey FOREIGN KEY (depends_on) REFERENCES public.processref(id);


    --
    -- Name: processdependencies processdependencies_processrefid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processdependencies
        ADD CONSTRAINT processdependencies_processrefid_fkey FOREIGN KEY (processrefid) REFERENCES public.processref(id);


    --
    -- Name: processes processes_projectid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processes
        ADD CONSTRAINT processes_projectid_fkey FOREIGN KEY (projectid) REFERENCES public.projects(id);


    --
    -- Name: processgroup processgroup_projectid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processgroup
        ADD CONSTRAINT processgroup_projectid_fkey FOREIGN KEY (projectid) REFERENCES public.projects(id);


    --
    -- Name: processref processref_processgroupid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processref
        ADD CONSTRAINT processref_processgroupid_fkey FOREIGN KEY (processgroupid) REFERENCES public.processgroup(id);


    --
    -- Name: processref processref_processid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.processref
        ADD CONSTRAINT processref_processid_fkey FOREIGN KEY (processid) REFERENCES public.processes2(id);


    --
    -- Name: refdataversion2process refdataversion2process_processid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2process
        ADD CONSTRAINT refdataversion2process_processid_fkey FOREIGN KEY (processid) REFERENCES public.processes2(id) ON DELETE CASCADE;


    --
    -- Name: refdataversion2process refdataversion2process_referencedataid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2process
        ADD CONSTRAINT refdataversion2process_referencedataid_fkey FOREIGN KEY (referencedataid) REFERENCES public.referencedata(id) ON DELETE CASCADE;


    --
    -- Name: refdataversion2process refdataversion2process_referencedataversionid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2process
        ADD CONSTRAINT refdataversion2process_referencedataversionid_fkey FOREIGN KEY (referencedataversionid) REFERENCES public.refdataversion(id) ON DELETE CASCADE;


    --
    -- Name: refdataversion2processref refdataversion2processref_processdefaultid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2processref
        ADD CONSTRAINT refdataversion2processref_processdefaultid_fkey FOREIGN KEY (processdefaultid) REFERENCES public.refdataversion2process(id) ON DELETE CASCADE;


    --
    -- Name: refdataversion2processref refdataversion2processref_processrefid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2processref
        ADD CONSTRAINT refdataversion2processref_processrefid_fkey FOREIGN KEY (processrefid) REFERENCES public.processref(id) ON DELETE CASCADE;


    --
    -- Name: refdataversion2processref refdataversion2processref_supersedingversionid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion2processref
        ADD CONSTRAINT refdataversion2processref_supersedingversionid_fkey FOREIGN KEY (supersedingversionid) REFERENCES public.refdataversion(id) ON DELETE CASCADE;


    --
    -- Name: refdataversion refdataversion_referenceid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.refdataversion
        ADD CONSTRAINT refdataversion_referenceid_fkey FOREIGN KEY (referenceid) REFERENCES public.referencedata(id);


    --
    -- Name: referencedataimport referencedataimport_referenceid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: projects
    --

    ALTER TABLE ONLY public.referencedataimport
        ADD CONSTRAINT referencedataimport_referenceid_fkey FOREIGN KEY (referenceid) REFERENCES public.referencedata(id);


    --
    -- PostgreSQL database dump complete
    --


    INSERT INTO version
        (version)
    SELECT 1
    WHERE
        NOT EXISTS (
            SELECT version FROM version
        );
END IF;
END $$;
