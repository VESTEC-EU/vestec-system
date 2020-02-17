import utils
import logging
import workflow

# set the logging level of the workflow logger
workflow.SetLoggingLevel(logging.DEBUG)


import fire
import MesoNH
import julia
import quick

workflow.execute()
