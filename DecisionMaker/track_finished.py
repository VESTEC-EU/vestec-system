from __future__ import print_function
from datetime import datetime, timedelta
import logging
import json
from DecisionMaker import DecisionMaker
import os, sys

def archer_queue_track():
    '''
    job = {id: '', nodes: '', predicted_time: '', actual_time: ''}
    '''
    print('---')
    print(str(datetime.now()))
    jobs_to_track = []

    with open(os.path.join(os.path.dirname(__file__), 'data/ARCHER', 'predicted_times.json'), 'r') as sample_file:
        jobs_to_track = json.load(sample_file)

    DM = DecisionMaker()
    '''The function performing qstat at the moment depends on having its output saved to an external file
    this means that looping through all the jobs could create the same number of
    files which is not ideal.

    finished_jobs = []

    for job in jobs_to_track:
        ran = DM.query_machine('ARCHER', "qstat %s" % job["id"])
        finished_jobs.append(ran)
    '''
    ran = DM.query_machine('ARCHER', "qstat 6236749")

    with open('data/ARCHER/finished_jobs.json', 'w') as sample_file:
        #sorted_jobs = sorted(ran, key=lambda k: k['nodes'])
        json.dump(ran, sample_file, indent=2, sort_keys=True)

if __name__ == "__main__":
    archer_queue_track()
    