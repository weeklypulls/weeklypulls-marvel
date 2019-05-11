from operator import itemgetter

from query.api import get_api


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
