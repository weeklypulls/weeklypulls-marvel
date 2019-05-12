import logging
from operator import itemgetter

import marvelous
from query.api import get_api

logger = logging.getLogger('flask.app')

def week_of_day(day):
    print(f'Fetching week {day} from API')
    api = get_api()
    # what would we do if there were more than 100 releases on the same day...?
    # I guess it's an issue in marvelous rather than here.
    comics = api.comics({
        'format': "comic",
        'formatType': "comic",
        'noVariants': True,
        'dateRange': "{day},{day}".format(day=day),
        'limit': 100
    })

    fetched = [{'id': comic.id,
                'title': comic.title,
                'on_sale': comic.dates.on_sale,
                'series_id': comic.series.id,
                'images': comic.images,
                } for comic in comics]

    fetched.sort(key=itemgetter('title'))
    return fetched


def all_comics_for_series(series_obj):
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
