#!/bin/bash
export SSH_AUTH_SOCK=/tmp/XXX
export PATH=$PATH:/Library/Frameworks/Python.framework/Versions/3.7/bin/
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/Library/Frameworks/Python.framework/Versions/3.7/lib/
export PYTHONPATH=$PYTHONPATH:/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages:/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7:/Library/Frameworks/Python.framework/Versions/3.7/bin/python3 

/Library/Frameworks/Python.framework/Versions/3.7/bin/python3 /Users/bprodan/Documents/vestec/DecisionMaker/estimate_active_jobs.py