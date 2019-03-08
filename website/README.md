# Vestec website

This will be the client-facing website/interface for the vestec WP5 system

## To create and run the docker image

First create the image:
``` $ docker build --tag=vestec``` 

Then we want to run the image to create a container:
``` $ docker run -p 5000:5000 vestec ```

To view the website, open http://localhost:5000/ in a browser. CTRL-C to close the container.
