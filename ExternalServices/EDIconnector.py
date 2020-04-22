import os
from flask import jsonify, request, Response
import requests

if "VESTEC_EDI_URI" in os.environ:
    EDI_URL = os.environ["VESTEC_EDI_URI"]    
else:    
    EDI_URL= 'http://127.0.0.1:5501/EDImanager'

def pushDataToEDI():
    pushDataToEDI("")

def pushDataToEDI(source):
    resp = requests.request(
        method=request.method,
        url=EDI_URL+"/"+source,
        headers={key: value for (key, value) in request.headers if key != 'Host'},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False)

    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    response = Response(resp.content, resp.status_code, headers)
    return response