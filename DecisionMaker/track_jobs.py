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
from decision_maker import DecisionMaker
sys.path.append(os.path.join(os.path.dirname(__file__), "data"))
from database_manager import DatabaseManager

'''To do:
- update to loop through machines, like estimate_active_jobs
- extract jobs from the database with tracking status 'queuing'
- use qstat -xf command to extract more info about these jobs
- select jobs with job_state = R
- use update function to update job_state in Jobs table to 'running'
- select jobs with job_state = F
- use update functions update_job, insert_actual_waittime and insert_actual_walltime from
DBM to insert the extracted data into the database
'''

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
        job_id = job[1]
        job_details = DM.query_machine(machine, connection, "qstat -xf %s" % job_id)
        job_id = DBM.get_job_id(job[1])

        if not job_details:
            print("# Job not found. Updating flag to 'deleted'...")
            DBM.update_job(job_id, "deleted")
        else:
            job_details = job_details[0]
            job_state = job_details["job_state"]

            if job_state == "R":
                start_time = DBM.date_to_db_format(DM.parse_time(job_details["stime"]))
                print("# Job running, updating start time to %s..." % start_time)
                # update_job(job_id, job_state, start_time=None, finish_time=None, exit_status=None)
                DBM.update_job(job_id, "running", start_time)
            else:
                try:
                    exit_status = int(job_details["Exit_status"])
                    start_time = DBM.date_to_db_format(DM.parse_time(job_details["stime"]))
                    finish_time = DBM.date_to_db_format(DM.parse_time(job_details["mtime"]))

                    if exit_status > 0:
                        print("# Job failed, updating details...")
                        DBM.update_job(job_id, "failed", start_time, finish_time, exit_status)
                    else:
                        print("# Job finished, updating details...")
                        estimated_waittime = int(DBM.get_estimated_waittime(job_id))
                        actual_waittime = timeparse(job_details["qtime"])
                        error_waittime = estimated_waittime - actual_waittime

                        requested_walltime = timeparse(job_details["Resource_list.walltime"])
                        actual_walltime = timeparse(job_details["resources_used.walltime"])
                        error_walltime = requested_walltime - actual_walltime

                        DBM.update_job(job_id, "finished", start_time, finish_time, exit_status)
                        # insert_waittime(job_id, estimated_waittime, actual_waittime=None, error=None)
                        DBM.insert_waittime(job_id, estimated_waittime, actual_waittime, error_waittime)
                        # insert_waittime(job_id, requested_walltime, actual_walltime=None, error=None)
                        DBM.insert_walltime(job_id, requested_walltime, actual_walltime, error_walltime)
                except:
                    print("# Job state: %s and no exit status. Skipping..." % job_state)


if __name__ == "__main__":
    DM = DecisionMaker('data/jobs_database.db')
    DBM = DatabaseManager('data/jobs_database.db')
    machines = DBM.get_machine_names()

    for machine in machines:
        track_jobs(machine)
    