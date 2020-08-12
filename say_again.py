#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Server
"""
import bottle
from bottle import request, run, static_file
from config import config
from api import resolve_endpoint
import webbrowser


app = bottle.Bottle()

@app.error(404)
def error404(error):
#    print(error)
    return "Nothing to see here, baby!"

@app.post('/api')
def server_api():
#    for k, v in request.forms.iteritems():
#        print('Form ' + str(k) + ": " + str(v))
#    for k, v in request.files.iteritems():
#        print("File " + str(k) + ": " + str(v))
    endpoint = request.forms.get('endpoint')
    if not endpoint:
        return "Endpoint not found"
    response = resolve_endpoint(endpoint,
                                {k: v for k, v in request.forms.iteritems()},
                                {k: v for k, v in request.files.iteritems()})
    return response


@app.route('/')
def server_index():
    return static_file('upload.html', root=config.STATIC_PATH)

@app.route('/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=config.STATIC_PATH)

URL = 'http://localhost:8014/'

if __name__ == '__main__':
    webbrowser.open(URL)
    run(app, reloader=True, host='localhost', port=8014, debug=True)
    

