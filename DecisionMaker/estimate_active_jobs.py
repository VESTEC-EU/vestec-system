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
    print("%s - ESTIMATING WAITTIME FOR %s JOBS CURRENTLY IN THE QUEUE..." % (str(datetime.now())[:-7], machine))
    connection = DM.machine_connect(machine)
    jobs = DM.query_machine(machine, connection, "qstat -f")
    queued = DM.get_queued(jobs)

    for job in queued:
        print("---")
        estimated = {}
        estimated["system_job_id"] = str(job['JobID'])
        estimated["queue_id"] = DBM.get_queue_id(job['queue'])[0]

        exists = DBM.check_job_existence(estimated["system_job_id"], estimated["queue_id"])

        if exists:
            print("### Job already existent in the database. Skipping...")
        else:
            print("### New job found. Estimating...")
            estimated["job_id"] = str(uuid.uuid4())
            estimated["no_nodes"] = int(job['Resource_List.nodect'])
            estimated["no_cpus"] = int(job['Resource_List.ncpus'])

            date = DBM.date_to_db_format(DM.parse_time(job['ctime']))
            estimated["submit_time"] = date

            estimated["start_time"] = None
            estimated["finish_time"] = None
            estimated["exit_status"] = None
            estimated["wall_time"] = int(timeparse(job['Resource_List.walltime']))
            estimated["current_state"] = 'queuing'
            estimated["qtime"] = DM.parse_time(job['qtime'])

            estimated_time = DM.machine_wait_time(machine, queued, estimated["no_nodes"])
            queued_time = datetime.now() - estimated["qtime"]
            total_time = int(estimated_time.total_seconds() + queued_time.total_seconds())

            estimated["estimated_waittime"] = total_time
            insert_data(estimated)


def insert_data(job):
    '''This function makes use of a list of job objects with estimated
    wait times and inserts the jobs in the Jobs table, the estimated
    wait times in the Waittimes table and the requested walltime in the
    Walltimes table'''
    print("# Inserting estimations for job %s..." % job["system_job_id"])

    if job["queue_id"] is not None:
        # Insert job into Jobs table
        DBM.insert_job(job["job_id"], job["system_job_id"], job["queue_id"],
                       job["no_nodes"], job["no_cpus"])
        # Insert job workflow into Workflow table
        workflow = {"job_id": job["job_id"], "submit_time": job["submit_time"],
                    "current_state": job["current_state"], "queue_time": job["qtime"],
                    "start_time": None, "finish_time": None, "exit_status": None,
                    "transit_time": None}
        DBM.insert_workflow(workflow)
        # insert_waittime(job_id, estimated_waittime, actual_waittime=None, error=None)
        DBM.insert_waittime(job["job_id"], job["estimated_waittime"])
        # insert_waittime(job_id, requested_walltime, actual_walltime=None, error=None)
        DBM.insert_walltime(job["job_id"], job["wall_time"])


if __name__ == "__main__":
    DM = DecisionMaker(os.path.join(os.path.dirname(__file__), 'data/jobs_database.db'))
    DBM = DatabaseManager(os.path.join(os.path.dirname(__file__), 'data/jobs_database.db'))
    machines = DBM.get_machine_names()

    for machine in machines:
        jobs = estimate_jobs(machine)
