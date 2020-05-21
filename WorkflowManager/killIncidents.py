import sys
sys.path.append("../")
import workflow
import pony.orm as pny
import Database

#quick and dirty code to kill any active workflow incidents

if __name__ == "__main__":

    #get all active incidents

    with pny.db_session:

        incidents = Database.workflow.Incident.select(lambda i: i.status == "ACTIVE" or i.status == "PENDING")
        
        workflow.OpenConnection()
        print("Incidents that are active...")
        for incident in incidents:
            print(incident.uuid)
            workflow.Cancel(incident.uuid)
        workflow.FlushMessages()
        workflow.CloseConnection()

