# -*- coding:utf8 -*-
# !/usr/bin/env python
from __future__ import print_function
from future.standard_library import install_aliases

install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os

from flask import Flask
from flask import request
from flask import make_response


app = Flask(__name__)


@app.route('/', methods=['POST, GET'])
def index():
    return "Forbidden"


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)


    print("initial request" + str(req))
    import requests

    print("imported req")
    url = "https://scorpa.ml/menuet/bot/webhook"
    r = requests.post(url, json.dumps(req))
    print("reequests fetched this shit" + str(r))
    return r
    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)
    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')