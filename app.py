import json
import os
from datetime import date, datetime
from random import randint

from flask import Flask, render_template, abort
from flask_cacheify import init_cacheify
from flask_cors import CORS

from marvelous.exceptions import ApiError
from query.series import get_ongoing, get_series_by_id
from query.time import week_of_day

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
