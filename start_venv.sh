#!/usr/bin/env bash

ls .venv &> /dev/null || virtualenv -p python3 .venv

. ./.venv/bin/activate
