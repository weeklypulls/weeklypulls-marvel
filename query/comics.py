import logging
from operator import itemgetter

import marvelous
from query.api import get_api, make_comic_dict

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

    fetched = [make_comic_dict(comic) for comic in comics]

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


def comic_by_id(comic_id):
    api = get_api()
    # the api needs work...
    api_result = api.call(['comics', comic_id])
    if not api_result.get('code', 0) == 200:
        return None
    if not api_result.get('data', {}).get('count', 0) > 0:
        return None
    comic, errors = marvelous.comic.ComicSchema().load(
        api_result['data']['results'][0])
    if errors:
        logger.error(
            f"Errors in comic_by_id for id {comic_id}: {errors}")
    if not hasattr(comic, 'id'):
        logger.error(
            f"Failed unmarshalling in comic_by_id, data was {api_result}")
        return None
    return make_comic_dict(comic)
