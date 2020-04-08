import utils
import logging
import workflow

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.DEBUG)


import fire
import MesoNH
#import julia
#import quick
import simple

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.WARNING)

workflow.OpenConnection()

fire.RegisterHandlers()
#julia.RegisterHandlers()
#quick.RegisterHandlers()
simple.RegisterHandlers()

workflow.execute()

#no need to close connection as this is done in the cleanup of execute()