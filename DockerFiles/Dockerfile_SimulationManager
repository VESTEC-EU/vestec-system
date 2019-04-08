FROM python:3-slim
EXPOSE 5500
COPY . /app
WORKDIR /app/SimulationManager
RUN pip install -r /app/SimulationManager/requirements.txt
ENTRYPOINT ["python"]
CMD ["manager.py"]
