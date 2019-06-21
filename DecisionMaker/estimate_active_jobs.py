'''This script extracts data about the jobs in the queue
and jobs running for testing purposes. The queued and
running jobs are saved to files that are used by the
track script to find the actual times they took while
waiting in the queue or while running.
'''
from __future__ import print_function
from pytimeparse.timeparse import timeparse
from datetime import datetime
import json
import os
import sys
import uuid
from decision_maker import DecisionMaker
sys.path.append(os.path.join(os.path.dirname(__file__), "data"))
from database_manager import DatabaseManager


def estimate_jobs(machine):
    print("%s - ESTIMATING WAITTIME FOR JOBS CURRENTLY IN THE QUEUE..." % str(datetime.now())[:-7])
    connection = DM.machine_connect(machine)
    jobs = DM.query_machine(machine, connection, "qstat -f")
    queued = DM.get_queued(jobs)

    estimated_jobs = []
    for job in queued:
        estimated = {}
        estimated["job_id"] = str(uuid.uuid4())
        estimated["system_id"] = str(job['JobID'])
        estimated["queue_id"] = DBM.get_queue_id(job['queue'])[0]
        estimated["no_nodes"] = int(job['Resource_List.nodect'])
        estimated["no_cpus"] = int(job['Resource_List.ncpus'])

        date = DBM.date_to_db_format(DM.parse_time(job['ctime']))
        estimated["submit_time"] = date

        estimated["start_time"] = None
        estimated["finish_time"] = None
        estimated["exit_status"] = None
        estimated["wall_time"] = int(timeparse(job['Resource_List.walltime']))
        estimated["job_state"] = 'queuing'

        estimated_time = DM.machine_wait_time('ARCHER', queued, estimated["no_nodes"])
        queued_time = datetime.now() - DM.parse_time(job['qtime'])
        total_time = int(estimated_time.total_seconds() + queued_time.total_seconds())

        estimated["estimated_waittime"] = total_time
        estimated_jobs.append(estimated)

    return estimated_jobs


def insert_data(estimations):
    '''This function makes use of a list of job objects with estimated
    wait times and inserts the jobs in the Jobs table, the estimated
    wait times in the Waittimes table and the requested walltime in the
    Walltimes table'''
    for estimation in estimations:
        print("# Inserting estimations for job %s..." % estimation["job_id"])

        if estimation["queue_id"] is not None:
            DBM.insert_job(estimation)
            # insert_waittime(job_id, estimated_waittime, actual_waittime=None, error=None)
            DBM.insert_waittime(estimation["job_id"], estimation["estimated_waittime"])
            # insert_waittime(job_id, requested_walltime, actual_walltime=None, error=None)
            DBM.insert_walltime(estimation["job_id"], estimation["wall_time"])


if __name__ == "__main__":
    DM = DecisionMaker("data/jobs_database.db")
    DBM = DatabaseManager('data/jobs_database.db')
    machines = DBM.get_machine_names()

    for machine in machines:
        jobs = estimate_jobs(machine)
        insert_data(jobs)
