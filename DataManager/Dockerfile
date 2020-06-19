FROM python:3.7-slim
EXPOSE 5000
COPY . /app
WORKDIR /app/DataManager
RUN apt update
RUN apt install -y curl
RUN pip install -r /app/DataManager/requirements.txt
CMD python manager.py
