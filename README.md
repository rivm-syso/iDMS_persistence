# iDMS_persistence

[![fair-software.eu](https://img.shields.io/badge/fair--software.eu-%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8B%20%20%E2%97%8B%20%20%E2%97%8B-orange)](https://fair-software.eu)
![PEP8](https://badgen.net/badge/pep/8/pink?icon=python)
![Python Version](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-EUPL_v1.2-green)

Database definition and REST interface for the configuration of prrojects, processes and processgroups

The database, usually referend to as Project-Database contains management information outside of the IRODS-System. 

Primarily these are:
 * Projects
   : A collection of users and mangers which have access to a project-collection. 
 * Processes
   : Defines a GIT-repository with code to run on the HPC, along with minimum requirements and compatible clusters
 * Processgroups
   : Defines dependencies between defined processes within a project. 
 * Reference datasets
   : Defines external datasets which needs to be checked regularly for changes and to create versions from.

## Endpoints

The file requests.http contains a complete set of example requests to the available endpoints

For ids (e.g. __projectid__, __processid__, __referencedataid__) its usually permissibale to use either the numerical value or the name of the object.

We use Basic HTTP Authentication.

endpoint|method|data fields|description
-|-|-|-
/api/1.0/projects|GET||lijst van projecten ophalen
/api/1.0/projects|POST|name|nieuw project aanmaken
/api/1.0/projects/\<projectid\>|GET||projectdetails opvragen
/api/1.0/projects/\<projectid\>|PUT|description,<br>default_collection,<br>service_account|projectdetails aanpassen
/api/1.0/projects/\<projectid\>/processes|GET||Processen voor project \<projectid\> opvragen
/api/1.0/projects/\<projectid\>/processes|POST|name|Nieuw proces voor project \<projectid\> aanmaken
/api/1.0/projects/\<projectid\>/processes|POST|name|Nieuw proces voor project \<projectid\> aanmaken
/api/1.0/projects/\<projectid\>/processes/\<processid\>|GET||Procesdetails voor proces \<processid\> in project \<projectid\> opvragen
/api/1.0/projects/\<projectid\>/processes/\<processid\>|PUT|name,description,<br>output_prefix,distribution,<br>modify_in_place, restartable,<br>repo,tag,<br>lsf_queue,next_projectid,<br>next_processid|Procesdetails voor proces \<processid\> in project \<projectid\> wijzigen
/api/1.0/projects/\<projectid\>/processes/\<processid\>|DELETE||Proces  verwijderen



# local setup for testing
 
 * conda env remove -n flask-rest
 * conda env create -f envs/flask-rest.source.yaml
 * conda activate flask-rest
 * pip install -e .



* copy ./instance/config.py.sample to ./instance/config.py

* For testing-purposes, the flask-rest-test environment contains a postgres instance.

* Since the script needs to login to the HEAD_NODE we need to provide the PRIVATE_KEY.
  As PRIVATE_KEY_FILE set: /home/<youruser>/.ssh/id_rsa and as PRIVATE_KEY_TYPE: RSA.
On the hosts (rivm-biohn-l01a/rivm-biohn-l02a) this key has to be added to the authorized-hosts:
 
  ssh rivm-biohn-l01a.rivm.ssc-campus.nl
  sudo su - svc-sscc-irods
  vi .ssh/authorized_keys


* settings.json.sample needs to be copied to settings.json.
~~  * Change the pythonPath to "/mnt/scratch_dir/<youruser>/conda/envs/flask-rest/bin/python" the python-interpreter in your local conda-environment for the project.~~
Here further environment variables are defined, for test, acc, prod, local, ...
  * Under $shared, insert the username as: "alt\\<yourname>"
  * Instead of providing the password as clear text, it is possible to provide the NTLM-hash.
Like for the irods_account, it has to be prefixed by 16 "0"s and a colon:

   "00000000000000000000000000000000:4dfbb221f67c4754ae61c1d6417858c9"

to get the NTLM-hash there is a script in the root-directory:
python myhash.py, provide it with the ldap-password, the hex-representation of the hash is in the last line of the output.

* After this you should be able to start the local rest-api, running with a local test-database (which is empty)- Any changes on the database-schema in the python-code will be migrated automatically during startup.

   ./start.sh

Now its possible to use the requests to fill the database.

* In VSCode install the extension "REST Client for Visual Studio Code" (Huachao Mao),
then the sample.requests can be easily executed by pressing "send request".
(Otherwise wget could be used, but then the authorization might be more problematic)

Since the database is initially empty create a new project first!


##debugging

To use the debugger, make sure the selected interpreter is the one of the correct conda-environment (on the bottom left of VSCode)

## Support


For questions, bug reports, or feature requests:
- Open an issue in the idms_persistence GitHub repository.
- Reach out to the iDMS maintenance team at BIR-intern@rivm.nl


## Contributing

## License

European Union Public Licence (EUPL) v. 1.2

