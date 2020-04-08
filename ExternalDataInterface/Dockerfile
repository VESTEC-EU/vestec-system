FROM python:3-slim
EXPOSE 5501
COPY . /app
WORKDIR /app/ExternalDataInterface
RUN pip install -r /app/ExternalDataInterface/requirements.txt
ENTRYPOINT ["python"]
CMD ["interface.py"]
