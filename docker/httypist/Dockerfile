FROM python:3.8

ARG GITEA_TOKEN

RUN apt-get update && apt-get install -y \
    git \
 && rm -rf /var/lib/apt/lists/*

RUN GIT_TRACE=2 pip install git+https://$GITEA_TOKEN@gitea.d1v3.de/matthias/httypist
RUN pip install gunicorn

VOLUME ["/app"]
WORKDIR /app

RUN mkdir /root/.ssh/ && echo "host *" > /root/.ssh/config && echo "IdentityFile /app/ssh_key_for_repo" >> /root/.ssh/config && echo "StrictHostKeyChecking no" >> /root/.ssh/config

CMD ["gunicorn", "-b", "0.0.0.0:8000", "httypist.server:app"]
