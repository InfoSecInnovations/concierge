FROM python:3.12-slim

COPY requirements.txt /
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY . /
CMD [ "python", "docker_run.py" ]

EXPOSE 15130