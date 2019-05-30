'''This script extracts data about the jobs in the queue
and jobs running for testing purposes. The queued and
running jobs are saved to files that are used by the
track script to find the actual times they took while
waiting in the queue or while running.
'''
from __future__ import print_function
from datetime import datetime
import json
import os
import sys
from DecisionMaker import DecisionMaker
sys.path.append(os.path.join(os.path.dirname(__file__), "data/ARCHER/"))

DM = DecisionMaker()
CONNECTION = DM.machine_connect('ARCHER')
JOBS = DM.query_machine('ARCHER', CONNECTION, "qstat -f")
TIME = str(datetime.now())[:-7]

def archer_queue_predict():
    '''
    job = {id: '', nodes: '', walltime: '', predicted_time: '', actual_time: ''}
    '''
    jobs_to_predict = []
    queued = DM.get_queued(JOBS)

    for job in queued:
        predict = {}
        predict['id'] = job['JobID']
        predict['nodes'] = int(job['Resource_List.nodect'])
        predict['walltime'] = job["Resource_List.walltime"]
        job_size = predict['nodes']
        print("---")
        print(predict['nodes'])

        node_time = DM.machine_wait_time('ARCHER', JOBS, job_size)
        wait_time = datetime.now() - DM.parse_time(job['qtime'])

        predict['predicted_time'] = str(node_time - wait_time)[:-7]
        jobs_to_predict.append(predict)

        save_to_file('data/ARCHER/predicted-%s.json' % TIME, jobs_to_predict)


def archer_check_running():
    '''
    job = {id: '', nodes: '', sumbitted: '', start_time: '', est_walltime: ''}
    '''
    running_jobs = []
    running = DM.get_running(JOBS)

    for job in running:
        run = {}
        run['id'] = job['JobID']
        run['nodes'] = int(job['Resource_List.nodect'])
        run['submitted'] = job['qtime']
        run['start_time'] = job['stime']
        run['est_walltime'] = job["Resource_List.walltime"]

        running_jobs.append(run)

        save_to_file('data/ARCHER/running-%s.json' % TIME, running_jobs)


def save_to_file(file_name, jobs):
    '''Saves jobs to json file'''
    with open(file_name, 'w') as sample_file:
        sorted_jobs = sorted(jobs, key=lambda k: k['nodes'])
        json.dump(sorted_jobs, sample_file, indent=2, sort_keys=True)


if __name__ == "__main__":
    archer_queue_predict()
    archer_check_running()
