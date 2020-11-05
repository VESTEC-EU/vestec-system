FROM python:3.8-slim
EXPOSE 5502
COPY MachineStatusManager/requirements.txt /app/MachineStatusManager/requirements.txt
RUN pip install -r /app/MachineStatusManager/requirements.txt
COPY . /app
WORKDIR /app/MachineStatusManager
CMD python manager.py
