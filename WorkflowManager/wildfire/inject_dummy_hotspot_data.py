import sys
sys.path.append("../")

import requests
import json

#url = 'https://vestec.epcc.ed.ac.uk/EDI/WFAHotspot'
url = 'http://localhost:8000/EDI/WFAHotspot'

if len(sys.argv) < 3:
    print("Error, you must provide the incidentID and hotspot file as a command line argument")
    sys.exit(-1)

hotspot_file=open(sys.argv[2], "r")
read_bytes=hotspot_file.read()
hotspot_file.close()

msg = {"incidentID": sys.argv[1], "payload" : read_bytes}

x = requests.post(url+"-"+sys.argv[1], data = json.dumps(msg))
print(x.text)
