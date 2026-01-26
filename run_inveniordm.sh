#!/bin/bash

set -o errexit

docker build -t inveniordm-dev-img ./serve-inveniordm
python3 -m venv venv
source ./venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r ./serve-inveniordm/tests/requirements.txt
export IMAGE_NAME=inveniordm-dev-img
python3 -m pytest ./serve-inveniordm/