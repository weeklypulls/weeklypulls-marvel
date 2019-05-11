import json
from datetime import datetime
from urllib.parse import quote_plus

import pytest
import vcr
from vcr import VCR

import app

# configure http recorder
my_vcr = vcr.VCR(
    cassette_library_dir='tests/cassettes',
    record_mode='once',
    serializer='json',
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query'],
    path_transformer=VCR.ensure_suffix('.json'),
    decode_compressed_response=True,
    filter_query_parameters=[('apikey', 'XXXXXXX'),
                             ('ts', '2019-05-0501:01:01'),
                             ('hash', 'deadbeef')]
)


@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    yield app.app.test_client()


@my_vcr.use_cassette
def test_series_by_id(client):
    series_id = 23012
    series_title = 'Weapon X (2017 - Present)'
    result = client.get(f'/series/{series_id}', follow_redirects=True)
    data = json.loads(result.data)
    assert data['series_id'] == series_id
    assert data['title'] == series_title
    assert len(data['comics']) == 27


@my_vcr.use_cassette
def test_series_ongoing(client):
    """ this only tests output dicts are compliant, not that the returned series are correct"""
    result = client.get(f'/series/ongoing', follow_redirects=True)
    data = json.loads(result.data)
    this_year = datetime.now().year
    required_keys = ['title', 'series_id', 'thumb']
    assert all(all(key in d for key in required_keys) for d in data)


@my_vcr.use_cassette
def test_series_search(client):
    #  fixme: should probably use something with more complex chars
    title = "Weapon X"
    result = client.get(f'/search/series?t={quote_plus(title)}')
    data = json.loads(result.data)
    assert len(data) == 1
    assert title in data[0]['title']
