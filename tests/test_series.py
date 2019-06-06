import json
from urllib.parse import quote_plus

import arrow as arrow
import pytest
from vcr import VCR

import app

# configure http recorder
my_vcr = VCR(
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

_COMICS_ATTRIBUTES = ['id', 'title', 'on_sale', 'series_id', 'images']
_SERIES_ATTRIBUTES = ['title', 'series_id', 'thumb']


def _structure_matches(attrs, list_of_dicts):
    return all(key in obj for key in attrs
               for obj in list_of_dicts)


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
    assert _structure_matches(_SERIES_ATTRIBUTES, [data])
    assert len(data['comics']) == 27
    assert _structure_matches(_COMICS_ATTRIBUTES, data['comics'])


@my_vcr.use_cassette
def test_series_ongoing(client):
    """ this only tests output dicts are compliant,
    not that the returned series are correct"""
    result = client.get(f'/series/ongoing', follow_redirects=True)
    data = json.loads(result.data)
    assert _structure_matches(_SERIES_ATTRIBUTES, data)


@my_vcr.use_cassette
def test_series_search(client):
    #  fixme: should probably use something with more complex chars
    title = "Weapon X"
    result = client.get(f'/search/series?t={quote_plus(title)}')
    data = json.loads(result.data)
    assert len(data) == 3
    assert _structure_matches(_SERIES_ATTRIBUTES, data)
    assert all(title in comic['title'] for comic in data)

    result_empty = client.get('/search/series?wrong=true')
    assert result_empty.status_code == 400
    result_empty2 = client.get('/search/series')
    assert result_empty2.status_code == 400


@my_vcr.use_cassette
def test_get_week(client):
    day = '2019-05-08'
    result = client.get(f'/weeks/{day}/', follow_redirects=True)
    data = json.loads(result.data)
    assert len(data['comics']) == 21
    assert _structure_matches(_COMICS_ATTRIBUTES, data['comics'])
    start, end = arrow.get(day).span('week')
    assert all(start <= arrow.get(comic['on_sale']) <= end
               for comic in data['comics'])


@my_vcr.use_cassette
def test_aggregated(client):
    series_ids = [23012, 2121]  # Weapon X (short series) + Fantastic Four (big series)
    result = client.get(f'/series/aggregate?series={",".join(str(sid) for sid in series_ids)}')
    data = json.loads(result.data)
    assert len(data) == len(series_ids)
    assert _structure_matches(_SERIES_ATTRIBUTES, data)
    for series in data:
        assert _structure_matches(_COMICS_ATTRIBUTES, series['comics'])
        assert series['series_id'] in series_ids
