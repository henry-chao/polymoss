#!/bin/bash

export FLASK_APP=/home/hchao/polymoss/index.py
export FLASK_DEBUG=0

flask run -h 0.0.0.0 -p 8080

