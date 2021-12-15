import time
import datetime
from dateutil.parser import parse

class JobStatus:
    def __init__(self, queue_id, status, walltime, number_nodes, submit_time, start_time, end_time):
        self.queue_id=queue_id
        self.status=status
        self.walltime=walltime
        self.number_nodes=number_nodes
        self.submit_time="-" if submit_time == "Unknown" else submit_time
        self.start_time="-" if start_time == "Unknown" else start_time
        self.end_time="-" if end_time == "Unknown" else end_time

    def getQueueId(self):
        return self.queue_id

    def getStatus(self):
        return self.status

    def getWalltime(self):
        return self.walltime

    def getNumberNodes(self):
        return self.number_nodes

    def getQueueTime(self):
        if self.submit_time=="-" or self.start_time == "-":
            return "-"
        submit=time.mktime(parse(self.submit_time).timetuple())
        start=time.mktime(parse(self.start_time).timetuple())
        return str(start-submit)

    def getRunTime(self):
        if self.start_time == "-" or self.end_time == "-":
            return "-"
        start=time.mktime(parse(self.start_time).timetuple())
        end=time.mktime(parse(self.end_time).timetuple())
        return str(end-start)

    def toString(self):
        return self.queue_id+" "+self.status+" "+self.walltime+" "+self.number_nodes+" "+self.getQueueTime() +" " +self.getRunTime()

        