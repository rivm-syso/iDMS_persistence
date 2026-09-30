DELETE FROM REFERENCEDATAIMPORT;
DELETE FROM REFDATAVERSION;
DELETE FROM REFERENCEDATA;
DELETE FROM PROCESSREF;
DELETE FROM PROCESSGROUP;
DELETE FROM PROCESSES2;
DELETE FROM PROJECTS;
INSERT INTO PROJECTS("name", "description", "service_account") VALUES ('ngslab', 'NGSLab', 'svc-irods_ngslab');
INSERT INTO PROJECTS("name", "description", "service_account") VALUES ('test1', 'Test project', 'svc-irods_test1');
INSERT INTO PROCESSES2("name") VALUES ('pr1');
INSERT INTO PROCESSGROUP("name", "projectid") VALUES 
    ('pg1', (SELECT id FROM PROJECTS WHERE NAME = 'ngslab'));
INSERT INTO PROCESSGROUP("name", "projectid") VALUES 
    ('pg2', (SELECT id FROM PROJECTS WHERE NAME = 'test1'));
INSERT INTO PROCESSREF("name", "processid", "processgroupid") VALUES 
    ('pr1', 
        (SELECT id FROM PROCESSES2 WHERE NAME = 'pr1'),
        (SELECT id FROM PROCESSGROUP WHERE NAME = 'pg1')
    );
INSERT INTO PROCESSREF("name", "processid", "processgroupid") VALUES 
    ('pr2', 
        (SELECT id FROM PROCESSES2 WHERE NAME = 'pr1'),
        (SELECT id FROM PROCESSGROUP WHERE NAME = 'pg2')
    );
INSERT INTO REFERENCEDATA("name") VALUES ('refdb1');
INSERT INTO REFDATAVERSION("referenceid", "version", "version_name", "dataset_id") VALUES
    ((SELECT id FROM referencedata where NAME = 'refdb1'),
        1,
        'Version 1',
        'd33719a6-7197-4f12-ad57-094184e0b47d'
    );
INSERT INTO REFDATAVERSION("referenceid", "version", "version_name", "dataset_id") VALUES
    ((SELECT id FROM referencedata where NAME = 'refdb1'),
        2,
        'Version 2',
        'c5122b5b-de19-4b79-a333-d060b2b6f90a'
    )

