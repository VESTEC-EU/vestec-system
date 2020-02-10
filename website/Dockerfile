FROM python:3-slim
ARG port=8000
ENV port $port
EXPOSE $port
COPY . /app
WORKDIR /app/website
RUN pip install -r /app/website/requirements.txt
CMD gunicorn -b 0.0.0.0:$port app:app
