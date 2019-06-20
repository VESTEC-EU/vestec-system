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
        print(("{0} Connecting to sqlite...").format(datetime.now()))
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
        print(("{0} Disconnecting from the database...").format(datetime.now()))
        self.connection.close()


    def get_queue_id(self, queue_name):
        '''This function returns the queue id from the Queues table
        given the queue name'''
        try:
            self.cursor.execute('''SELECT queue_id FROM Queues
                                   WHERE queue_name= ?''', (queue_name,))

            queue_id = self.cursor.fetchone()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return queue_id


    def get_queue_name(self, job_id):
        '''This function returns the queue name of the specified job by id'''
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
        print("Getting default queue from database...")
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
        print("Getting machine names from database...")
        try:
            self.cursor.execute('SELECT machine_name FROM Machines')

            machine_names = self.cursor.fetchall()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return [machine[0] for machine in machine_names]


    def get_machine_nodes(self, machine):
        '''This function returns the number of available nodes for the
        specified machine from the Machines table'''
        print("Getting machine available nodes from database...")
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
            print(("## Inserting machine {0}...").format(machine["machine_name"]))
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
            print(("## Inserting queue {0} belonging to {1}...").format(queue["queue_name"], queue["machine_name"]))
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
        - run_time text,
        - exit_status integer,
        - track_status text NOT NULL
        
        Data structures:
        job: {"job_id": "", "system_id": "", "queue_is": "", "no_nodes": "", "no_cpus": "", "submit_time": "",
              "start_time": "", "finish_time": "", "run_time": "", "exit_status": "",
              "wall_time": "", "track_status": "", "estimated_waittime": "", "machine": ""}
        '''
        print(("## Inserting job {0} belonging to queue {1}...").format(job["job_id"], job["queue_id"]))
        try:
            self.cursor.execute('''INSERT INTO Jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (job["job_id"], job["system_id"], job["queue_id"], job["no_nodes"],
                                    job["no_cpus"], job["submit_time"], job["start_time"], job["finish_time"],
                                    job["run_time"], job["exit_status"], job["track_status"])
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def update_job(self, job):
        '''This function takes a job object as input and updates its already existent entry into the Jobs table'''
        print(("## Updating job {0} belonging to queue {1}...").format(job["job_id"], job["queue_id"]))
        try:
            self.cursor.execute('''UPDATE Jobs SET job_id = ?, system_id = ?, queue_id = ?, no_nodes = ?,
                                   no_cpus = ?, submit_time = ?, start_time = ?, finish_time = ?,
                                   run_time = ?, exit_status = ?, track_status = ?''',
                                   (job["job_id"], job["system_id"], job["queue_id"], job["no_nodes"],
                                    job["no_cpus"], job["submit_time"], job["start_time"], job["finish_time"],
                                    job["run_time"], job["exit_status"], job["track_status"])
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def insert_estimated_waittime(self, job_id, waittime):
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
        print(("## Inserting estimated waittime for job {0}...").format(job_id))
        try:
            self.cursor.execute('INSERT INTO Waittimes (job_id, estimated_waittime) VALUES (?, ?)',
                                 (job_id, waittime)
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def insert_actual_waittime(self, job_id, waittime):
        '''This function inserts the actual waittime (queue time) and the error rate for a
        job in the Waittimes table. This is usually used for tracking data, after the job
        finished queuing.

        Waittimes Table Columns:
        - job_id text PRIMARY KEY NOT NULL
        - estimated_waittime text NOT NULL
        - actual_waittime text
        - error text

        Data structures:
        job_id: str
        waittime: int (seconds)
        '''
        try:
            print(("## Inserting actual waittime for job {0}...").format(job_id))
            self.cursor.execute('''INSERT INTO Waittimes (actual_waittime) VALUES (?)
                                   WHERE job_id = ?''', (waittime, job_id)
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        try:
            print("### Inserting waittime error rate...")
            self.cursor.execute('''UPDATE Waittimes SET error = estimated_waittime - actual_waittime
                                   WHERE job_id = ?''', (job_id, )
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def insert_full_walltime(self, walltime):
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
        print(("## Inserting walltime for job {0}...").format(walltime["job_id"]))
        try:
            self.cursor.execute('INSERT INTO Walltimes VALUES (?, ?, ?, ?)', (
                                    walltime["job_id"], walltime["requested_walltime"],
                                    walltime["actual_walltime"], walltime["error"])
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def insert_requested_walltime(self, job_id, walltime):
        '''This function inserts the requested walltime for a job in the Walltimes table.
        This is usually used for tracking data, before the job finished running.

        Data structures:
        job_id: str
        walltime: int (seconds)
        '''
        print(("## Inserting requested walltime for job {0}...").format(job_id))
        try:
            self.cursor.execute('INSERT INTO Walltimes (job_id, requested_walltime) VALUES (?, ?)',
                                 (job_id, walltime)
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

            
    def insert_actual_walltime(self, job_id, walltime):
        '''This function inserts the actual walltime (run time) and the error rate for a
        job in the Walltimes table. This is usually used for tracking data, after the job
        finished running.

        Data structures:
        job_id: str
        walltime: int (seconds)
        '''
        try:
            print(("## Inserting actual walltime for job {0}...").format(job_id))
            self.cursor.execute('''INSERT INTO Walltimes (actual_walltime) VALUES (?)
                                   WHERE job_id = ?''', (walltime, job_id)
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        try:
            print("### Inserting walltime error rate...")
            self.cursor.execute('''UPDATE Walltimes SET error = requested_walltime - actual_walltime
                                   WHERE job_id = ?''', (job_id, )
                               )
            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


if __name__ == "__main__":
    DBM = DatabaseManager(str(sys.argv[1]))
    print(DBM.get_machine_nodes('ARCHER'))
