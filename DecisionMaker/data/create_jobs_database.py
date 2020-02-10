'''This script creates a database for jobs to be stored
into for improved tracking and querying.
'''
import sqlite3
from database_manager import DatabaseManager


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
                machine_name text PRIMARY KEY NOT NULL,
                host text NOT NULL,
                available_nodes integer NOT NULL,
                cores_per_node integer NOT NULL,
                scheduler text NOT NULL,
                UNIQUE (machine_name, host)
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
                queue_name text NOT NULL,
                machine_name text NOT NULL,
                max_nodes integer NOT NULL,
                min_time text NOT NULL,
                max_time text NOT NULL,
                default_queue integer NOT NULL DEFAULT 0,
                FOREIGN KEY (machine_name) REFERENCES Machines(machine_name) ON DELETE CASCADE,
                UNIQUE (queue_name, machine_name)
            )'''
        )

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def create_jobs_table():
    '''This function creates a Jobs table holding all the job details. This has as FKs the queue
    id and the machine ID. The PK of this table acts as FK for Waittimes and Walltimes tables.'''
    try:
        print("Creating Jobs table...")
        CURSOR.execute('''DROP TABLE IF EXISTS Jobs''')
        CURSOR.execute(
            '''CREATE TABLE Jobs (
                job_id text PRIMARY KEY NOT NULL,
                system_job_id text NOT NULL,
                queue_id text NOT NULL,
                no_nodes integer NOT NULL,
                no_cpus integer NOT NULL,
                FOREIGN KEY (queue_id) REFERENCES Queues(queue_id) ON DELETE CASCADE,
                UNIQUE (system_job_id, queue_id)
            )'''
        )

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


def create_workflow_table():
    '''This function creates a Workflow table holding the different stages of every job
    and the dates of when these states have been achieved. This has been created in order
    to support state tracking on the user interface.'''
    try:
        print("Creating Workflow table...")
        CURSOR.execute('''DROP TABLE IF EXISTS Workflow''')
        CURSOR.execute(
            '''CREATE TABLE Workflow (
                job_id text PRIMARY KEY NOT NULL,
                submit_time text,
                queue_time text,
                start_time text,
                transit_time text,
                finish_time text,
                current_state text,
                exit_status integer,
                FOREIGN KEY (job_id) REFERENCES Jobs(job_id) ON DELETE CASCADE,
                UNIQUE (job_id, submit_time)
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
                            estimated_waittime text NOT NULL,
                            actual_waittime text,
                            error text,
                            FOREIGN KEY (job_id) REFERENCES Jobs(job_id) ON DELETE CASCADE
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
        CURSOR.execute('''CREATE TABLE Walltimes (
                            job_id text PRIMARY KEY NOT NULL,
                            requested_walltime text NOT NULL,
                            actual_walltime text,
                            error text,
                            FOREIGN KEY (job_id) REFERENCES Jobs(job_id) ON DELETE CASCADE
                        )''')

        CONNECTION.commit()
    except sqlite3.Error as err:
        print("An error occurred:", err.args[0])


if __name__ == "__main__":
    DBM = DatabaseManager('jobs_database.db')
    CONNECTION, CURSOR = DBM.get_connection()

    print("CREATING FRESH DATABASE...")
    create_machines_table()
    create_queues_table()
    create_jobs_table()
    create_workflow_table()
    create_waittimes_table()
    create_wallimes_table()
    DBM.disconnect()
