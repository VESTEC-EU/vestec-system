FROM python:3.7-slim
COPY . /app
WORKDIR /app/MachineInterface
RUN apt-get update;apt-get install -y openssh-client vim
# add credentials on build
ARG SSH_PRIVATE_KEY
RUN mkdir /root/.ssh/
RUN cp "${SSH_PRIVATE_KEY}" /root/.ssh/id_rsa
RUN ssh-keyscan -p 25005 -H 130.237.222.173 > /root/.ssh/known_hosts
RUN /bin/bash -c 'chmod 600 /root/.ssh/*'
RUN pip install -r /app/MachineInterface/requirements.txt
CMD python interface.py --config machines.yaml
