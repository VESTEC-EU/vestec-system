# -*- coding: utf-8 -*-
'''This script populates the SQLite database created
with the use of the create_jobs_database script.
'''
from datetime import datetime
from glob import glob
import sqlite3
import uuid
import csv
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../ConnectionManager"))
from machines import machines
from database_manager import DatabaseManager


def populate_machines_table():
    '''This function populates the Machine table with
    a generated UUID, the machine name and the total nodes
    available.

    Machines table columns:
    - Machine table structure:
    - machine_name text PRIMARY KEY NOT NULL
    - host text NOT NULL
    - available_nodes integer NOT NULL
    - cores_per_node integer NOT NULL
    - scheduler text NOT NULL
    '''
    print("# Populating Machines table...")

    for machine in machines:
        machine_obj = {"machine_name": machine, "host": machines[machine]["host"],
                       "available_nodes": machines[machine]["available_nodes"],
                       "cores_per_node": machines[machine]["cores_per_node"],
                       "scheduler": machines[machine]["scheduler"]}

        DBM.insert_machine(machine_obj)


def populate_queues_table():
    '''This function populates the Queues table with
    a generated UUID, the queue name, the machine id,
    the maximum number of nodes allocated, the maximum
    time allowed, the limit of available nodes.

    Queues table columns:
    - queue_id text PRIMARY KEY NOT NULL,
    - queue_name text NOT NULL,
    - machine_name text NOT NULL,
    - max_nodes integer NOT NULL,
    - min_time text NOT NULL,
    - max_time text NOT NULL
    - default_queue integer NOT NULL DEFAULT 0
    '''
    print("# Populating Queues table...")

    for machine in machines:
        default_queue = machines[machine]["main_queue"]

        for queue in machines[machine]["queues"]:
            queue["queue_id"] = str(uuid.uuid4())
            queue["machine_name"] = machine
            queue["default_queue"] = 1 if queue["queue_name"] == default_queue else 0

            DBM.insert_queue(queue)


def import_from_csv(file_name):
    '''This function imports logs of finished jobs for both
    ARCHER and CIRRUS from csv files and creates a list of job
    objects to be used for the population of the SQLite database.

    Track statuses:
    - queuing (jobs currently in queue and estimated)
    - finished (jobs that finished running and have all the data)
    '''
    print("# Importing data from file...")
    with open(file_name, mode='r', encoding='utf-8-sig') as jobs_file:
        parsed_jobs = csv.DictReader(jobs_file)

        jobs = []
        for row in parsed_jobs:
            queue = DBM.get_queue_id(row['queue'].strip())

            if queue is not None:
                job = {}
                job["job_id"] = str(uuid.uuid4())
                job["system_id"] = row['id_string'].strip()
                job["queue_id"] = queue[0]
                job["no_nodes"] = row['node_count'].strip()
                job["no_cpus"] = row['ncpus'].strip()
                job["submit_time"] = row['submit_time(date)'].strip()
                job["start_time"] = row['start_time(date)'].strip()
                job["finish_time"] = row['end_time(date)'].strip()
                job["run_time"] = int(row['runtime(s)'].strip())
                job["exit_status"] = row['exit_status'].strip()
                job["wait_time"] = int(row['waittime(s)'].strip())
                job["wall_time"] = int(row["walltime(s)"].strip())
                job["track_status"] = 'finished'

                jobs.append(job)

    return jobs


def populate_jobs(jobs):
    '''This function makes use of most of the job object attributes to populate the Jobs and
    the Walltimes table.'''
    print("# Populating Jobs and Walltimes tables...")

    for job in jobs:
        DBM.insert_job(job)

        error_rate = job["wall_time"] - job["run_time"]
        walltime = {"job_id": job["job_id"], "requested_walltime": job["wall_time"],
                    "actual_walltime": job["run_time"], "error": error_rate}

        DBM.insert_full_walltime(walltime)


if __name__ == "__main__":
    DBM = DatabaseManager('jobs_database.db')
    CONNECTION, CURSOR = DBM.get_connection()

    print("POPULATING FRESH DATABASE WITH LOG DATA...")
    populate_machines_table()
    populate_queues_table()

    JOBS_FILES = glob("*/*.csv")

    for job_file in JOBS_FILES:
        imported_jobs = import_from_csv(job_file)
        populate_jobs(imported_jobs)

    DBM.disconnect()
