FROM python:3.7-slim
COPY . /app
WORKDIR /app/MachineInterface
RUN pip install -r /app/MachineInterface/requirements.txt
CMD python interface.py
