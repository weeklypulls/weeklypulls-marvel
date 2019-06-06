import json
import os
from datetime import date, datetime
from hashlib import sha1
from random import randint

from flask import Flask, render_template, abort, request
from flask_cacheify import init_cacheify
from flask_cors import CORS

from marvelous.exceptions import ApiError
from query.comics import week_of_day, comic_by_id
from query.series import get_ongoing, get_series_by_id, search_by_filter

app = Flask(__name__)
CORS(app)
cache = init_cacheify(app)

_ONE_DAY_SECONDS = 60 * 60 * 24


def series_cache_time():
    return randint(7, 14) * _ONE_DAY_SECONDS


def week_of_cache_time():
    return _ONE_DAY_SECONDS


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


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

    try:
        fetched = get_ongoing()
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

    response = get_series_by_id(series_id)
    response_json = json.dumps(response, default=json_serial)
    cache.set(series_id, response_json, series_cache_time())
    return response_json


@app.route('/series/aggregate', methods=['GET'])
def series_list():
    """
    Given multiple series_id, return all details for them in a huge view.
    This is basically testing the limits of the current approach.

    It must be called with a comma-separated list of series IDs in querystring,
    i.e. ?series=1234,5678,9012...
    """
    key = 'series'
    if not key in request.args:
        abort(400)
    sids = request.args[key].split(',')
    # validate format so we don't have to worry later
    if not all(sid.isnumeric() for sid in sids):
        abort(400)
    # dedupe and sort so cache key is consistent regardless of query order
    sids = sorted(set(sids))
    # generate plaintext cache key
    cache_key_plain = '_'.join(sids)
    # hash so we don't care about key length
    # using sha1 because crypto strength is irrelevant here, we want speed
    cache_key = 'aggregated_' + sha1(cache_key_plain.encode('ascii')).hexdigest()
    response = cache.get(cache_key)
    if response:
        return response

    # retrieve all the info, using cache if possible
    aggregated_data = []
    for sid in sids:
        try:
            cached_series = cache.get(sid)
            if not cached_series:
                cache.set(sid, json.dumps(get_series_by_id(int(sid)),
                                          default=json_serial))
                cached_series = cache.get(sid)
            aggregated_data.append(cached_series)
        except Exception as e:
            app.logger.error(f'Unexpected {type(e)} fetching series {sid}: {e}')

    response_json = f'[{",".join(aggregated_data)}]'
    # todo: here we should check the total size is not over 1mb.
    # If it is, we need to compress it before caching
    cache.set(cache_key, response_json, week_of_cache_time())
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

    response = {
        'week_of': week_of,
        'comics': week_of_day(week_of),
    }
    response_json = json.dumps(response, default=json_serial)
    cache.set(week_of, response_json, week_of_cache_time())
    return response_json


@app.route('/search/series/', methods=['GET'])
def search_series():
    """
    Return all series matching the provided querystring.
    Supported parameters:
        t=my+series+title
    :return: lson list of series representations (without comics)
    """
    # map our querystring to acceptable Marvel API filters
    key_map = {'search': 'title'}
    filter = {key_map[key]: request.args[key]
              for key in sorted(key_map.keys())
              if key in request.args}
    # calculate an identifier to use with cache
    flat_filter = '||'.join([
        f'{key}::{value}' for key, value in filter.items()
    ])
    search_id = f'search__{flat_filter}'
    response = cache.get(search_id)
    if response:
        return response
    response = search_by_filter(filter)
    response_json = json.dumps(response, default=json_serial)
    cache.set(search_id, response_json, week_of_cache_time())
    return response_json


@app.route('/comics/<comic_id>', methods=['GET'])
def get_comic(comic_id):
    """
    Given an ID, return comic details
    :param comic_id: int
    :return: a json comic representation
    """
    cache_id = f'comic_{comic_id}'
    response = cache.get(cache_id)
    if response:
        return response

    response = comic_by_id(comic_id)
    if not response:
        abort(404)
    response_json = json.dumps(response, default=json_serial)
    cache.set(cache_id, response_json, week_of_cache_time())
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
