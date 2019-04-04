from __future__ import print_function
import requests
import time
import uuid
import os
import json
from namesgenerator import get_random_name

host="http://0.0.0.0:5500/"

print("\nSubmitting a job")
uuid = str(uuid.uuid4())
name=get_random_name()
print("name= %s"%name)
url = os.path.join(host,"jobs",uuid)
r=requests.put(url,json={"name":name,"uuid" :uuid})
print(r.text)

time.sleep(1)

print("\nGetting job status")
r=requests.get(url)
js=r.json()
for key, value in js.items():
    print(key, value)

time.sleep(1)

print("\nDetails on all Jobs")
url = os.path.join(host,"jobs")
r=requests.get(url)
js=r.json()

print(json.dumps(js,indent=4))
