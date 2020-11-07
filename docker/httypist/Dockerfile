FROM python:3.8

ARG GITEA_TOKEN

RUN apt-get update && apt-get install -y \
    git \
 && rm -rf /var/lib/apt/lists/*


VOLUME ["/app"]
WORKDIR /app

COPY httypist /app/

RUN pip install -r httypist/requirements
RUN  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
      && python3.8 get-pip.py \
      && pip install -r httypist/requirements \
      && pip install httypist

RUN mkdir /root/.ssh/ \
    && echo "host *" > /root/.ssh/config \
    && echo "IdentityFile /app/ssh_key_for_repo" >> /root/.ssh/config  \
    && echo "StrictHostKeyChecking no" >> /root/.ssh/config

CMD ["uvicorn", "--port", "8000", "httypist:app"]
