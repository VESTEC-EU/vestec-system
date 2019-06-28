from Database import db
import pony.orm as pny
from enum import Enum
import datetime
from Database.queues import Queue


class JobStatus(Enum):
    QUEUED=1
    RUNNING=2
    COMPLETED=3
    ERROR=4


class Job(db.Entity):
    uuid = pny.Required(str)
    queue = pny.Required(Queue)
    queueID = pny.Required(str)
    
    nNodes = pny.Required(int)
    walltime = pny.Required(datetime.timedelta)
    
    submitTime = pny.Required(datetime.datetime)
    runTime = pny.Optional(datetime.datetime)
    endTime = pny.Optional(datetime.datetime)
    
    status = pny.Required(JobStatus)

    activities = pny.Set("VestecJobs")

# class SubmittedActivityStatus(Enum):
#     PENDING=1
#     ACTIVE=2
#     COMPLETED=3
#     ERROR=4

# class Activity(db.Entity):
#     name = pny.Required(str)
#     uuid = pny.Required(str)
#     submittedjobs = pny.Set('SubmittedJob')
#     date = pny.Required(datetime.datetime)
#     status = pny.Required(SubmittedActivityStatus,default=SubmittedActivityStatus.PENDING)


#     def getName(self):
#         return self.name

#     def getUUID(self):
#         return self.uuid

#     def getDate(self):
#          return self.date

#     def getStatus(self):
#         return self.status

#     def setStatus(self,status):
#         self.status = status

#     def addSubmittedJob(self ,uuid, machine, executable, queue_id,wkdir):
#         newJob = SubmittedJob(uuid=uuid, executable=executable, machine=machine, queue_id=queue_id, wkdir=wkdir)
#         self.submittedjobs.add(newJob)
#         return newJob

#     def getNumberSubmittedJobs(self):
#         return len(self.submittedjobs)

#     def getSubmittedJobs(self):
#         return self.submittedjobs

#     def hasCompleted(self):
#         for j in self.submittedjobs:
#             if j.hasCompleted(): return True
#         return False


# class SubmittedJob(db.Entity):
#     activity=pny.Optional(Activity)
#     uuid = pny.Required(str)
#     executable = pny.Required(str)
#     status = pny.Required(SubmittedJobStatus, default=SubmittedJobStatus.QUEUED)
#     machine = pny.Required('Machine')
#     queue_id = pny.Required(str)
#     wkdir = pny.Required(str)

#     def getUUID(self):
#         return self.uuid

#     def updateStatus(self, status):
#         self.status=status

#     def getExecutable(self):
#         return self.executable

#     def getStatus(self):
#         return self.status

#     def hasCompleted(self):
#         return self.status == SubmittedJobStatus.COMPLETED or self.status == SubmittedJobStatus.ERROR

#     def getMachine(self):
#         return self.machine

#     def getQueueId(self):
#         return self.queue_id
