FROM texlive/texlive:latest

RUN apt-get update && apt-get install -y \
      git \
      curl \
      python3.8 \
 && rm -rf /var/lib/apt/lists/*


VOLUME ["/app"]
WORKDIR /app

COPY httypist /app/

RUN  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
      && python3.8 get-pip.py \
      && pip install -r httypist/requirements
      && pip install httypist

CMD [ "python3", "-m", "httypist", "--worker"]

