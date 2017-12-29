import os
import marvelous
import json
from random import randint
from datetime import date, datetime

from flask import Flask, render_template
from flask_cors import CORS
from flask_cacheify import init_cacheify

app = Flask(__name__)
CORS(app)
cache = init_cacheify(app)


def series_cache_time():
    ONE_DAY = 60 * 60 * 24
    return randint(7, 14) * ONE_DAY


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def get_api():
    public_key = os.environ['MAPI_PUBLIC_KEY']
    private_key = os.environ['MAPI_PRIVATE_KEY']
    marvel_api = marvelous.api(public_key, private_key)
    return marvel_api


def all_comics_for_series(series):
    LIMIT = 100
    offset = 0
    total = None
    comics = []
    fetches = 0

    while total is None or offset < total:
        print('Fetching {} comics from {} offset, out of {}'.format(LIMIT, offset, total))
        response = series.comics({
            'format': 'comic',
            'formatType': 'comic',
            'noVariants': True,
            'limit': LIMIT,
            'offset': offset,
            'orderBy': 'issueNumber'
        })
        comics += response.comics
        total = response.response['data']['total']
        offset += LIMIT
        fetches += 1

        # Just a safety break. No comic has more than 1k issues
        if fetches > 10:
            break

    return comics


@app.route('/series/<series_id>/', methods=['GET'])
def series(series_id):
    response = cache.get(series_id)
    if response:
        return response

    # raise Exception('Turning off API requests while I wait for rate limiter to expire')
    print('Fetching series {} from API'.format(series_id))
    api = get_api()
    series = api.series(series_id)

    response = {
        'title': series.title,
        'comics': [],
        'series_id': series.id,
    }

    comics = all_comics_for_series(series)

    for comic in comics:
        response['comics'].append({
            'id': comic.id,
            'title': comic.title,
            'on_sale': comic.dates.on_sale,
            'series_id': series.id,
            'images': comic.images,
        })

    response_json = json.dumps(response, default=json_serial)
    cache.set(series_id, response_json, series_cache_time())
    return response_json


@app.route('/weeks/<week_of>/', methods=['GET'])
def weeks(week_of):
    response = cache.get(week_of)
    if response:
        return response

    print('Fetching week {} from API'.format(week_of))
    api = get_api()
    comics = api.comics({
        'format': "comic",
        'formatType': "comic",
        'noVariants': True,
        'dateRange': "{day},{day}".format(day=week_of),
        'limit': 100
    })

    response = {
        'week_of': week_of,
        'comics': [],
    }

    for comic in comics:
        response['comics'].append({
            'id': comic.id,
            'title': comic.title,
            'on_sale': comic.dates.on_sale,
            'series_id': comic.series.id,
            'images': comic.images,
        })

    response_json = json.dumps(response, default=json_serial)
    cache.set(week_of, response_json, series_cache_time())
    return response_json


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
