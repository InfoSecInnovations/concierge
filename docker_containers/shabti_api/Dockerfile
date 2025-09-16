FROM python:3.12-slim AS cpu

COPY requirements.txt /
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY . /
ENV PYTHONUNBUFFERED=1
CMD [ "python", "docker_run.py" ]

EXPOSE 15130

FROM cpu AS cuda
RUN --mount=type=cache,target=/root/.cache/pip pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu126