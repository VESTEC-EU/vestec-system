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
from decision_maker import DecisionMaker

print('---')
print('Tracking finished jobs at %s...' % str(datetime.now())[:-7])

DM = DecisionMaker()
CONNECTION = DM.machine_connect('ARCHER')

def archer_track_finished():
    '''
    job = {id: '', nodes: '', sumbitted: '', start_time: '' , estimated_walltime: '', actual_walltime: ''}
    '''
    jobs_files = glob(os.path.join(os.path.dirname(__file__), "data/ARCHER/running-*.json"))

    for jobs_file in jobs_files:
        jobs = []
        finished_jobs = []

        with open(jobs_file, 'r') as sample_file:
            jobs = json.load(sample_file)

        job_result = DM.query_machine('ARCHER', CONNECTION, "qstat -xf %s" % jobs[0]["id"])

        for job in jobs:
            if 'actual_walltime' not in job:
                ran = DM.query_machine('ARCHER', CONNECTION, "qstat -xf %s" % job["id"])
                job["actual_walltime"] = ran[0]['resources_used.walltime']

        if len(jobs) >= 1:
            with open(jobs_file, 'w') as sample_file:
                json.dump(jobs, sample_file, indent=2, sort_keys=True)

        print("Found and tracked %s jobs from %s" % (len(jobs), jobs_file))


if __name__ == "__main__":
    archer_track_finished()
    