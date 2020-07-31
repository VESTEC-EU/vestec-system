import sys
sys.path.append("../")
sys.path.append("../../")
from manager import workflow

if __name__ == "__main__":
    upperLeft = "1.8347167968750002/53.38332836757156"
    lowerRight = "11.744384765625/48.75618876280552"
    workflow.OpenConnection()
    id = workflow.CreateIncident(name="wildfire",kind="WILDFIRE",upper_left_latlong=upperLeft,lower_right_latlong=lowerRight,duration=1)

    msg = {"IncidentID": id}

    workflow.send(queue="wildfire_init",message=msg,src_tag="Start")
    workflow.FlushMessages()
    workflow.CloseConnection()

