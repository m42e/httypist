FROM python:3.8

RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
 && rm -rf /var/lib/apt/lists/*

VOLUME ["/app"]
WORKDIR /app

COPY . /app/

RUN ls

RUN  pip install -r requirements.txt \
      && pip install .

RUN mkdir /root/.ssh/ \
    && echo "host *" > /root/.ssh/config \
    && echo "IdentityFile /app/ssh_key_for_repo" >> /root/.ssh/config  \
    && echo "StrictHostKeyChecking no" >> /root/.ssh/config

CMD ["uvicorn", "--port", "8000", "httypist:app"]
