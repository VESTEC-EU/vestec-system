#!/usr/local/bin/flask
'''render_template loads html pages of the application
'''
import os
import uuid
import requests
from flask import Flask, render_template, request

APP = Flask(__name__)  # create an instance if the imported Flask class

TARGET_URI = 'http://127.0.0.1:5500/jobs'
CURRENT_JOB = {'uuid': '', 'name': ''}

def generate_id():
    '''auto-generates a uuid'''
    return str(uuid.uuid1())


@APP.route('/')  # used to bind the following function to the specified URL
def welcome_page():
    '''Render a static welcome template'''
    return render_template('index.html')


@APP.route('/submit', methods=['PUT'])
def submit_job():
    '''This function sends a PUT request to the SMI for a CURRENT_JOB
       to be created

       Process:
       - generate CURRENT_JOB object
       - send CURRENT_JOB object as JSON to the SMI server
       - if the SMI server has received the JSON package, return string message

       Input Params: none
       Output Params: response_data - SMI response string

       Data Structures:
       - SMI URI: /jobs/uuid
       - CURRENT_JOB object: {'uuid': <id>, 'name': <title>}
       - SMI response data: 'SUCCESS' or 'FAILURE'
    '''
    CURRENT_JOB['uuid'] = generate_id()
    CURRENT_JOB['name'] = request.form.get('jsdata')

    job_request = requests.put(TARGET_URI + '/' + CURRENT_JOB.get('uuid'), json=CURRENT_JOB)
    response_data = job_request.text

    return response_data


@APP.route('/jobs/current', methods=['GET'])
def check_job_status():
    '''This function sends a GET request to the SMI for the details of the current job

       Process:
       - send get request to the SMI passing the current job as parameter
       - get SMI response job dictionary
       - render SMI response on table template

       Input Params: none
       Output Params: response_data - SMI response dictionary

       Data Structures:
       - SMI URI: /jobs/uuid
       - SMI response data: {"uuid": <jobuuid>, "name": <jobname>,
                             "jobs": [{"machine": <machinename>,
                                       "status": <jobstatus>, "executable": <exec>,
                                       "QueueID": <queueid>}, {}],
                             "date": <jobsubmitdate>, "status": <jobstatus>}
    '''
    current_stat_req = requests.get(TARGET_URI + '/' + str(CURRENT_JOB.get('uuid')))
    response_data = [current_stat_req.json()]

    return render_template('jobstatustable.html', jobs=response_data)


@APP.route('/jobs', methods=['GET'])
def check_all_jobs_status():
    '''This function sends a GET request to the SMI for the details of all jobs

       Process:
       - send get request to the SMI for all jobs
       - get SMI response jobs dictionary of dictionaries
       - render SMI response on table template

       Input Params: none
       Output Params: response_data - SMI response dictionary

       Data Structures:
       - SMI URI: /jobs
       - SMI response data: [{"uuid": <jobuuid>, "name": <jobname>,
                              "jobs": [{"machine": <machinename>,
                                        "status": <jobstatus>, "executable": <exec>,
                                        "QueueID": <queueid>}, {}
                              ], "date": <jobsubmitdate>, "status": <jobstatus>}, {}]
    '''
    all_stat_req = requests.get(TARGET_URI)
    response_data = all_stat_req.json()

    return render_template('jobstatustable.html', jobs=response_data)


@APP.errorhandler(404)
def page_not_found():
    '''note that we set the 404 status explicitly'''
    return render_template('404.html'), 404


if __name__ == '__main__':
    if "VESTEC_MANAGER_URI" in os.environ:
        TARGET_URI = os.environ["VESTEC_MANAGER_URI"]
    print("Website using SimulationManager URI: %s"%TARGET_URI)
    APP.run(host='0.0.0.0', port=5000)
