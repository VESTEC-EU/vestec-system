from passlib.hash import sha256_crypt as sha256
from Database.users import User
from uuid import uuid4
import pony.orm as pny
from flask import jsonify
import flask_jwt_extended as jwt
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
        user = User(user_id=user_id, username=username, name=name, email=email, password_hash=password_hash, access_rights=1)

        pny.commit()

        print("User '%s' created" % username)
        return "True"
    else: 
        print("User already exists")
        return "False"


@pny.db_session
def verify_user(username, password):    
    user = User.get(username=username)
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


#Custom function decorator for functions that require a login
#Checks the JWT is a valid JWT, then checks if it is in the database as known JWT
def login_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        print("login required")
        jwt.verify_jwt_in_request()
        jti = jwt.get_raw_jwt()["jti"]
        print("jti=%s"%jwt.get_raw_jwt()["jti"])
        with pny.db_session:
            #first check for expired tokens and delete them
            now=datetime.datetime.now()
            dt = datetime.timedelta(hours=1) #timeout period of token
            ddt = datetime.timedelta(days=7) #maximum allowed age of token

        return fn(*args,**kwargs)
    return wrapper

#checks if the user is an admin. Is used as a function decorator
def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args,**kwargs):
        print("admin_required")
        #check that the jwt is valid
        jwt.verify_jwt_in_request()
        user=jwt.get_jwt_identity()
        if IsAdmin(user):
            return fn(*args,**kwargs)
        else:
            return jsonify(msg='User is not an admin'), 403
    return wrapper




@pny.db_session
def IsAdmin(username):
    user = Database.User.get(username=username)

    authlevel=user.accessRights

    if authlevel==0:
        return True
    else:
        return False

    


@pny.db_session
def ShowUsers():
    print("---------------\nListing users:")
    users=pny.select(a for a in Database.User)[:]

    for user in users:
        print(user.name)
    print("End of users\n---------------")


if __name__ == "__main__":
    Database.initialiseDatabase()

    ShowUsers()

    status=AddUser("gordon","Gordon Gibb","g.gibb@epcc.ed.ac.uk","ImASecret")
    
    
    ShowUsers()

    VerifyUser("gordon","ImASecret")
    VerifyUser("gordon","secret")

