FROM python:3.7-slim
EXPOSE 5502
COPY . /app
WORKDIR /app/MachineStatusManager
RUN pip install -r /app/MachineStatusManager/requirements.txt
CMD python manager.py
