FROM python:3-slim
EXPOSE 5501
COPY ExternalDataInterface/requirements.txt /app/ExternalDataInterface/requirements.txt
RUN pip install -r /app/ExternalDataInterface/requirements.txt
COPY . /app
WORKDIR /app/ExternalDataInterface
ENTRYPOINT ["python"]
CMD ["interface.py"]
