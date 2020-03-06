import utils
import logging
import workflow
import fire
import MesoNH
import julia
import quick

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.WARNING)

workflow.OpenConnection()

fire.RegisterHandlers()
julia.RegisterHandlers()
quick.RegisterHandlers()
MesoNH.RegisterHandlers()


workflow.execute()

#no need to close connection as this is done in the cleanup of execute()