import os

import marvelous


def get_api():
    """
    Load the Marvel API wrapper
    :return: :class:`marvelous.sessions.Session`
    """
    public_key = os.environ['MAPI_PUBLIC_KEY']
    private_key = os.environ['MAPI_PRIVATE_KEY']
    marvel_api = marvelous.api(public_key, private_key)
    return marvel_api

# what to display when no thumbnail is available
_DEFAULT_IMG = "http://i.annihil.us/u/prod/marvel/i/mg/b/40/image_not_available.jpg"

# standard comic representation in this app
def make_comic_dict(comic_obj):
    return {'id': comic_obj.id,
            'title': comic_obj.title,
            'on_sale': comic_obj.dates.on_sale,
            'series_id': comic_obj.series.id,
            'images': comic_obj.images,
            }