from flask import Flask, render_template
from flask import make_response, request, redirect

from tv.db.db import ShowDatabase
from tvdb.api import TvDbApi

app = Flask(__name__)


def user_id():
    cookie = request.cookies.get('uid')
    return int(cookie) if isinstance(cookie, str) else cookie


def user_data():
    db = ShowDatabase()
    uid = user_id()
    username = db.get_user_name(uid) if uid else None
    return {
        'users': db.user_names(),
        'user': username,
    }


@app.route('/')
def queue():
    return render_template('queue.html', **user_data())


@app.route('/login/<username>')
def login(username):
    resp = make_response(redirect('/'))
    resp.set_cookie('uid', str(ShowDatabase().get_user_id(username)))
    return resp


@app.route('/search')
def search():
    api = TvDbApi()
    query = request.args['q']
    results = api.search(query) if query else []
    subscriptions = set(ShowDatabase().get_subscriptions(user_id()))
    for result in results:
        result['subscribed'] = result['id'] in subscriptions
    return render_template('search.html', results=results, **user_data())


@app.route('/subscribe')
def subscribe():
    series_id = request.args['series_id']
    ShowDatabase().subscribe(user_id(), int(series_id))
    return series_id


@app.route('/unsubscribe')
def unsubscribe():
    series_id = request.args['series_id']
    ShowDatabase().unsubscribe(user_id(), int(series_id))
    return series_id
