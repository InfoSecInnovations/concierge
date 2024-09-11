FROM python:3.12-slim

COPY requirements.txt /
ENV PIP_NO_CACHE_DIR=1
RUN pip install -r requirements.txt

COPY . /
CMD [ "python", "docker_run.py" ]

EXPOSE 15130