FROM python:3-slim
ARG port=8000
ENV port $port
EXPOSE $port
COPY . /app
WORKDIR /app/ExternalServices
RUN apt update
RUN apt install -y graphviz libgraphviz-dev gcc
RUN pip install -r /app/ExternalServices/requirements.txt
CMD gunicorn -b 0.0.0.0:$port app:interface
