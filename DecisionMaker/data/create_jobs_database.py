'''This script creates a database for jobs to be stored
into for improved tracking and querying.
'''
import sqlite3
from DatabaseManager import DatabaseManager


def create_machines_table():
    '''This function creates a Machines table holding
    the machine name and the number of available nodes.
    The PK of this table is to be used as FK in table
    Queues.'''
    try:
        print("Creating Machines table...")
        CURSOR.execute('''DROP TABLE IF EXISTS Machines''')
        CURSOR.execute(
            '''CREATE TABLE Machines (
                machine_id text PRIMARY KEY NOT NULL,
                machine_name text NOT NULL,
                host text NOT NULL,
                available_nodes integer NOT NULL,
                cores_per_node integer NOT NULL,
                UNIQUE (machine_name, host) ON CONFLICT REPLACE
            )'''
        )

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def create_queues_table():
    '''This function creates a Queues table holding
    the queue name, the node and time limit and what
    machine they belong to. The PK of this table is
    to be used as FK in table Jobs. This also holds
    the machine id as FK from the Machines table'''
    try:
        print("Creating Queues table...")
        CURSOR.execute('''DROP TABLE IF EXISTS Queues''')
        CURSOR.execute(
            '''CREATE TABLE Queues (
                queue_id text PRIMARY KEY NOT NULL,
                machine text NOT NULL,
                queue_name text NOT NULL,
                max_nodes integer NOT NULL,
                min_time text NOT NULL,
                max_time text NOT NULL,
                default_queue integer NOT NULL DEFAULT 0,
                FOREIGN KEY (machine) REFERENCES Machines(machine_id),
                UNIQUE (machine, queue_name) ON CONFLICT REPLACE
            )'''
        )

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def create_jobs_table():
    '''This function creates a Jobs table holding
    all the job details. This has as FKs the queue
    id and the machine ID. The PK of this table acts
    as FK for Waittimes and Walltimes tables.'''
    try:
        print("Creating Jobs table...")
        CURSOR.execute('''DROP TABLE IF EXISTS Jobs''')
        CURSOR.execute(
            '''CREATE TABLE Jobs (
                job_id text PRIMARY KEY NOT NULL,
                no_nodes integer NOT NULL,
                no_cpus integer NOT NULL,
                queue text NOT NULL,
                submit_time text NOT NULL,
                start_time text,
                finish_time text,
                run_time text,
                exit_status integer,
                track_status text NOT NULL,
                FOREIGN KEY (queue) REFERENCES Queues(queue_id)
                UNIQUE (job_id, queue) ON CONFLICT REPLACE
            )'''
        )

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def create_waittimes_table():
    '''This function creates a Waittimes table holding
    the estimated and actual wait time in queue for
    every job in the jobs table. This table makes use
    of the job_ID from table Jobs as FK.'''
    try:
        print("Creating Waittimes table...")
        CURSOR.execute('''DROP TABLE IF EXISTS Waittimes''')
        CURSOR.execute('''CREATE TABLE Waittimes (
                            job_id text PRIMARY KEY NOT NULL,
                            queue text NOT NULL,
                            estimated_waittime text NOT NULL,
                            actual_waittime text,
                            error text,
                            FOREIGN KEY (job_id) REFERENCES Jobs(job_id)
                            UNIQUE (job_id, queue) ON CONFLICT REPLACE
                          )''')

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def create_wallimes_table():
    '''This function creates a Walltimes table holding
    the requested and actual walltime in queue for
    every job in the jobs table. This table makes use
    of the job_ID from table Jobs as FK.'''
    try:
        print("Creating Walltimes table...")
        CURSOR.execute('''DROP TABLE IF EXISTS Walltimes''')
        CURSOR.execute(
            '''CREATE TABLE Walltimes (
                job_id text PRIMARY KEY NOT NULL,
                queue text NOT NULL,
                requested_walltime text NOT NULL,
                actual_walltime text,
                error text,
                FOREIGN KEY (job_id) REFERENCES Jobs(job_id),
                UNIQUE (job_id, queue) ON CONFLICT REPLACE
            )'''
        )

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


if __name__ == "__main__":
    DBM = DatabaseManager('jobs_database.db')
    CONNECTION, CURSOR = DBM.get_connection()
    create_machines_table()
    create_queues_table()
    create_jobs_table()
    create_waittimes_table()
    create_wallimes_table()
    DBM.disconnect()
