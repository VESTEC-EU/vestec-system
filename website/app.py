#!/usr/local/bin/flask
# render_template loads html pages of the application
import uuid
import requests
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)  # create an instance if the imported Flask class

targetURI = 'http://127.0.0.1:5500/jobs'
current_job = {'uuid': '', 'name': ''}

def generate_id():
    return str(uuid.uuid1())

@app.route('/')  # used to bind the following function to the specified URL
def welcome_page():
    '''Render a static welcome template'''
    return render_template('index.html')

@app.route('/submit', methods = ['PUT'])
def submit_job():
    '''This function sends a PUT request to the SMI for a current_job
       to be created

       Process:
       - generate current_job object
       - send current_job object as JSON to the SMI server
       - if the SMI server has received the JSON package, return string message

       Input Params: none
       Output Params: response_data - SMI response string

       Data Structures:
       - SMI URI: /jobs/uuid
       - current_job object: {'uuid': <id>, 'name': <title>}
       - SMI response data: 'SUCCESS' or 'FAILURE'
    '''
    current_job['uuid'] = generate_id()
    current_job['name'] = request.form.get('jsdata')

    job_request = requests.put(targetURI + '/' + current_job.get('uuid'), json=current_job)
    response_data = job_request.text

    return response_data

@app.route('/jobs/current', methods = ['GET'])
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
       - SMI response data: {"uuid": <jobuuid>, "name": <jobname>, "jobs": [{"machine": <machinename>,
                             "status": <jobstatus>, "executable": <exec>, "QueueID": <queueid>}, {}],
                             "date": <jobsubmitdate>, "status": <jobstatus>}
    '''
    current_stat_req = requests.get(targetURI + '/' + str(current_job.get('uuid')))
    response_data = [current_stat_req.json()]

    return render_template('jobstatustable.html', jobs=response_data)

@app.route('/jobs', methods = ['GET'])
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
       - SMI response data: [{"uuid": <jobuuid>, "name": <jobname>, "jobs": [{"machine": <machinename>,
                              "status": <jobstatus>, "executable": <exec>, "QueueID": <queueid>}, {}
                             ], "date": <jobsubmitdate>, "status": <jobstatus>}, {}]
    '''
    all_stat_req = requests.get(targetURI)
    response_data = all_stat_req.json()

    return render_template('jobstatustable.html', jobs=response_data)

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

if __name__ == '__main__':
    if "VESTEC_MANAGER_URI" in os.environ:
        targetURI = os.environ["VESTEC_MANAGER_URI"]
    print("Website using SimulationManager URI: %s"%targetURI)
    app.run(host='0.0.0.0', port=5000)
