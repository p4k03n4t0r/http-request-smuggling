FROM python:3
RUN pip3 install -v gunicorn==20.0.4
RUN pip3 install Flask-AutoIndex
WORKDIR /app
COPY flag flag
COPY hello hello
CMD gunicorn --threads 8 --bind 0.0.0.0:8000 flask_autoindex.run:app