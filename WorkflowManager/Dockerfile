FROM python:3.8-slim
COPY . /app
WORKDIR /app/WorkflowManager
RUN apt update
RUN apt install -y graphviz libgraphviz-dev gcc
RUN pip install -r /app/WorkflowManager/requirements.txt
CMD python run.py
