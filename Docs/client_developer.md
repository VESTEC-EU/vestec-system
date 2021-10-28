# Client Developer Overview

The client developer is working with the External Services part of the VESTEC system and such exposes a series of webservices that the client can then call into. This is implemented using a RESTful API and as pre the diagram below once a request is made then a thread from a pool will be activated to execute it and return any associated results to the source. 

![Web service](https://raw.githubusercontent.com/VESTEC-EU/vestec-system/main/Docs/images/web_service.png)

The APIs for this part of the system are divided into three categories; [incident management](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/incident_management_api.md), [user management](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/user_management_api.md), and [system administration](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/administration_api.md). For the majority of these calls the caller must provide a JWT access token that authorises them which has been provided by the system when they authorise (via the appropriate API call in the user management APIs). Some calls for system administrator require admin privileges by the user.

The VESTEC web management interface uses the same External Services APIs for interaction with the system which can be integrated into client applications. Therefore these can be viewed as visual frontends which sit atop the APIs and interact with the VESTEC system using REST.
