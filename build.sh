#!/usr/bin/env bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
mkdir -p media


#!/usr/bin/env bash

apt-get update && apt-get install -y ffmpeg

pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate