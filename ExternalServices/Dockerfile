FROM python:3.8-slim
ARG port=8000
ENV port $port
EXPOSE $port
RUN apt-get update && apt-get install -y graphviz libgraphviz-dev gcc
COPY ExternalServices/requirements.txt /app/ExternalServices/requirements.txt
RUN pip install -r /app/ExternalServices/requirements.txt
COPY . /app
WORKDIR /app/ExternalServices
CMD gunicorn -b 0.0.0.0:$port interface:app
