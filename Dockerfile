# syntax=docker/dockerfile:1
FROM debian:bookworm

WORKDIR /app

COPY . .

# install app dependencies
RUN apt-get update && apt-get install -y python3-venv python3-dev

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt

RUN apt-get install -y nodejs
RUN apt-get install -y npm
RUN apt-get install -y nginx

CMD ["/app/run.sh"]