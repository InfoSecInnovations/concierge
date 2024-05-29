FROM python:3

COPY requirements.txt /
ENV PIP_NO_CACHE_DIR=1
RUN pip install -r requirements.txt

COPY . /
CMD [ "python", "-m", "shiny", "run", "--host", "0.0.0.0", "--launch-browser", "concierge_shiny/app.py" ]

EXPOSE 8000