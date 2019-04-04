from __future__ import print_function
import datetime
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import sys
sys.path.append("../")
import ConnectionManager

CurrentTime = datetime.datetime.today()

#Parses a string containing output from a 'qstat -f' command
def Parse(QueueData):
    jobs=[]
    l=0

    for line in QueueData:
        l+=1
        #print(l)
        #print("|%s|"%line)
        if line[0:6] == "Job Id":
            num = ""
            for char in line:
                if char.isdigit(): num+=char
            #print("Processing job %s"%num)
            dict={}
            dict["JobID"] = num
        elif line[0:4] == "    ":
            pair = line.split(" = ")
            key=pair[0].strip()
            value=pair[1].strip()
            dict[key] = value
        elif line[0] == "\t":
            value = line.strip()
            dict[key] += value
        elif line[0] == "\n":
            jobs.append(dict)
        else:
            print("Dunno what to do...")
            print(line)

    return jobs

#parses string from a 'qstat -f' command which is stored in a file
def ParseFromFile(fname):
    f=open(fname,"r")
    print("Reading queue data in %s"%fname)
    data = f.readlines()
    f.close()
    return Parse(data)


def CountNodes(jobs):
    nodes=0
    for job in jobs:
        #if job["job_state"] == "R":
        nodes += int(job['Resource_List.nodect'])
    return nodes


def GetQueued(jobs):
    queued = []
    for job in jobs:
        if job["job_state"] == "Q":
            queued.append(job)
    return queued

def GetRunning(jobs):
    running=[]
    for job in jobs:
        if job["job_state"]=="R":
            running.append(job)
    return running

def GetHeld(jobs):
    held=[]
    for job in jobs:
        if job["job_state"]=="H":
            held.append(job)
    return held

def GetQueue(name,jobs):
    queue=[]
    for job in jobs:
        if job["queue"] == name:
            queue.append(job)
    return queue

def ParseTime(timestring):
    t=datetime.datetime.strptime(timestring,"%a %b %d %H:%M:%S %Y")
    return t

def ParseWalltime(job):
    s=job["Resource_List.walltime"]
    s=s.split(":")
    wt = 0.
    wt += float(s[0]) + 1./60*float(s[1]) + 1./3600.*float(int(s[2]))
    return wt

def GetWaitTime(job):
    qt = ParseTime(job["qtime"])
    if job["job_state"] == "Q":
        rt = CurrentTime
    else:
        rt=ParseTime(job["stime"])
    wt = rt-qt
    return(wt.total_seconds()/3600.)

def ParseNodeCount(job):
    return int(job["Resource_List.nodect"])


def GetEstimatedTime(walltime,size,jobs):
    #Calculates a weighted average of wait times in queue around the requested walltime and job size
    w=[]
    t=[]
    s=[]
    for job in jobs:
        w.append(ParseWalltime(job))
        s.append(ParseNodeCount(job))
        t.append(GetWaitTime(job))

    w=np.asarray(w)
    t=np.asarray(t)
    s=np.asarray(s)

    dw = np.max([walltime*0.2,1.])**2
    ds = np.max([size*0.2,1.])**2

    wgts = np.exp( -(w-walltime)**2/dw -(s-size)**2/ds)

    est = np.sum(wgts*t)/np.sum(wgts)

    #print("Walltime= %02.1f, Size = %03d, Estimated Time = %2.1f, error = %6.2f"%(walltime,size,est, np.sqrt(1./np.sum(wgts))))

    return est


if __name__ == "__main__":
    c=ConnectionManager.RemoteConnection("ARCHER")
    print("Querying the queue...")
    result = c.ExecuteCommand("qstat -f")

    print("\n\n\nWriting data to file to test ParseFromFile")
    f=open("queuedata.txt","w")
    f.write(result.stdout)
    f.close()

    jobs=ParseFromFile("queuedata.txt")

    queued = GetQueued(jobs)
    running = GetRunning(jobs)
    held = GetHeld(jobs)

    print("Number of Queued jobs is %d"%len(queued))
    print("Number of Running jobs is %d"%len(running))
    print("Number of Held jobs is %d"%len(held))
    print("Number of nodes in use is %d"%CountNodes(running))
    print("Number of requested nodes in queue is %d"%CountNodes(queued))

    print("\n\n\n")

    print("Parsing string from RemoteCommand directly")
    qstat = (result.stdout).splitlines(True)

    jobs=Parse(qstat)

    queued = GetQueued(jobs)
    running = GetRunning(jobs)
    held = GetHeld(jobs)

    print("Number of Queued jobs is %d"%len(queued))
    print("Number of Running jobs is %d"%len(running))
    print("Number of Held jobs is %d"%len(held))
    print("Number of nodes in use is %d"%CountNodes(running))
    print("Number of requested nodes in queue is %d"%CountNodes(queued))

    alljobs = GetQueue("standard",running)



    t=[]
    s=[]
    w=[]

    for j in alljobs:
        wt=GetWaitTime(j)
        t.append(wt)
        s.append(int(j["Resource_List.nodect"]))
        w.append(ParseWalltime(j))

    t=np.asarray(t)
    s=np.asarray(s)
    w=np.asarray(w)

    tt=[]
    ss=[]
    ww=[]

    for h in range(1,25):
        for i in range(9):
            walltime = float(h)
            size = 2.**(i)
            est = GetEstimatedTime(walltime=walltime,size=size,jobs=alljobs)
            ww.append(walltime)
            ss.append(size)
            tt.append(est)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(t,s,w)
    ax.scatter(tt,ss,ww)
    ax.set_xlabel("Time in Queue")
    ax.set_ylabel("Job Size")
    ax.set_zlabel("Walltime")
    ax.set_title("All jobs")
    plt.show()




    sys.exit()



    t=[]
    s=[]
    w=[]

    for j in running:
        wt=GetWaitTime(j)
        t.append(wt)
        s.append(int(j["Resource_List.nodect"]))
        w.append(ParseWalltime(j))

    t=np.asarray(t)
    s=np.asarray(s)
    w=np.asarray(w)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(t,s,w)
    ax.set_xlabel("Time in Queue")
    ax.set_ylabel("Job Size")
    ax.set_zlabel("Walltime")
    ax.set_title("Running jobs")
    plt.show()





    t=[]
    s=[]
    w=[]

    for j in queued:
        wt=GetWaitTime(j)
        t.append(wt)
        s.append(int(j["Resource_List.nodect"]))
        w.append(ParseWalltime(j))

    t=np.asarray(t)
    s=np.asarray(s)
    w=np.asarray(w)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(t,s,w)
    ax.set_xlabel("Time in Queue")
    ax.set_ylabel("Job Size")
    ax.set_zlabel("Walltime")
    ax.set_title("Queued jobs")
    plt.show()
