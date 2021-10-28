# Client Developer Overview

The client developer is working with the External Services part of the VESTEC system and such exposes a series of webservices that the client can then call into. This is implemented using a RESTful API and as pre the diagram below once a request is made then a thread from a pool will be activated to execute it and return any associated results to the source. 

![Web service](https://raw.githubusercontent.com/VESTEC-EU/vestec-system/main/Docs/web_service.png)

The APIs for this part of the system are divided into three categories; [incident management](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/incident_management_api.md), [user management](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/user_management_api.md), and [system administration](https://github.com/VESTEC-EU/vestec-system/blob/main/Docs/administration_api.md). 
