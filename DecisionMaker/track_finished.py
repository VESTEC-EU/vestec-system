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
from glob import glob
from DecisionMaker import DecisionMaker

print('---')
print('Tracking finished jobs at %s...' % str(datetime.now())[:-7])

DM = DecisionMaker()
CONNECTION = DM.machine_connect('ARCHER')

def archer_track_finished():
    '''
    job = {id: '', nodes: '', sumbitted: '', start_time: '' , est_walltime: '', real_walltime: ''}
    '''
    jobs_files = glob(os.path.join(os.path.dirname(__file__), "data/ARCHER/running-*.json"))

    for jobs_file in jobs_files:
        jobs_to_track = []
        finished_jobs = []

        with open(jobs_file, 'r') as sample_file:
            jobs_to_track = json.load(sample_file)

        for job in jobs_to_track:
            if 'real_walltime' not in job:
                ran = DM.query_machine('ARCHER', CONNECTION, "qstat %s" % job["id"])
                finished_jobs.append(ran)

        if len(finished_jobs) >= 1:
            with open(os.path.join(os.path.dirname(__file__), "data/ARCHER/finished_jobs.json"), 'w') as sample_file:
                json.dump(finished_jobs, sample_file, indent=2, sort_keys=True)

        print("Found and tracked %s jobs from %s" % (len(finished_jobs), jobs_file))

if __name__ == "__main__":
    archer_track_finished()
    