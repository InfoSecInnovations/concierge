FROM python:3.12-slim AS cpu

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
/bin/sh -c set -eux; apt-get update; apt-get install -y --no-install-recommends poppler-utils pandoc tesseract-ocr libreoffice libgl1 libglib2.0-0

COPY requirements.txt /
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
COPY . /shabti/
WORKDIR /shabti/
CMD [ "python", "docker_run.py" ]

EXPOSE 15130

FROM cpu AS cuda
RUN --mount=type=cache,target=/root/.cache/pip pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu126