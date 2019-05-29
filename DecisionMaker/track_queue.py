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

    with open(os.path.join(os.path.dirname(__file__), 'data/ARCHER/', 'predicted_times.json'), 'r') as sample_file:
        jobs_to_track = json.load(sample_file)

    DM = DecisionMaker()
    jobs = DM.query_machine('ARCHER', "qstat -f")
    running = DM.get_running(jobs)

    for job in running:
        for track in jobs_to_track:
            if track['id'] == job['JobID']:
                actual_time = DM.parse_time(job['stime']) - DM.parse_time(job['qtime'])
                track['actual_time'] = str(actual_time)

    with open('data/ARCHER/predicted_times.json', 'w') as sample_file:
        sorted_jobs = sorted(jobs_to_track, key=lambda k: k['nodes'])
        json.dump(sorted_jobs, sample_file, indent=2, sort_keys=True)

if __name__ == "__main__":
    archer_queue_track()
    