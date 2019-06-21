'''This script is used by the database creator, populator, Decision
Maker and live trackers.
'''
from datetime import datetime
import sqlite3
import sys


class DatabaseManager:
    '''This script creates a database query object that holds
    general queries for the SQLite jobs database.
    '''
    def __init__(self, database_path):
        '''This function connects to sqlite and creates a cursor
        that is passed on to every function to avoid creation
        of multiple connections.'''
        print("%s Connecting to sqlite..." % str(datetime.now())[:-7])
        try:
            connection = sqlite3.connect(database_path)
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")

        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        self.connection = connection
        self.cursor = cursor

    def get_connection(self):
        '''This function returns the connection and cursor'''
        return self.connection, self.cursor


    def disconnect(self):
        '''This function disconnects from the database'''
        print("%s Disconnecting from the database..." % str(datetime.now())[:-7])
        self.connection.close()


    def date_to_db_format(self, date):
        '''This function takes in a date object and parses it to the DB date format
        before being inserted'''
        return date.strftime("%Y-%m-%d %H:%M:%S")


    def get_queue_id(self, queue_name):
        '''This function returns the queue id from the Queues table
        given the queue name'''
        queue_id = ()
        try:
            self.cursor.execute('''SELECT queue_id FROM Queues
                                   WHERE queue_name= ?''', (queue_name,))

            queue_id = self.cursor.fetchone()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return queue_id


    def get_queue_name(self, job_id):
        '''This function returns the queue name of the specified job by id'''
        queue = ""
        try:
            self.cursor.execute('SELECT queue FROM Jobs WHERE job_id=?', (job_id,))

            queue = self.cursor.fetchone()[0]
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return queue


    def get_standard_queue(self, machine):
        '''This function gets the default queue for the specified machine
        from the jobs database.
        '''
        print("# Getting default queue from database...")
        standard_queue = ""
        try:
            self.cursor.execute('''SELECT queue_name FROM Queues
                                   WHERE machine_name=?
                                   AND default_queue=1''', (machine,))

            standard_queue = self.cursor.fetchone()[0]
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return standard_queue


    def get_machine_names(self):
        '''This function returns a list containing the names of all
        machines in the Machine table'''
        print("# Getting machine names from database...")
        machine_names = []
        try:
            self.cursor.execute('SELECT machine_name FROM Machines')

            machine_names = self.cursor.fetchall()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return [machine[0] for machine in machine_names]


    def get_machine_nodes(self, machine):
        '''This function returns the number of available nodes for the
        specified machine from the Machines table'''
        print("# Getting machine available nodes from database...")
        available_nodes = ""
        try:
            self.cursor.execute('''SELECT available_nodes FROM Machines
                                   WHERE machine_name = ?''', (machine, ))

            available_nodes = self.cursor.fetchone()[0]
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return available_nodes


    def insert_machine(self, machine):
        '''This function takes a machine disctionary and inserts it into the Machines table

        Machines table columns:
        - Machine table structure:
        - machine_name text PRIMARY KEY NOT NULL
        - host text NOT NULL
        - available_nodes integer NOT NULL
        - cores_per_node integer NOT NULL
        - scheduler text NOT NULL
        
        Data structures:
        machine: {"machine_name": "", "host": "", "available_nodes": "", "cores_per_node": "",
                  "scheduler": ""}
        '''
        try:
            print("## Inserting machine %s..." % machine["machine_name"])
            self.cursor.execute('INSERT INTO Machines VALUES (?, ?, ?, ?, ?)',
                                (machine["machine_name"], machine["host"], machine["available_nodes"],
                                 machine["cores_per_node"], machine["scheduler"])
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def insert_queue(self, queue):
        '''This function takes a queue disctionary and inserts it into the Queues table

        Queues table columns:
        - queue_id text PRIMARY KEY NOT NULL,
        - queue_name text NOT NULL,
        - machine_name text NOT NULL,
        - max_nodes integer NOT NULL,
        - min_time text NOT NULL,
        - max_time text NOT NULL
        - default_queue integer NOT NULL DEFAULT 0
        
        Data structures:
        queue: {"queue_id": "", "queue_name": "", "machine_name": "", "max_nodes": "",
                "min_time": "", "max_time": "", "default_queue": ""}
        '''
        try:
            print("## Inserting queue %s belonging to %s..." % (queue["queue_name"], queue["machine_name"]))
            self.cursor.execute('INSERT INTO Queues VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (queue["queue_id"], queue["queue_name"], queue["machine_name"],
                                 queue["max_nodes"], queue["min_time"], queue["max_time"], queue["default_queue"])
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def insert_job(self, job):
        '''This function takes a job object as input and inserts it into the Jobs table

        Job Table Columns:
        - job_id text PRIMARY KEY NOT NULL,
        - system_id text NOT NULL,
        - queue_id text NOT NULL,
        - no_nodes integer NOT NULL,
        - no_cpus integer NOT NULL,
        - submit_time text NOT NULL,
        - start_time text,
        - finish_time text,
        - exit_status integer,
        - job_state text NOT NULL
        
        Data structures:
        job: {"job_id": "", "system_id": "", "queue_is": "", "no_nodes": "", "no_cpus": "", "submit_time": "",
              "start_time": "", "finish_time": "", "exit_status": "",
              "wall_time": "", "job_state": "", "estimated_waittime": "", "machine": ""}
        '''
        print("## Inserting job %s belonging to queue %s..." % (job["job_id"], job["queue_id"]))
        try:
            self.cursor.execute('''INSERT INTO Jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (job["job_id"], job["system_id"], job["queue_id"], job["no_nodes"],
                                    job["no_cpus"], job["submit_time"], job["start_time"], job["finish_time"],
                                    job["exit_status"], job["job_state"])
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def update_job(self, job_id, job_state, start_time=None, finish_time=None, exit_status=None):
        '''This function updates the job_status flag and on the Jobs table'''
        print("# Updating job %s..." % job_id)
        try:
            self.cursor.execute('''UPDATE Jobs SET start_time = ?, finish_time = ?, exit_status = ?,
                                   job_state = ? WHERE job_id = ?''', (
                                        start_time, finish_time, exit_status, job_state, job_id
                                   )
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def get_job_id(self, system_id):
        '''This function returns the job db id with a given system id'''
        print("# Getting Job DB ID...")
        job_id = ''
        try:
            self.cursor.execute('SELECT job_id FROM Jobs WHERE system_id = ?', (system_id,))
            job_id = self.cursor.fetchone()[0]
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return job_id


    def insert_waittime(self, job_id, estimated_waittime, actual_waittime=None, error=None):
        '''This function inserts the estimated time for a job to wait in the queue
        depending on the job size into the Waittimes table. This is usually used for
        tracking data. This is usually used before the job starts running, while it is
        still waiting in the queue.

        Waittimes Table Columns:
        - job_id text PRIMARY KEY NOT NULL
        - estimated_waittime text NOT NULL
        - actual_waittime text
        - error text

        Data structures:
        job_id: str
        waittime: int (seconds)
        '''
        print("## Inserting waittime for job %s..." % job_id)
        try:
            self.cursor.execute('INSERT OR REPLACE INTO Waittimes VALUES (?, ?, ?, ?)',
                                 (job_id, estimated_waittime, actual_waittime, error)
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def get_estimated_waittime(self, job_id):
        '''This function queries the Waittimes table with a job id and returns the estimated waittime'''
        print("## Getting estimated waittime for job %s..." % job_id)
        estimated_waittime = ""
        try:
            self.cursor.execute('SELECT estimated_waittime FROM Waittimes WHERE job_id = ?', (job_id,))
            estimated_waittime = self.cursor.fetchone()[0]
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return estimated_waittime


    def insert_walltime(self, job_id, requested_walltime, actual_walltime=None, error=None):
        '''This function inserts the requested walltime, the actual walltime and the error rate
        between the two for a job in the Walltimes table. This is usually used for log data.
        
        Walltimes Table Columns:
        - job_id text PRIMARY KEY NOT NULL,
        - requested_walltime text NOT NULL,
        - actual_walltime text,
        - error text

        Data structures:
        walltime: {"job_id": "", "requested_walltime": "", "actual_walltime": "", "error": ""}
        '''
        print("## Inserting walltime for job %s..." % "job_id")
        try:
            self.cursor.execute('INSERT OR REPLACE INTO Walltimes VALUES (?, ?, ?, ?)', (
                                    job_id, requested_walltime, actual_walltime, error)
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def get_queued_jobs(self, machine):
        '''This function queries the Jobs table and extracts all the jobs with job_state "queuing".
        This is usually used by track_finished.py to track jobs and extract data after they finish running'''
        print("# Extracting jobs with status 'queuing' from the database...")
        jobs = []
        try:
            self.cursor.execute('''SELECT * FROM Jobs AS J
                                   INNER JOIN Queues AS Q ON J.queue_id = Q.queue_id
                                   WHERE Q.machine_name = ?
                                   AND J.job_state = "queuing";''', (machine,))

            jobs = self.cursor.fetchall()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return jobs


if __name__ == "__main__":
    DBM = DatabaseManager(str(sys.argv[1]))
    print(DBM.get_machine_nodes('ARCHER'))
