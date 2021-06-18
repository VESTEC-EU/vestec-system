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
from workflows.helloworld_remote import helloworld
from workflows.data_transfer import data_transfer

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.WARNING)

workflow.OpenConnection()


#julia.RegisterHandlers()
#quicksort.RegisterHandlers()
simple.RegisterHandlers()
performance_data.RegisterHandlers()
wildfire.RegisterHandlers()
tests.RegisterHandlers()
helloworld.RegisterHandlers()
data_transfer.RegisterHandlers()

workflow.execute()

#no need to close connection as this is done in the cleanup of execute()
