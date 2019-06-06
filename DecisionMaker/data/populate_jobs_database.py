# -*- coding: utf-8 -*-
'''This script populates the SQLite database created
with the use of the create_jobs_database script.
'''
from glob import glob
import sqlite3
import uuid
import csv
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../ConnectionManager"))
from machines import machines


def connect():
    '''This function connects to sqlite and creates a cursor
    that is passed on to every function to avoid creation
    of multiple connections.'''
    print("Connecting to sqlite...")
    try:
        connection = sqlite3.connect('jobs_database.db')
        cursor = connection.cursor()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])

    return connection, cursor


def populate_machines_table():
    '''This function populates the Machine table with
    a generated UUID, the machine name and the total nodes
    available.

    Machines table columns:
    - machine_id text PRIMARY KEY NOT NULL,
    - machine_name text NOT NULL,
    - host text NOT NULL,
    - available_nodes integer NOT NULL,
    - cores_per_node integer NOT NULL'''
    print("Populating Machines table...")
    machines_list = []

    for machine in machines:
        machine_id = str(uuid.uuid4())
        machine_tuple = (machine_id, machine, machines[machine]["host"],
                         machines[machine]["available_nodes"],
                         machines[machine]["cores_per_node"])

        machines_list.append(machine_tuple)
        machines[machine]["machine_id"] = machine_id

    try:
        CURSOR.executemany('INSERT INTO Machines VALUES (?, ?, ?, ?, ?)', machines_list)
        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def populate_queues_table():
    '''This function populates the Queues table with
    a generated UUID, the queue name, the machine id,
    the maximum number of nodes allocated, the maximum
    time allowed, the limit of available nodes.

    Queues table columns:
    - queue_id text PRIMARY KEY NOT NULL,
    - machine text NOT NULL,
    - queue_name text NOT NULL,
    - max_nodes integer NOT NULL,
    - min_time text NOT NULL,
    - max_time text NOT NULL'''
    print("Populating Queues table...")
    queues_list = []

    for machine in machines:
        machine_id = machines[machine]["machine_id"]
        for queue in machines[machine]["queues"]:
            queue_id = str(uuid.uuid4())
            queue_tuple = (queue_id, machine_id, queue["queue_name"], queue["max_nodes"],
                           queue["min_time"], queue["max_time"])

            queues_list.append(queue_tuple)

    try:
        CURSOR.executemany('INSERT INTO Queues VALUES (?, ?, ?, ?, ?, ?)', queues_list)
        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def import_from_csv(file_name):
    '''This function imports logs of finished jobs for both
    ARCHER and CIRRUS from csv files and creates a list of job
    objects to be used for the population of the SQLite database.

    Track statuses:
    - phase0 (new)
    - phase1 (estimated for queuing jobs)
    - phase2 (actual data from finished jobs)
    - lost (jobs that cannot be traced anymore)
    '''
    print("Importing data from file...")
    with open(file_name, mode='r', encoding='utf-8-sig') as jobs_file:
        parsed_jobs = csv.DictReader(jobs_file)

        jobs = []
        for row in parsed_jobs:
            queue = get_queue_id(row['queue'].strip())

            if queue is not None:
                job = {}
                job["job_ID"] = row['id_string'].strip()[:-4]
                job["no_nodes"] = row['node_count'].strip()
                job["no_cpus"] = row['ncpus'].strip()
                job["queue"] = queue[0]
                job["submit_time"] = row['submit_time(date)'].strip()
                job["start_time"] = row['start_time(date)'].strip()
                job["finish_time"] = row['end_time(date)'].strip()
                job["run_time"] = int(row['runtime(s)'].strip())
                job["exit_status"] = row['exit_status'].strip()
                job["wait_time"] = int(row['waittime(s)'].strip())
                job["wall_time"] = int(row["walltime(s)"].strip())
                job["track_status"] = 'tracked'

                jobs.append(job)

    return jobs


def get_queue_id(queue_name):
    '''This function queries the database for a queue id
    based on the queue name.

    Note: this should probably also take into consideration
    the machine'''
    try:
        CURSOR.execute('''SELECT queue_id FROM Queues
                          WHERE queue_name=?''', (queue_name,))

        queue_id = CURSOR.fetchone()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])

    return queue_id


def populate_jobs_table(jobs):
    '''This function makes use of most of the job object
    attributes to populate the Jobs table.

    Job Table Columns:
    - job_id text PRIMARY KEY NOT NULL,
    - no_nodes integer NOT NULL,
    - no_cpus integer NOT NULL,
    - queue text NOT NULL,
    - submit_time text NOT NULL,
    - start_time text,
    - finish_time text,
    - run_time text,
    - exit_status integer,
    - track_status text NOT NULL'''
    print("Populating Jobs table...")
    jobs_list = []
    for job in jobs:
        job_tuple = (job['job_ID'], job['no_nodes'], job['no_cpus'],
                     job['queue'], job['submit_time'], job['start_time'],
                     job['finish_time'], job['run_time'], job['exit_status'],
                     job['track_status'])

        jobs_list.append(job_tuple)

    try:
        CURSOR.executemany('INSERT INTO Jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', jobs_list)
        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def populate_walltimes_table(jobs):
    '''This function makes use of most of the job object
    attributes to populate the Walltimes table.

    Walltimes Table Columns:
    - job_id text PRIMARY KEY NOT NULL,
    - requested_walltime text NOT NULL,
    - actual_walltime text,
    - error text'''
    print("Populating Walltimes table...")
    times_list = []
    for job in jobs:
        error_rate = job["wall_time"] - job["run_time"]
        time_tuple = (job["job_ID"], job["wall_time"], job["run_time"], error_rate)

        times_list.append(time_tuple)

    try:
        CURSOR.executemany('INSERT INTO Walltimes VALUES (?, ?, ?, ?)', times_list)
        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


if __name__ == "__main__":
    CONNECTION, CURSOR = connect()
    populate_machines_table()
    populate_queues_table()

    JOBS_FILES = glob("*/*.csv")

    for job_file in JOBS_FILES:
        imported_jobs = import_from_csv(job_file)
        populate_jobs_table(imported_jobs)
        populate_walltimes_table(imported_jobs)
