FROM python:3.12-slim AS cpu

COPY requirements.txt /
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY . /
ENV PYTHONUNBUFFERED=1
CMD [ "python", "docker_run.py" ]

EXPOSE 15130

FROM cpu AS cuda
RUN --mount=type=cache,target=/root/.cache/pip pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126