# User management

The user management API allows callers to manage their own session within the VESTEC system, for instance to login, logout, signup and check their level of access.

Note that any API calls indicated as requiring a logged in user will return the 403 status code if either an access token is not provided, or the session that the access token references to is deemed expired.

The user's credentials are passed via the HTTP header, with the key _Authorization_ and value _Bearer <usertoken>_ where <usertoken> is returned by the system when you logged in. For instance, 'Authorization':'Bearer 123' if the token 123 was returned.

## Login
This call enables a user to login with the VESTEC system and returns a session token which is then used for subsequent calls to uniquely identify this user within that session.

*Address:* /flask/login

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | Username for logging into the system
password | Password for logging into the system 

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
access_token | Session based access token used to authorise all API calls

#### Output data on failure
*Output data format:* JSON

Failure is defined as the login attempt failed due to an incorrect username or password, or some internal system error.

Key | Value
------ | -----------
status | 400
msg | Message explaining reason for failure 


## Logout
This call logs out a user, deleting the current session for that user so subsequent API calls with the token will be unauthorised

*Address:* /flask/logout

*HTTP method:* DELETE

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | User logged out

*Note:* This call always succeeds, irrespective of whether the user was logged in or not

## Authorised
Based upon the user token deduces whether this is an authorised user, e.g. is the current session associated with this deemed as active or has it expired. ***Requires a logged in user***

*Address:* /flask/authorised

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | User authorised.

#### Output data on failure

Key | Value
------ | -----------
status | 403

## Get user type
Retrieves the type of logged in user, currently this is simply whether the logged in user is of type _user_ (a normal user) or _administrator_ (a sysop.) ***Requires a logged in user***

*Address:* /flask/user_type

*HTTP method:* GET

#### Input data
HTTP header should contain access token

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
access_level | Access level (0 is user, 1 is administrator)

#### Output data on failure

Key | Value
------ | -----------
status | 403

## Sign up
Enables a potential user to signup to the VESTEC system and create a user account. Note that all user accounts are created disabled and it requires an administrator to explicitly enable these so that the user can login to the VESTEC system.

*Address:* /flask/signup

*HTTP method:* POST

#### Input data
*Input data format:* JSON

Key | Value
------ | -----------
username | Username for the new user
name | User's name
email | Email address of the user
password | Password for the user

#### Output data on success
*Output data format:* JSON

Key | Value
------ | -----------
status | 200
msg | User successfully created. Log in.

#### Output data on failure

Key | Value
------ | -----------
status | Status code
msg | Associated error message

If the user already exists then status code 409 will be returned, if the JSON data was incorrectly formatted then status 400 is returned.
