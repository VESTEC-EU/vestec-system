class JobStatus:
    def __init__(self, queue_id, status, walltime, number_nodes):
        self.queue_id=queue_id
        self.status=status
        self.walltime=walltime
        self.number_nodes=number_nodes

    def getQueueId(self):
        return self.queue_id

    def getStatus(self):
        return self.status

    def getWalltime(self):
        return self.walltime

    def getNumberNodes(self):
        return self.number_nodes

    def toString(self):
        return self.queue_id+" "+self.status+" "+self.walltime+" "+self.number_nodes

        