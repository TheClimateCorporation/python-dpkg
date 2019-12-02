#!/bin/sh -ex

if ! [ -f venv2/bin/activate ]; then
  virtualenv venv2
fi

. venv2/bin/activate

pip install -U pip setuptools

python setup.py sdist bdist_wheel

twine upload dist/*
