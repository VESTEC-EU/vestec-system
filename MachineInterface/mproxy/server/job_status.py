class JobStatus:
    def __init__(self, queue_id, status, walltime):
        self.queue_id=queue_id
        self.status=status
        self.walltime=walltime

    def getQueueId(self):
        return self.queue_id

    def getStatus(self):
        return self.status

    def getWalltime(self):
        return self.walltime
        