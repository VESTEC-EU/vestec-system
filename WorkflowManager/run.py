import sys
sys.path.append("../")
import logging
from manager import workflow

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.DEBUG)

#from workflows.julia import julia
#from workflows.quicksort import quicksort
from workflows.simple import simple
from workflows.performance_data import performance_data
from workflows.wildfire import main as wildfire
from workflows.tests import tests
from workflows.spaceweather import spaceweather
from workflows.mosquito import mosquito

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.WARNING)

workflow.OpenConnection()


#julia.RegisterHandlers()
#quicksort.RegisterHandlers()
simple.RegisterHandlers()
performance_data.RegisterHandlers()
wildfire.RegisterHandlers()
tests.RegisterHandlers()
spaceweather.RegisterHandles()
mosquito.RegisterHandles()

workflow.execute()

#no need to close connection as this is done in the cleanup of execute()
