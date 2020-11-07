FROM texlive/texlive:latest

RUN apt-get update && apt-get install -y \
      git \
      curl \
      pandoc \
      python3.8 \
      python3-pip \
      python3-pygments \
     && apt-get --purge remove -y .\*-doc$ \
     && apt-get clean -y \
     && apt-get autoremove \
     && rm -rf /var/lib/apt/lists/*


VOLUME ["/app"]
WORKDIR /app

COPY httypist /app/

RUN tlmgr update --self; \
    tlmgr install \
		latexmk \
		lipsum \
		background \
		everypage \
		siunitx \
		titlesec; \
    tlmgr update --all

RUN   pip install -r requirements.txt \
      && pip install .

CMD [ "python3", "-m", "httypist", "--worker"]

