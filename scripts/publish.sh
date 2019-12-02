#!/bin/sh -ex

if ! [ -f venv/bin/activate ]; then
  virtualenv --python=$(which python3) venv
fi

. venv/bin/activate

pip install -U pip setuptools twine

python setup.py sdist bdist_wheel

twine upload dist/*
