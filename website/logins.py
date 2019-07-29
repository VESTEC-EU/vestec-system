from passlib.hash import sha256_crypt as sha256
import Database
import pony.orm as pny
from flask import jsonify
import flask_jwt_extended as jwt
from functools import wraps
import datetime


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
def AddUser(username,name,email,password):
    
    #check if the user already exists
    test = Database.User.get(username=username)
    if test != None:
        print("User already exists")
        return False
    
    #hash the password to be stored
    passwordHash = sha256.hash(password)

    #create user
    user = Database.User(username=username,name=name,email=email,passwordHash=passwordHash,accessRights=1)

    print("User '%s' created"%username)
    return True


@pny.db_session
def VerifyUser(username,password):
    
    #get the user
    user = Database.User.get(username=username)
    if user==None:
        print("User does not exist!")
        return False
    
    pHash = user.passwordHash
    
    verified = sha256.verify(password,pHash)
    
    if verified:
        print("User '%s' is authenticated :)"%username)
        return True
    else:
        print("User '%s' is not authenticated :("%username)
        return False

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

