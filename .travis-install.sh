#!/bin/bash
pip install tox

if [ "$TOXENV" = 'py34' ]; then
    pip install coveralls
fi

# needed until chromedriver 2.31 is officially released
curl -L 'https://github.com/davidthornton/chromedriver-2.31/blob/master/chromedriver?raw=true' -o /tmp/chromedriver
chmod +x /tmp/chromedriver
