'''This script is used by the database creator, populator, Decision
Maker and live trackers.
'''
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
        print("Connecting to sqlite...")
        try:
            connection = sqlite3.connect(database_path)
            cursor = connection.cursor()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        self.connection = connection
        self.cursor = cursor

    def get_connection(self):
        '''This function returns the connection and cursor'''
        return self.connection, self.cursor


    def disconnect(self):
        '''This function disconnects from the database'''
        print("Disconnecting from the database...")
        self.connection.close()


    def get_queue_id(self, queue_name):
        '''This function returns the queue id from the Queues table
        given the queue name'''
        try:
            self.cursor.execute('''SELECT queue_id FROM Queues
                                   WHERE queue_name=?''', (queue_name,))

            queue_id = self.cursor.fetchone()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])

        return queue_id


    def get_job_queue_name(self, job_id):
        '''This function returns the queue name of the queue id associated with a job'''
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
        standard_queue = ''
        try:
            self.cursor.execute('''SELECT queue_name FROM Queues AS Q
                                   INNER JOIN Machines AS M
                                   ON M.machine_id = Q.machine
                                   WHERE M.machine_name = ?
                                   AND Q.default_queue = 1''', (machine,))

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


    def insert_job(self, job):
        '''This function makes use of a job object to insert a new row in
        the Jobs table'''
        try:
            self.cursor.execute('''INSERT INTO Jobs
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                   (job["job_id"], job["no_nodes"], job["no_cpus"],
                                    job["queue"], job["submit_time"], job["start_time"],
                                    job["finish_time"], job["run_time"], job["exit_status"],
                                    job["track_status"]))

            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


    def insert_estimation(self, job_id, queue_id, estimation):
        '''This function is used to insert a new row in the Waittimes table'''
        try:
            self.cursor.execute('''INSERT INTO Waittimes
                                   VALUES (?, ?, ?, ?, ?)''', (job_id, queue_id,
                                   estimation, None, None))

            self.connection.commit()
        except sqlite3.Error as err:
            print("An error occurred:", err.args[0])


if __name__ == "__main__":
    DBM = DatabaseManager(str(sys.argv[1]))
    DBM.insert_estimation('6754637', 12, 106373)
