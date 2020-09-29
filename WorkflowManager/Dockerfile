FROM python:3-slim
RUN apt update
RUN apt install -y graphviz libgraphviz-dev gcc
COPY ./WorkflowManager/requirements.txt /app/WorkflowManager/requirements.txt
RUN pip install -r /app/WorkflowManager/requirements.txt
COPY . /app
WORKDIR /app/WorkflowManager
CMD python run.py
