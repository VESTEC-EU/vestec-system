'''This script reads the collected jobs from the queue
and checks when they start to run in order to register
the actual time they waited in the queue and compare it
with the estimated time.
'''
from __future__ import print_function
from datetime import datetime
import json
import os
import sys
from glob import glob
from DecisionMaker import DecisionMaker
sys.path.append(os.path.join(os.path.dirname(__file__), "data/ARCHER/"))

DM = DecisionMaker()
CONNECTION = DM.machine_connect('ARCHER')

def archer_queue_track():
    '''
    job = {id: '', nodes: '', predicted_time: '', actual_time: ''}
    '''
    print('---')
    print(str(datetime.now())[:-7])

    jobs = DM.query_machine('ARCHER', CONNECTION, "qstat -f")
    running = DM.get_running(jobs)

    jobs_files = glob("data/ARCHER/predicted-*.json")

    for jobs_file in jobs_files:
        jobs_to_track = []

        with open(jobs_file, 'r') as sample_file:
            jobs_to_track = json.load(sample_file)

            for job in running:
                for track in jobs_to_track:
                    if track['id'] == job['JobID']:
                        actual_time = DM.parse_time(job['stime']) - DM.parse_time(job['qtime'])
                        track['actual_time'] = str(actual_time)

        with open(jobs_file, 'w') as sample_file:
            sorted_jobs = sorted(jobs_to_track, key=lambda k: k['nodes'])
            json.dump(sorted_jobs, sample_file, indent=2, sort_keys=True)

if __name__ == "__main__":
    archer_queue_track()
    