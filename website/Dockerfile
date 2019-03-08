FROM python:3-slim
WORKDIR /home
COPY . /home

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python","run.py"]
