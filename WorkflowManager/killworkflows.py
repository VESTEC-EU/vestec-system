import sys
sys.path.append("../")
import pony.orm as pny
import manager.workflow as workflow

import Database


Database.initialiseDatabase()

with pny.db_session:
    incidents=Database.Incident.select(lambda i: i.status == "ACTIVE" or i.status == "PENDING")[:]
   

    ids=[]
    for incident in incidents:
        ids.append(incident.uuid)
    print(ids)

if len(ids) > 0:
    workflow.OpenConnection()
    for id in ids:
        workflow.Cancel(id,reason="Manualy killed")
    workflow.CloseConnection()
else:
    print("No active incidents to kill")