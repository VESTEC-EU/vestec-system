from __future__ import print_function
import requests
import time
import uuid
import os
import json

host="http://0.0.0.0:5500/"

print("\nSubmitting a job")
name = str(uuid.uuid4())
print("name= %s"%name)
url = os.path.join(host,"jobs",name)
r=requests.put(url,json={"name":name,"machine":"ARCHER"})
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

# name = str(uuid.uuid4())
# url = os.path.join(host,"jobs",name)
# requests.put(url,data={"data": "yes", "json":"no"})
