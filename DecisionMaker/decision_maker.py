
'''Decision maker for the submission of jobs based on the time
   required for it to wait to be processed by different machines.

   This takes into consideration the node hours required for queued
   jobs to run added to the number of node hours required for the
   running jobs to finish processing.

   Note: This is based on GG's pbs.py

   26.04.19 - v0.1 - BP: create basic decision maker based on the
                         average wait time of all jobs in queue
                         added to the remaining running time of
                         currently running jobs
   22.05.19 - v0.2 - BP: - upgrade decision maker to class
                         - take into consideration queue type
                         - take into consideration job size
   28.05.19 - v0.3 - BP: - separate machines to config file
                         - pass on job size to avoid overwriting
                         - pass on current time to consider on
                           make_decision, not class instantiation
                         - remove write to and read from file for
                           parsing machine response
   30.05.19 - v0.4 - BP: - separate machine connection from query
'''
from __future__ import print_function
from datetime import datetime, timedelta
import os
import logging
import sys
from pytimeparse.timeparse import timeparse
sys.path.append(os.path.join(os.path.dirname(__file__), "../ConnectionManager"))
from ConnectionManager import RemoteConnection
sys.path.append(os.path.join(os.path.dirname(__file__), "data"))
from database_manager import DatabaseManager

logging.basicConfig(filename='logging.log', level=logging.DEBUG)


class DecisionMaker:
    '''This class checks the availability of machines and tries
    to decide where to submit a job for faster processing'''
    def __init__(self, database_path):
        '''This function connects to the database'''
        self.DBM = DatabaseManager(database_path)

    def machine_connect(self, machine_name):
        '''Connects to machine and returns connection for use
        by query_machine'''
        logging.info("Connecting to %s...", machine_name)
        connection = RemoteConnection(machine_name)

        return connection


    def query_machine(self, machine_name, connection, command):
        '''Executes a qstat command, makes use of save_queuedata
        to save and parse the response and then selects jobs only
        from the standard queue.
        '''
        logging.info("Querying the queue...")
        stdout,stderr,exit_code = connection.ExecuteCommand(command)
        jobs = self.parse_machine_response((stdout).splitlines(True))

        standard_queue = self.DBM.get_standard_queue(machine_name)
        jobs = self.get_queue(standard_queue, jobs)

        return jobs


    def parse_machine_response(self, queue_data):
        '''Parses the qstat -f response from a file containing a single
        line of data to an array of job objects containing the
        required attributes for metrics measurements.

        Data Structures:
        jobs = [job, job, ...]
        job = {"JobID": int, }
        '''
        jobs = []

        for line in queue_data:
            if line[0:6] == "Job Id":
                job = {}
                job["JobID"] = line.split(":")[-1:][0].strip()
            elif line[0:4] == "    ":
                pair = line.split(" = ")
                key = pair[0].strip()
                value = pair[1].strip()
                job[key] = value
            elif line[0] == "\t":
                value = line.strip()
                job[key] += value
            elif line[0] == "\n":
                jobs.append(job)
            else:
                print(line)

        return jobs


    def get_queue(self, queue_name, jobs):
        '''Returns an array of the jobs that are currently in the
        specified queue (pulled from MACHINES).

        Types of queues depending on machine:
        ARCHER: standard, short, long, largemem, serial
        CIRRUS: workq, indy, large
        '''
        logging.info("Checking jobs of %s queue...", queue_name)
        queue = []

        for job in jobs:
            if job["queue"] == queue_name:
                queue.append(job)

        return queue


    def get_queued(self, jobs):
        '''Returns an array of the jobs that are currently in the
        queue waiting to be processed.
        '''
        logging.info("Extracting queuing jobs...")
        queued = []

        for job in jobs:
            if job["job_state"] == "Q":
                queued.append(job)

        return queued

    def cut_queue(self, jobs, job_size):
        '''Returns an array of the jobs that are currently in the
        queue waiting to be processed and are of the same size as the
        job to be submitted.
        '''
        logging.info("Cutting queuing jobs...")
        queued = []

        for job in jobs:
            if int(job["Resource_List.nodect"]) <= job_size:
                queued.append(job)

        return queued


    def get_running(self, jobs):
        '''Returns an array of the jobs that are currently being
        processed.
        '''
        logging.info("Extracting running jobs...")
        running = []

        for job in jobs:
            if job["job_state"] == "R":
                running.append(job)

        return running


    def parse_time(self, time_string):
        '''Parses a time string and returns a datetime object of
        format "Tue Apr 16 13:17:58 2019"
        '''
        return datetime.strptime(time_string, "%a %b %d %H:%M:%S %Y")


    def get_job_nodes(self, job):
        '''Returns the number of nodes a job has requested for.'''
        return int(job["Resource_List.nodect"])


    def get_jobs_wait_time(self, jobs):
        '''Returns an estimated wait time for a list of jobs. This list
        can contain either queued jobs or running jobs.

        For queued jobs: the sum of all queued jobs' expected time to
        process multiplied by the number of requested nodes.
        For running jobs: the sum of all queued jobs' time left to run
        multiplied by the number of requested nodes.
        '''
        wait_time = 0

        for job in jobs:
            walltime = timeparse(job["Resource_List.walltime"])  # seconds
            no_nodes = self.get_job_nodes(job)

            if job["job_state"] == "Q":
                wait_time += walltime*no_nodes
            elif job["job_state"] == "R":
                ran_time = datetime.now() - self.parse_time(job["stime"])
                left_time = timeparse(job["Resource_List.walltime"]) - ran_time.total_seconds()
                wait_time += left_time*no_nodes

        return wait_time


    def machine_wait_time(self, machine, jobs, job_size):
        '''This makes use of query_machine to connect to a specified
        machine, perform a qstat, save the response to a file via the
        parse_file function which returns an array of jobs. This is then
        separated into queued and running jobs and used to calculate the
        expected wait time. The expected wait time is then divided by the
        number of compute nodes available on the specified machine.

        Note: perhaps the MACHINE array could be expanded to contain more
        detailed profiles of the machines such as the number of compute
        nodes available for each machine? This profile could perhaps hold the
        types of queues and their limits.
        '''
        logging.info("Calculating wait time...")
        queued = self.get_queued(jobs)
        cut_queue = self.cut_queue(queued, job_size)
        running = self.get_running(jobs)

        queued_time = self.get_jobs_wait_time(cut_queue)
        running_time = self.get_jobs_wait_time(running)
        total_nodes = self.DBM.get_machine_nodes(machine)
        total_time = (queued_time/total_nodes)+(running_time/total_nodes)

        wait_time = timedelta(seconds=total_time)
        print("Estimated total wait time for %s is: %s" % (machine, str(wait_time)[:-7]))

        return wait_time


    def make_decision(self, job_size):
        '''This function gets the total estimated wait time for multiple machines
        and compares the results in order to decide which machine is less busy
        and where the next job could be sumbitted to.
        '''
        availability = {}
        machines = self.DBM.get_machine_names()

        for machine in machines:
            print("---")
            connection = self.machine_connect(machine)
            jobs = self.query_machine(machine, connection, "qstat -f")
            availability[machine] = self.machine_wait_time(machine, jobs, job_size)

        choice = min(availability, key=lambda k: availability[k]
                     if isinstance(availability[k], timedelta)
                     else timedelta.max
                    )

        print("Submitting to %s..." % choice)

if __name__ == "__main__":
    DM = DecisionMaker()
    DM.make_decision(1)  # number of nodes of job to submit
    