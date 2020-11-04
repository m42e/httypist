FROM python3.8

ARG GITEA_TOKEN

RUN apt-get update && apt-get install -y \
      git \
      curl \
 && rm -rf /var/lib/apt/lists/*

RUN  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3.8 get-pip.py && pip install git+https://$GITEA_TOKEN@gitea.d1v3.de/matthias/httypist

VOLUME ["/app"]
WORKDIR /app

CMD [ "celery", "-A", "httypist.processor", "worker"]

