import sys
sys.path.append("../")

import workflow


from . import mesoNH
from . import hotspots
from . import wildfire




@workflow.handler
def wildfire_init(msg):
    IncidentID = msg["IncidentID"]

    print("\nSetting up wildfire incident %s"%IncidentID)
    workflow.setIncidentActive(IncidentID)

    workflow.send(queue="wildfire_mesonh_init",message=msg)
    workflow.send(queue="wildfire_hotspot_init",message=msg)
    #workflow.send(queue="wildfire_fire_static",message=msg)

    


def RegisterHandlers():
    workflow.RegisterHandler(handler = wildfire_init,queue="wildfire_init")
    hotspots.RegisterHandlers()
    mesoNH.RegisterHandlers()
    wildfire.RegisterHandlers()




