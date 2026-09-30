import argparse
import json
import requests
from requests.auth import HTTPBasicAuth

PROJECT_URL = "http://rivm-bioir-l01a.rivm.ssc-campus.nl/api/1.0/"
PROJECT_URL = "http://0.0.0.0:5000/api/1.0/"
username = ''
userhash = ''

REQUESTS_METHODS = {
    'GET':   requests.get,
    'PUT':   requests.put,
    'POST':  requests.post,
    'DELETE':requests.delete
}

def rest_call(request_type, endpoint, data={}):    
    url = '{}{}'.format(PROJECT_URL, endpoint)
    auth = HTTPBasicAuth(username, userhash)
    return_data = {}
    if request_type in REQUESTS_METHODS:
        response = REQUESTS_METHODS[request_type](url, auth=auth, json=data)
    try:
        return_data = response.json()
    except:
        return_data = {}
    return return_data, response.status_code

def convert_db():

    global username, userhash

    parser = argparse.ArgumentParser(description='Data synchronisation between iRODS and '
        'other file protocols.')
    parser.add_argument('-i', '--input', help='input json file', required=True)
    parser.add_argument('-P', '--projects', help='Convert projects', action="store_true")
    parser.add_argument('-p', '--processes', help='Convert processes', action="store_true")
    parser.add_argument('-f', '--force', help='Always create project', action="store_true")
    parser.add_argument('-U', '--user', help='AD User account ( domain\\user )', required=True)
    parser.add_argument('-H', '--hash', help='AD password or NTLM HASH', required=True)

    args = parser.parse_args()
    
    username = args.user
    userhash = args.hash

    with open(args.input, 'r') as f:
        input_json = json.load(f)

    if args.projects:
        for project in input_json:
            print('Analyzing {}'.format(project))
            data, result = rest_call('GET', 'projects/{}'.format(project))
            if result == 200:
                print('Project exists. Updating settings')
                props = input_json[project]['settings']
                data, result2 = rest_call('PUT', 'projects/{}'.format(project), data=props)
            if args.force or result != 200:
                print('Create {}'.format(project))
                data, result = rest_call('POST', 'projects', data={'name': project, 'force': 'true'})

    if args.processes:
        for project in input_json:
            data, result = rest_call('GET', 'projects/{}'.format(project))
            if result == 200:
                for process in input_json[project]['processes']:
                    print('Project {}, process {}'.format(project, process))
                    data, result2 = rest_call('GET', 'projects/{}/processes/{}'.format(project, process))
                    if result2 != 200:
                        print('process {} not found. Creating ..'.format(process))
                        data, result3 = rest_call('POST', 'projects/{}/processes'.format(project), data={ 'name': process})

                    # SET PROCESS PROPERTIES
                    process_data = input_json[project]['processes'][process]
                    props = { prop: process_data[prop] for prop in process_data if prop in
                        ["description", "lsf_queue", "name", "repo", "tag", "next_processID", "next_projectID"] }
                    for prop in [ "distribution", "modify_in_place", "restartable" ]:
                        if prop in process_data:
                            props[prop] = 1 if process_data[prop] == 'true' else 0
                    data, result4 = rest_call('PUT',
                        'projects/{}/processes/{}'.format(project, process),
                        data=props)
                    print(data, result4)
            else:
                print('Project {} not found'.format(project))


if __name__ == "__main__":
    convert_db()
