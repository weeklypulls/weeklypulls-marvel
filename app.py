import json
import os
from datetime import date, datetime
from operator import itemgetter
from random import randint

from flask import Flask, render_template, abort
from flask_cacheify import init_cacheify
from flask_cors import CORS

import marvelous
from marvelous.exceptions import ApiError

app = Flask(__name__)
CORS(app)
cache = init_cacheify(app)

_ONE_DAY_SECONDS = 60 * 60 * 24
# what to display when no thumbnail is available
_DEFAULT_IMG = "http://i.annihil.us/u/prod/marvel/i/mg/b/40/image_not_available.jpg"


def series_cache_time():
    return randint(7, 14) * _ONE_DAY_SECONDS


def week_of_cache_time():
    return _ONE_DAY_SECONDS


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def get_api():
    """
    Load the Marvel API wrapper
    :return: :class:`marvelous.sessions.Session`
    """
    public_key = os.environ['MAPI_PUBLIC_KEY']
    private_key = os.environ['MAPI_PRIVATE_KEY']
    marvel_api = marvelous.api(public_key, private_key)
    return marvel_api


def all_comics_for_series(series_obj: marvelous.Series):
    """
    Get all published or announced comics for a series.

    :param series_obj: :class:`marvelous.Series` instance
    :return: `list` of :class:`marvelous.Comic` instances
    """
    limit = 100
    offset = 0
    total = None
    comics = []
    fetches = 0

    while total is None or offset < total:
        print(f'Fetching {limit} comics from {offset} offset, out of {total}')
        response = series_obj.comics({
            'format': 'comic',
            'formatType': 'comic',
            'noVariants': True,
            'limit': limit,
            'offset': offset,
            'orderBy': 'issueNumber'
        })
        comics += response.comics
        total = response.response['data']['total']
        offset += limit
        fetches += 1

        # Just a safety break. No comic has more than 1k issues
        if fetches > 10:
            break

    return comics


@app.route('/series/ongoing/', methods=['GET'])
def ongoing_series():
    """ Retrieve all series that are supposedly ongoing.
    This call is *very* slow and expensive when not cached;
    in practice, users should *never* get a non-cached response.

    :return: json list with subset representation of
            :class:`marvelous.Series` instances
    """

    response = cache.get('ongoing')
    if response:
        return response

    app.logger.debug('Fetching ONGOING series from API, '
                     'this will take a while...')
    api = get_api()
    # unfortunately, there is no alternative but to fetch them all 
    # (550 at last check) and then filter the ones with endYear set to 2099. 
    # I asked Marvel to fix this but I bet they will never do it...
    fetched = []
    offset = 0
    page_size = 100  # 100 is max
    this_year = datetime.now().year
    try:
        while True:
            # Note that 'ongoing' seriesType just means the series was
            # originally published as never-ending (as opposed to miniseries
            # etc). E.g. Spectacular Spider-Man is 'ongoing' even though it
            # has long been dead.
            series_list = api.series(params={'seriesType': 'ongoing',
                                             'limit': page_size,
                                             'offset': offset})
            for series_obj in series_list:
                # ongoing series usually have endYear set to 2099
                if series.endYear == 2099 or series_obj.endYear > this_year:
                    output = {
                        'title': series_obj.title,
                        'series_id': series_obj.id,
                        'thumb': series_obj.thumbnail or _DEFAULT_IMG
                    }
                    fetched.append(output)
            # how many records we examined
            num_records = offset + len(series_list)
            app.logger.debug(f"fetched {num_records} results...")
            # set the offset forward
            offset += page_size
            # if the number of records is lower than the next offset, 
            # we're done
            if num_records < offset:
                break

        app.logger.info(f'Completed "ongoing" call, '
                        f'found {len(fetched)} out of {num_records} series.')
        fetched.sort(key=itemgetter('title'))
        response_json = json.dumps(fetched, default=json_serial)
        cache.set('ongoing', response_json, series_cache_time())
        return response_json
    except ApiError as a:
        app.logger.error(a.args)
        return abort(422)


@app.route('/series/<series_id>/', methods=['GET'])
def series(series_id):
    """
    Given a numeric ID, return the Series instance

    :param series_id: `int`
    :return: json representing subset of :class:`marvelous.Series` instance
    """
    response = cache.get(series_id)
    if response:
        return response

    print(f'Fetching series {series_id} from API')
    api = get_api()
    series_obj = api.series(series_id)

    response = {
        'title': series_obj.title,
        'comics': [],
        'series_id': series_obj.id,
        'thumb': series_obj.thumbnail or _DEFAULT_IMG
    }

    comics = all_comics_for_series(series_obj)

    for comic in comics:
        response['comics'].append({
            'id': comic.id,
            'title': comic.title,
            'on_sale': comic.dates.on_sale,
            'series_id': series_obj.id,
            'images': comic.images,
        })

    response_json = json.dumps(response, default=json_serial)
    cache.set(series_id, response_json, series_cache_time())
    return response_json


@app.route('/weeks/<week_of>/', methods=['GET'])
def weeks(week_of: str):
    """
    Return all physical releases for the week containing the requested day

    :param week_of: `str` of format `yyy-mm-dd`
    :return: `json` with a subset of :class:`marvelous.Comic` details
    """
    response = cache.get(week_of)
    if response:
        return response

    print(f'Fetching week {week_of} from API')
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
    cache.set(week_of, response_json, week_of_cache_time())
    return response_json


@app.route('/', methods=['GET'])
def index():
    """
    Simple ping page
    :return: index page
    """
    return render_template('index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
