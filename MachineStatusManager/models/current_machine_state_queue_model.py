from Database.machine import Machine
from mproxy.client import Client
import pony.orm as pny
import asyncio
import aio_pika
import datetime
from dateutil.parser import parse

hours_to_go_back=3
minutes_to_go_back=0
min_history_entries=100
min_number_node_entries=20

class QueuePredictionCurrentMachineState():
    def __init__(self, machine_name):
        self.machine_name=machine_name

    def retrieve_historical_status(self):
        now = datetime.datetime.now()
        detailed_historical_status=""
        hrs_back=hours_to_go_back
        while (len(detailed_historical_status.split('\n')) < min_history_entries):            
            start=now - datetime.timedelta(hours=hrs_back, minutes=minutes_to_go_back)
            detailed_historical_status=asyncio.run(self.retrieve_machine_status(self.machine_name, start.strftime('%H:%M'), now.strftime('%H:%M')))            
            hrs_back+=1
            if hrs_back - hours_to_go_back > 6: break
        return detailed_historical_status

    @pny.db_session
    def predict(self, walltime, number_nodes, detailed_status):        
        detailed_historical_status=self.retrieve_historical_status()        
        similar_runs=[]
        num_nodes_range=2
        pt=parse(walltime)
        requested_seconds= pt.second + pt.minute*60 + pt.hour*3600 
        while (len(similar_runs) < min_number_node_entries):
            similar_runs=self.extract_num_nodes_similar(detailed_historical_status, int(min_number_node_entries), num_nodes_range, requested_seconds)
            num_nodes_range+=10
            if num_nodes_range > 30: break
        if len(similar_runs) == 0: return 0.0      
        return self.average_queue_waittime(similar_runs)

    def average_queue_waittime(self, entries):
        average_time=0.0
        pp=0
        for entry in entries:            
            average_time+=float(entry[0]) * entry[1]
            pp+=entry[1]         
        return average_time / pp

    def extract_num_nodes_similar(self, detailed_status, num_nodes_requested, node_range, requested_seconds):
        return_info=[]
        for entry in detailed_status.split('\n'):
            tokens=entry.split()
            if len(tokens)==4:
                num_nodes=int(tokens[1])
                if num_nodes >= num_nodes_requested-node_range and num_nodes <= num_nodes_requested+node_range:                    
                    if requested_seconds < int(tokens[3]):
                        part=requested_seconds
                        whole=int(tokens[3])
                    else:
                        part=int(tokens[3])
                        whole=requested_seconds                    
                    return_info.append([tokens[2], 1 / ((whole-part))])
        return return_info


    async def retrieve_machine_status(self, machine_name, start_time, end_time):         
        client = await Client.create(machine_name)
        status = await client.getHistoricalStatus(start_time, end_time)
        return status