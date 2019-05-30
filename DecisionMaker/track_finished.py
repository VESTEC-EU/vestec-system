'''This script reads the collected running jobs and checks
their details after they have run in order to find the actual
time they took to run and compare that with the estimated
walltime they have been submitted with. This is to be used
to generate an error score of the walltimes depending on the
job sizes.
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

def archer_track_finished():
    '''
    job = {id: '', nodes: '', sumbitted: '', start_time: '' , est_walltime: '', real_walltime: ''}
    '''
    print('---')
    print(str(datetime.now())[:-7])

    jobs_files = glob("data/ARCHER/running-*.json")

    for jobs_file in jobs_files:
        jobs_to_track = []
        finished_jobs = []

        with open(jobs_file, 'r') as sample_file:
            jobs_to_track = json.load(sample_file)

        for job in jobs_to_track:
            ran = DM.query_machine('ARCHER', CONNECTION, "qstat %s" % job["id"])

            finished_jobs.append(ran)

        with open("data/ARCHER/finished_jobs.json", 'w') as sample_file:
            #sorted_jobs = sorted(jobs_to_track, key=lambda k: k['nodes'])
            json.dump(finished_jobs, sample_file, indent=2, sort_keys=True)

if __name__ == "__main__":
    archer_track_finished()
    