import logging
from datetime import datetime
from operator import itemgetter

from query.api import get_api, _DEFAULT_IMG, make_comic_dict
from query.comics import all_comics_for_series

# logging to the main logger for now
logger = logging.getLogger('flask.app')


def get_ongoing():
    """ Retrieve all series that are supposedly ongoing.
    This call is *very* slow and expensive

    :return: list of dicts with subset representation of
            :class:`marvelous.Series` instances
    """

    logger.debug('Fetching ONGOING series from API, '
                 'this will take a while...')
    api = get_api()
    # unfortunately, there is no alternative but to fetch them all
    # (550 at last check) and then filter the ones with endYear set to 2099.
    # I asked Marvel to fix this but I bet they will never do it...
    fetched = []
    offset = 0
    page_size = 100  # 100 is max
    this_year = datetime.now().year
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
            if series_obj.endYear > this_year:
                output = {
                    'title': series_obj.title,
                    'series_id': series_obj.id,
                    'thumb': series_obj.thumbnail or _DEFAULT_IMG
                }
                fetched.append(output)
        # how many records we examined
        num_records = offset + len(series_list)
        logger.debug(f"fetched {num_records} results...")
        # set the offset forward
        offset += page_size
        # if the number of records is lower than the next offset,
        # we're done
        if num_records < offset:
            break

    logger.info(f'Completed "ongoing" call, '
                f'found {len(fetched)} out of {num_records} series.')
    fetched.sort(key=itemgetter('title'))
    return fetched


def get_series_by_id(series_id):
    logger.info(f'Fetching series {series_id} from API')
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
        response['comics'].append(make_comic_dict(comic))
    return response


def search_by_filter(params_dict):
    logger.info(f'Fetching series with parameters: {params_dict}')
    api = get_api()
    found_series = api.series(params=params_dict)
    fetched = [{
        'title': series_obj.title,
        'series_id': series_obj.id,
        'thumb': series_obj.thumbnail or _DEFAULT_IMG
    } for series_obj in found_series]
    fetched.sort(key=itemgetter('title'))
    return fetched