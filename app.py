import os
import marvelous
import json
from datetime import date, datetime

from flask import Flask, render_template
from flask.ext.sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/flask_app.db')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)


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
    while total is None or len(comics) < total:
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

    return comics


@app.route('/series/<series_id>/', methods=['GET'])
def series(series_id):
    api = get_api()
    series = api.series(series_id)

    response = {
        'title': series.title,
        'comics': [],
        'series_id': series_id,
    }

    comics = all_comics_for_series(series)

    for comic in comics:
        response['comics'].append({
            'id': comic.id,
            'title': comic.title,
            'on_sale': comic.dates.on_sale,
            'series_id': comic.series.id,
            'images': comic.images,
        })

    return json.dumps(response, default=json_serial)



@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
