# User administration functionality from the command line
import sys
sys.path.append("../")
import Database
from Database.users import User
from Database.workflow import Incident
import pony.orm as pny
import csv

def display_help():
  print("-dump [filename]: Dumps out user configuration into the CSV file")
  print("-load [filename]: Loads in user configuration from the CSV file")

@pny.db_session
def dump_user_info(filename):
  with open(filename, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["User_id", "Username", "Name", "Password_hash", "Email", "Access_rights", "Enabled"])
    users=pny.select(user for user in User)
    for user in users:
      if not user == None:
        writer.writerow([user.user_id, user.username, user.name, user.password_hash, user.email, user.access_rights, user.enabled])

@pny.db_session
def load_user_info(filename):
  with open(filename, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
      user_info=dict(row)
      user = User(user_id=user_info["User_id"], username=user_info["Username"], name=user_info["Name"], email=user_info["Email"], password_hash=user_info["Password_hash"], access_rights=user_info["Access_rights"], enabled=user_info["Enabled"])        

num_args=len(sys.argv)
if num_args != 3:
  display_help()
else:
  if (sys.argv[1] == "-dump"):
    # Initialise database
    Database.initialiseDatabase()
    dump_user_info(sys.argv[2])
  elif (sys.argv[1] == "-load"):
    # Initialise database
    Database.initialiseDatabase()
    load_user_info(sys.argv[2])
  else:
    display_help()  
