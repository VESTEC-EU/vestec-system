import utils
import logging
import workflow

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.WARNING)


import fire
import MesoNH
import julia
import quick

workflow.execute()
