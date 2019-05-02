FROM python:3-slim
ARG port=5000
ENV port $port
EXPOSE $port
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD gunicorn -b 0.0.0.0:$port app:APP
