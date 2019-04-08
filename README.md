# vestec-wp5
VESTEC Project WP5

## Docker Instructions
To run all the services, change into the `DockerFiles` directory and run
```
$ docker-compose build
$ docker-compose up
```

To bring the services down, use
```
$ docker-compose down
```
(`CTRL-C` does not always work so this step is needed to ensure everything is cleaned up)

To build a single service (e.g. for testing) run
```
$ docker build -f [dockerfile] --tag=[image_name] ../
$ docker run [image_name]
```
