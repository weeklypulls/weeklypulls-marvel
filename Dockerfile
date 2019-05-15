FROM python:3.6-alpine3.9

ENV PYTHONUNBUFFERED=0

RUN apk add --no-cache gcc \
                       musl-dev \
                       postgresql-dev \
                       libmemcached-dev \
                       cyrus-sasl-dev \
                       zlib-dev

# For using early releases of marvelous
RUN apk update && \
   apk upgrade && \
   apk add git

RUN mkdir /app

WORKDIR /app

ADD requirements.txt /app/
RUN pip install -U pip
RUN pip install -r requirements.txt

ADD ./app.py /app/app.py
ADD /query /app/query
ADD ./templates /app/templates

COPY ./docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 5000:5000
