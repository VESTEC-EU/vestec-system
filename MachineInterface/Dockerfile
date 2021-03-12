FROM python:3.8-slim
RUN apt-get update && apt-get install -y openssh-client vim
COPY MachineInterface/requirements.txt /app/MachineInterface/requirements.txt
RUN pip install -r /app/MachineInterface/requirements.txt
COPY . /app
WORKDIR /app/MachineInterface
#RUN cat /app/MachineInterface/misc/ssh_archer_config >> /etc/ssh/ssh_config
#RUN cat /app/MachineInterface/misc/ssh_hpda_config >> /etc/ssh/ssh_config
RUN cat /app/MachineInterface/misc/ssh_hpda_config >> $HOME/.ssh/ssh_config
CMD python interface.py
