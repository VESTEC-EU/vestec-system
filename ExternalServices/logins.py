from passlib.hash import sha256_crypt as sha256
from Database.users import User
from uuid import uuid4
import pony.orm as pny
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
import datetime

@pny.db_session
def get_user_access_level(username):
  user = User.get(username=username)
  if user is None:
    return 0
  else:
    return user.access_rights

@pny.db_session
def get_all_users():
    user_descriptions=[]
    users=pny.select(user for user in User)
    for user in users:
        if not user == None:
            user_info={}
            user_info["username"]=user.username
            user_info["name"]=user.name
            user_info["email"]=user.email
            user_info["access_rights"]=user.access_rights
            user_info["enabled"]=user.enabled
            user_info["workflows"]=[]
            for wf in user.allowed_workflows:
                user_info["workflows"].append(wf.kind)
            user_descriptions.append(user_info)
    return user_descriptions

@pny.db_session
def get_user_details(user):
    user_descriptions=[]
    users=[User.get(username=user)]
    for user in users:
        if not user == None:
            user_info={}
            user_info["username"]=user.username
            user_info["name"]=user.name
            user_info["email"]=user.email
            user_info["access_rights"]=user.access_rights
            user_info["enabled"]=user.enabled
            user_info["workflows"]=[]
            for wf in user.allowed_workflows:
                user_info["workflows"].append(wf.kind)
            user_descriptions.append(user_info)
    return user_descriptions

@pny.db_session
def get_allowed_workflows(user):
    workflows=[]
    users=[User.get(username=user)]
    for user in users:
        if not user == None:
            for wf in user.allowed_workflows:
                workflows.append(wf.kind)
    return workflows

@pny.db_session
def add_user(username, name, email, password):
    #check if the user already exists
    test_user = User.get(username=username)

    if test_user is None:
        user_id = str(uuid4())
        #hash the password to be stored
        password_hash = sha256.hash(password)

        #create user
        user = User(user_id=user_id, username=username, name=name, email=email, password_hash=password_hash, access_rights=0)

        pny.commit()

        print("User '%s' created" % username)
        return 1
    else:
        print("User already exists")
        return 0

@pny.db_session
def verify_user(username, password):
    user = User.get(username=username)
    if user is None: return False
    if not user.enabled: return False
    verified = False

    if user is None:
        print("User does not exist!")
        return False
    else:
        password_hash = user.password_hash
        verified = sha256.verify(password, password_hash)

    if verified:
        print("User '%s' is authenticated :)" % username)
        return True
    else:
        print("User '%s' is not authenticated :(" % username)
        return False


#checks if the user is an admin. Is used as a function decorator
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        print("admin_required")
        #check that the jwt is valid
        identity = get_jwt_identity()
        user = User.get(username=identity)
        is_admin = True if user.access_rights == 1 else False

        if is_admin:
            return fn(*args,**kwargs)
        else:
            return jsonify(msg='User is not an admin'), 403

    return wrapper

