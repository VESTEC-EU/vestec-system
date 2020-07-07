FROM python:3.7-slim
EXPOSE 5505
COPY . /app
WORKDIR /app/SimulationManager
RUN pip install -r /app/SimulationManager/requirements.txt
CMD python manager.py
