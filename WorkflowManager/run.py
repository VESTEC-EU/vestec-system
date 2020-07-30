import sys
sys.path.append("../")
#import manager.utils
import logging
from manager import workflow

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.DEBUG)



#from workflows.julia import julia
#from workflows.quicksort import quicksort
from workflows.simple import simple
#import workflowshotspot
from workflows.performance_data import performance_data
from workflows.wildfire import wildfire

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.WARNING)

workflow.OpenConnection()

#fire.RegisterHandlers()
#MesoNH.RegisterHandlers()
#julia.RegisterHandlers()
#quick.RegisterHandlers()
simple.RegisterHandlers()
#hotspot.RegisterHandlers()
performance_data.RegisterHandlers()
wildfire.RegisterHandlers()


workflow.execute()

#no need to close connection as this is done in the cleanup of execute()
