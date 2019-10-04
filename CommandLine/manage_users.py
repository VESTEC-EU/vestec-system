# User administration functionality from the command line
import sys
sys.path.append("../")
import Database
from Database.users import User
import pony.orm as pny

ACCESS_LEVEL_NORMAL=0
ACCESS_LEVEL_ADMIN=1

def display_help():
  print("-h: Displays this help")
  print("-display: Displays all users")
  print("-e: Enable user")
  print("-d: Disable user")
  print("-normal: Set user normal")
  print("-admin: Set user as admininstrator")


def generate_access_right(code):
  if code==0:
    return "normal user"
  elif code == 1:
    return "administrator"
  else:
    return "unknown type"

def generate_enabled(enabled):
  if enabled:
    return "enabled"
  else:
    return "disabled"

@pny.db_session
def set_user_access_level(username, level):
  user=User.get(username=username)
  if user == None:
    print("Error:", username, "not found")
  else:
    user.access_rights=level
    print("Set user access level for",username,"as",level)

@pny.db_session
def set_user_enable_flag(username, flag):
  user=User.get(username=username)
  if user == None:
    print("Error:", username, "not found")
  else:
    user.enabled=flag
    if flag:
      print ("User",username, "enabled")
    else:
      print ("User",username, "disabled")

@pny.db_session
def display_user_info(user=None):
  if user == None:
    users=pny.select(user for user in User)
  else:
    users=[User.get(username=user)]
    if users[0]==None:
      print("Error:", username, "not found")
  for user in users:
    if not user == None:
      print(user.username, ",", generate_access_right(user.access_rights), ",", generate_enabled(user.enabled))

# Initialise database
Database.initialiseDatabase()

num_args=len(sys.argv)

if (num_args < 2):
  display_help()
else:
  command=sys.argv[1]
  if command.lower() == "-display":
    if (num_args > 2):
      display_user_info(sys.argv[2])
    else:
      display_user_info()
  elif command.lower() == "-h":
    display_help()
  elif command.lower() == "-e":
    if (num_args > 2):
      set_user_enable_flag(sys.argv[2], True)
    else:
      print("Error: You need to provide a username with enable")
  elif command.lower() == "-d":
    if (num_args > 2):
      set_user_enable_flag(sys.argv[2], False)
    else:
      print("Error: You need to provide a username with disable")
  elif command.lower() == "-normal" or command.lower() == "-admin":
    if (num_args > 2):
      set_user_access_level(sys.argv[2], ACCESS_LEVEL_NORMAL if command.lower() == "-normal" else ACCESS_LEVEL_ADMIN)
    else:
      print("Error: You need to provide a username when setting user access level")


