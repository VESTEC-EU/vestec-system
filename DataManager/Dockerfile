FROM python:3.7-slim
EXPOSE 5000
RUN apt-get update && apt-get install -y curl
COPY DataManager/requirements.txt /app/DataManager/requirements.txt
RUN pip install -r /app/DataManager/requirements.txt
COPY . /app
WORKDIR /app/DataManager
CMD python manager.py
