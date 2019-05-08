#!/bin/sh

gunicorn --timeout 240 -b 0.0.0.0:5000 app:app