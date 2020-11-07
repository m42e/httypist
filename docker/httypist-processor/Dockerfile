FROM texlive/texlive:latest

RUN apt-get update && apt-get install -y \
      git \
      curl \
      python3.8 \
      python3-pip \
 && rm -rf /var/lib/apt/lists/*


VOLUME ["/app"]
WORKDIR /app

COPY httypist /app/

RUN   pip install -r httypist/requirements.txt \
      && pip install httypist

CMD [ "python3", "-m", "httypist", "--worker"]

