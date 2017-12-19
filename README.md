Weekly Pulls - Marvel
=====================

A simple Python Flask application for serving up Marvel comics information for
my Weekly Pulls project.

## Development Setup

* `virtualenv venv`

* `source venv/bin/activate`

* `pip install -r requirements.txt`

* `python app.py`

## Deploy

* `heroku create`

* `heroku addons:create heroku-postgresql:hobby-dev`

* `git push heroku master`
