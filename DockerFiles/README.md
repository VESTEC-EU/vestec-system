# Docker setup

## Build

Build and tag (since swarm works on tags) the images

```
docker image build -f Dockerfile_SimulationManager -t vestec-server/manager:latest ..
docker image build -f Dockerfile_website -t vestec-server/website:latest ..
```

## Run

Create a swarm

```
docker swarm init
```

Add secrets:
```
echo "top secret!" | docker secret create rabbit_erlang_cookie -
echo "top secret!" | docker secret create rabbit_admin_password -
```

Run the stack:

```
docker stack deploy -c docker-compose.yml vestec
```
