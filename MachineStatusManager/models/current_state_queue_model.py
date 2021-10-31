from Database.machine import Machine
import pony.orm as pny

class QueuePredictionCurrentState():
    def __init__(self, machine_name):
        self.machine_name=machine_name

    @pny.db_session
    def predict(self, walltime, number_nodes, detailed_status):
        machine_details=Machine.get(machine_name=self.machine_name)
        queued_nodes=self._getNumberNodesInState(detailed_status, "QUEUED")
        running_nodes=self._getNumberNodesInState(detailed_status, "RUNNING")
        machine_nodes=machine_details.num_nodes
        free_nodes=machine_nodes - running_nodes
        ratio=float(queued_nodes)/float(running_nodes)
        return ratio* 20 / (free_nodes / int(number_nodes))
        

    def _getNumberNodesInState(self, detailed_status, state):
        node_num=0
        for entry in detailed_status.split("\n"):            
            facets=entry.split()
            if len(facets)==4 and facets[1]==state:
                node_num+=int(facets[3])
        return node_num