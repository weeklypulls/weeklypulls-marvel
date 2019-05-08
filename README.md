Weekly Pulls - Marvel
=====================

A simple Python Flask application for serving up Marvel comics information for
the Weekly Pulls project.

## Development Setup

Create a `.env` file with the Marvel API details as follows:
```dotenv
MAPI_PUBLIC_KEY=yourpubkey
MAPI_PRIVATE_KEY=yourprivkey
```
Then choose one of the following options to run:

### Pure Python
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
source .env
python app.py  # or: heroku local -e .env
```

### Docker
```bash
docker build -t wpmarvel .
docker run -d -p 5000:5000 --env-file .env wpmarvel
```

## Production Setup

### Heroku
```bash
heroku create yourappname
cat .env | xargs -I % heroku config:set % -a yourappname
git push heroku master
```

