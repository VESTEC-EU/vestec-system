FROM python:3.8-slim
EXPOSE 5505
COPY SimulationManager/requirements.txt /app/SimulationManager/requirements.txt
RUN pip install -r /app/SimulationManager/requirements.txt
COPY . /app
WORKDIR /app/SimulationManager
CMD python manager.py
