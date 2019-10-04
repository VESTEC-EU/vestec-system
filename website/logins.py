from passlib.hash import sha256_crypt as sha256
from Database.users import User
from uuid import uuid4
import pony.orm as pny
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
import datetime


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

