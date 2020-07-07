FROM python:3.7-slim
COPY . /app
WORKDIR /app/MachineInterface
RUN apt-get update;apt-get install -y openssh-client vim
RUN cat /app/MachineInterface/misc/ssh_archer_config >> /etc/ssh/ssh_config
RUN pip install -r /app/MachineInterface/requirements.txt
CMD python interface.py --config machines.yaml
