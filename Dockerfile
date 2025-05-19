FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=0

RUN apk add --no-cache gcc \
                       musl-dev \
                       python3-dev \
                       linux-headers \
                       libmemcached-dev \
                       cyrus-sasl-dev \
                       zlib-dev

# For installing packages from Git
RUN apk add --no-cache git

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

EXPOSE 5000
