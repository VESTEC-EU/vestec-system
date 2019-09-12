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
from pytimeparse.timeparse import timeparse
from decision_maker import DecisionMaker
sys.path.append(os.path.join(os.path.dirname(__file__), "data"))
from database_manager import DatabaseManager

def track_jobs(machine):
    '''
    job_details: (job_id, system_id, queue_id, no_nodes, no_cpus, submit_time, start_time,
                  finish_time, exit_status, job_state)

    Job states:
    System state         DB state
    Q                    queuing (jobs currently in queue and have been estimated)
    R                    running (jobs currently running and have been estimated)
    T                    transiting (jobs in the process of being moved to a new destination)
    F                    finished (jobs that finished running or extracted from logs)
    F + exit_status > 0  failed (job failed running)
                         deleted (qstat -xf on specific job comes back as empty)
    '''
    print("%s Tracking finished jobs for %s..." % (str(datetime.now())[:-7], machine))

    connection = DM.machine_connect(machine)
    jobs = DBM.get_queued_jobs(machine)
    running_jobs = []
    finished_jobs = []
    failed_jobs = []

    for job in jobs:
        print("---")
        job_details = DM.query_machine(machine, connection, "qstat -xf %s" % job[1])

        if not job_details:
            print("# Job not found. Updating flag to 'deleted'...")
            DBM.update_workflow(job[0], "deleted")
        else:
            job_details = job_details[0]
            job_state = job_details["job_state"]

            if job_state == "R":
                start_time = DBM.date_to_db_format(DM.parse_time(job_details["stime"]))
                print("# Job running, updating start time to %s..." % start_time)
                # update_job(job_id, job_state, start_time=None, finish_time=None, exit_status=None)
                DBM.update_workflow(job[0], "running", start_time)
            else:
                exit_status = -1
                start_time = None
                finish_time = None
                qtime = None

                try:
                    exit_status = int(job_details["Exit_status"])
                    start_time = DM.parse_time(job_details["stime"])
                    finish_time = DM.parse_time(job_details["mtime"])
                    qtime = DM.parse_time(job_details["qtime"])
                except:
                    print("# Job state: %s and no exit status. Skipping..." % job_state)

                if start_time and finish_time and qtime and exit_status == 0:
                    print("# Job finished, updating details...")
                    estimated_waittime = int(DBM.get_estimated_waittime(job[0]))
                    actual_waittime = timeparse(str(start_time - qtime))
                    error_waittime = estimated_waittime - actual_waittime

                    requested_walltime = timeparse(job_details["Resource_List.walltime"])
                    actual_walltime = timeparse(job_details["resources_used.walltime"])
                    error_walltime = requested_walltime - actual_walltime

                    DBM.update_workflow(job[0], "finished", start_time, finish_time, exit_status)
                    # insert_waittime(job_id, estimated_waittime, actual_waittime=None, error=None)
                    DBM.insert_waittime(job[0], estimated_waittime, actual_waittime, abs(error_waittime))
                    # insert_waittime(job_id, requested_walltime, actual_walltime=None, error=None)
                    DBM.insert_walltime(job[0], requested_walltime, actual_walltime, abs(error_walltime))
                elif exit_status > 0:
                    print("# Job failed, updating details...")
                    DBM.update_workflow(job[0], "failed", start_time, finish_time, exit_status)


if __name__ == "__main__":
    DM = DecisionMaker(os.path.join(os.path.dirname(__file__), 'data/jobs_database.db'))
    DBM = DatabaseManager(os.path.join(os.path.dirname(__file__), 'data/jobs_database.db'))
    machines = DBM.get_machine_names()

    for machine in machines:
        track_jobs(machine)
    