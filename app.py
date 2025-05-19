import json
import os
from datetime import date, datetime
from hashlib import sha1
from random import randint
from typing import Any, Dict, List, Optional

from flask import Flask, abort, jsonify, request, render_template, make_response
from flask_cacheify import init_cacheify
from flask_cors import CORS

from marvelous.exceptions import ApiError
from query.comics import week_of_day, comic_by_id
from query.series import get_ongoing, get_series_by_id, search_by_filter

app = Flask(__name__)
CORS(app)
cache = init_cacheify(app)

_ONE_DAY_SECONDS = 60 * 60 * 24


@app.errorhandler(400)
def bad_request(error):
    return jsonify(error=str(error.description)), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify(error=str(error.description)), 404


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify(error=str(error.description)), 500


@app.errorhandler(502)
def bad_gateway(error):
    return jsonify(error=str(error.description)), 502


def series_cache_time() -> int:
    return randint(7, 14) * _ONE_DAY_SECONDS


def week_of_cache_time() -> int:
    return _ONE_DAY_SECONDS


def json_serial(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@app.route('/series/ongoing/', methods=['GET'])
def ongoing_series():
    """ Retrieve all series that are supposedly ongoing.
    This call is *very* slow and expensive when not cached;
    in practice, users should *never* get a non-cached response.

    Returns:
        JSON response containing list of ongoing series
    """
    try:
        response = cache.get('ongoing')
        if response:
            return make_response(response)

        series = get_ongoing()
        response = jsonify([s.to_dict() for s in series])
        cache.set('ongoing', response.get_data(as_text=True), series_cache_time())
        return response
    except ApiError as e:
        abort(502, description=str(e))
    except Exception as e:
        app.logger.error(f"Error in ongoing_series: {str(e)}")
        abort(500, description="Internal server error")


@app.route('/series/<series_id>/', methods=['GET'])
def series(series_id):
    """
    Given a numeric ID, return the Series instance

    Args:
        series_id (str): The numeric ID of the series

    Returns:
        JSON response representing subset of Series instance
    """
    try:
        response = cache.get(series_id)
        if response:
            return make_response(response)

        data = get_series_by_id(series_id)
        response = jsonify(data)
        cache.set(series_id, response.get_data(as_text=True), series_cache_time())
        return response
    except Exception as e:
        app.logger.error(f"Error retrieving series {series_id}: {str(e)}")
        abort(500, description="Internal server error")


@app.route('/series/aggregate', methods=['GET'])
def series_list():
    """
    Given multiple series_id, return all details for them in a huge view.
    This is basically testing the limits of the current approach.

    Query Parameters:
        series (str): A comma-separated list of series IDs

    Returns:
        JSON response containing details for all requested series
    """
    key = 'series'
    if key not in request.args:
        abort(400, description="Missing required parameter 'series'")
    
    sids = request.args[key].split(',')
    # validate format so we don't have to worry later
    if not all(sid.isnumeric() for sid in sids):
        abort(400, description="Invalid series IDs. All IDs must be numeric.")
    
    # dedupe and sort so cache key is consistent regardless of query order
    sids = sorted(set(sids))
    # generate plaintext cache key
    cache_key_plain = '_'.join(sids)
    # hash so we don't care about key length
    # using sha1 because crypto strength is irrelevant here, we want speed
    cache_key = 'aggr_' + sha1(cache_key_plain.encode('ascii')).hexdigest()
    
    response = cache.get(cache_key)
    if response:
        return make_response(response)

    try:
        # retrieve all the info, using cache if possible
        aggregated_data = []
        for sid in sids:
            try:
                cached_series = cache.get(sid)
                if not cached_series:
                    series_data = get_series_by_id(int(sid))
                    response = jsonify(series_data)
                    cache.set(sid, response.get_data(as_text=True), series_cache_time())
                    cached_series = cache.get(sid)
                aggregated_data.append(json.loads(cached_series))
            except Exception as e:
                app.logger.error(f'Error fetching series {sid}: {e}')
                # Skip failed series but continue with others
                continue

        response = jsonify(aggregated_data)
        cache.set(cache_key, response.get_data(as_text=True), week_of_cache_time())
        return response
    except Exception as e:
        app.logger.error(f'Unexpected error in series_list: {e}')
        abort(500, description="Internal server error")


@app.route('/weeks/<week_of>/', methods=['GET'])
def weeks(week_of: str):
    """
    Return all physical releases for the week containing the requested day

    Args:
        week_of (str): Date in format 'yyyy-mm-dd'

    Returns:
        JSON response containing comics released in the specified week
    """
    try:
        response = cache.get(week_of)
        if response:
            return make_response(response)

        data = {
            'week_of': week_of,
            'comics': week_of_day(week_of),
        }
        response = jsonify(data)
        cache.set(week_of, response.get_data(as_text=True), week_of_cache_time())
        return response
    except Exception as e:
        app.logger.error(f'Error fetching week {week_of}: {e}')
        abort(500, description="Internal server error")


@app.route('/search/series/', methods=['GET'])
def search_series():
    """
    Return all series matching the provided querystring.
    
    Query Parameters:
        search (str): Title of the series to search for
    
    Returns:
        JSON list of series representations (without comics)
    """
    try:
        # map our querystring to acceptable Marvel API filters
        key_map = {'search': 'title'}
        filter = {key_map[key]: request.args[key]
                for key in sorted(key_map.keys())
                if key in request.args and request.args[key] != ''}
        
        if not filter:
            abort(400, description="Missing required search parameters")
        
        # calculate an identifier to use with cache
        flat_filter = '||'.join([
            f'{key}::{value}' for key, value in filter.items()
        ])
        search_id = f'search__{flat_filter}'
        
        response = cache.get(search_id)
        if response:
            return make_response(response)
        
        data = search_by_filter(filter)
        response = jsonify(data)
        cache.set(search_id, response.get_data(as_text=True), week_of_cache_time())
        return response
    except Exception as e:
        app.logger.error(f'Error in search_series: {e}')
        abort(500, description="Internal server error")


@app.route('/comics/<comic_id>', methods=['GET'])
def get_comic(comic_id):
    """
    Given an ID, return comic details
    
    Args:
        comic_id (str): The ID of the comic to retrieve
    
    Returns:
        JSON response containing comic details
    """
    try:
        cache_id = f'comic_{comic_id}'
        response = cache.get(cache_id)
        if response:
            return make_response(response)

        data = comic_by_id(comic_id)
        if not data:
            abort(404, description=f"Comic {comic_id} not found")
        
        response = jsonify(data)
        cache.set(cache_id, response.get_data(as_text=True), week_of_cache_time())
        return response
    except Exception as e:
        app.logger.error(f'Error retrieving comic {comic_id}: {e}')
        abort(500, description="Internal server error")


@app.route('/', methods=['GET'])
def index():
    """
    Simple health check endpoint that shows the app is running
    
    Returns:
        JSON response containing basic app health information
    """
    try:
        return jsonify({
            'status': 'ok',
            'version': '1.0.0',
            'message': 'Weekly Pulls Marvel API is running'
        })
    except Exception as e:
        app.logger.error(f'Error in index: {e}')
        abort(500, description="Internal server error")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
