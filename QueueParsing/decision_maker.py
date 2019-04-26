'''Decision maker for the submission of jobs based on the time
   required for it to wait to be processed by different machines.

   This takes into consideration the node hours required for queued
   jobs to run added to the number of node hours required for the
   running jobs to finish processing.

   Note: This is based on GG's pbs.py
'''
from __future__ import print_function
from datetime import datetime, timedelta
import sys
from pytimeparse.timeparse import timeparse
sys.path.append("../")
import ConnectionManager

CURRENT_TIME = datetime.today()

def parse_response(queue_data):
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
            num = ""

            for char in line:
                if char.isdigit():
                    num += char

            job = {}
            job["JobID"] = num
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


def parse_file(fname, result):
    '''Parses the string response from the qstat command and stores
       it in a file. This then makes use of the parse_response funct.
       to return an array of job objects.
    '''
    write_jobs = open(fname, "w")
    write_jobs.write(result.stdout)
    write_jobs.close()

    read_jobs = open(fname, "r")
    print("Reading queue data in %s" % fname)
    data = read_jobs.readlines()
    read_jobs.close()

    return parse_response(data)


def get_queue(name, jobs):
    '''Returns an array of the jobs that are currently in the
       specified queue.

       Types of queue:
       - standard
       - short
       - long
       - largemem
    '''
    queue = []

    for job in jobs:
        if job["queue"] == name:
            queue.append(job)

    return queue


def get_queued(jobs):
    '''Returns an array of the jobs that are currently in the
       queue waiting to be processed.
    '''
    queued = []

    for job in jobs:
        if job["job_state"] == "Q":
            queued.append(job)

    return queued


def get_running(jobs):
    '''Returns an array of the jobs that are currently being
       processed.
    '''
    running = []

    for job in jobs:
        if job["job_state"] == "R":
            running.append(job)

    return running


def parse_time(time_string):
    '''Parses a time string and returns a datetime object of
       format "Tue Apr 16 13:17:58 2019"
    '''
    time = datetime.strptime(time_string, "%a %b %d %H:%M:%S %Y")

    return time


def get_job_nodes(job):
    '''Returns the number of nodes a job has requested for.
    '''
    return int(job["Resource_List.nodect"])


def get_jobs_wait_time(jobs):
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
        no_nodes = get_job_nodes(job)

        if job["job_state"] == "Q":
            wait_time += walltime*no_nodes
        else:
            ran_time = CURRENT_TIME - parse_time(job["stime"])
            left_time = timeparse(job["Resource_List.walltime"]) - ran_time.total_seconds()
            wait_time += left_time*no_nodes

    return wait_time


def get_total_wait_time(machine):
    '''This makes use of the ConnectionManager to connect to a specified
       machine, perform a qstat, save the response to a file via the
       parse_file function which returns an array of jobs. This is then
       separated into queued and running jobs and used to calculate the
       expected wait time. The expected wait time is then divided by the
       number of compute nodes available on the specified machine.

       Note: perhaps the number of compute nodes could come from a profile
       of the machines via the ConnectionManager? This profile could perhaps
       also hold the types of queues and their limits.
    '''
    print("---")
    print("Connecting to %s" % machine)
    connection = ConnectionManager.RemoteConnection(machine)
    print("Querying the queue...")
    result = connection.ExecuteCommand("qstat -f")

    jobs = parse_file("queuedata.txt", result)
    queued = get_queued(jobs)
    running = get_running(jobs)

    queued_time = get_jobs_wait_time(queued)
    running_time = get_jobs_wait_time(running)
    total_nodes = 4920 if machine == 'ARCHER' else 280
    total_time = (queued_time/total_nodes)+(running_time/total_nodes)

    wait_time = str(timedelta(seconds=total_time))
    print("Estimated total wait time for %s is: %s" % (machine, wait_time[:-7]))

    return total_time


def make_decision():
    '''This function gets the total estimated wait time for multiple machines
       and compares the results in order to decide which machine is less busy
       and where the next job could be sumbitted to.
    '''
    archer_wait_time = get_total_wait_time('ARCHER')
    cirrus_wait_time = get_total_wait_time('CIRRUS')

    if archer_wait_time < cirrus_wait_time:
        print("Submitting job to ARCHER...")
    else:
        print("Submitting job to CIRRUS...")


if __name__ == "__main__":
    make_decision()
