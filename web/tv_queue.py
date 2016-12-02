import flask
from flask import request

from tv.db.db import ShowDatabase
from tvdb.api import TvDbApi

app = flask.Flask(__name__)


def render_template(*args, **kwargs):
    kwargs.update(user_data())
    return flask.render_template(*args, **kwargs)


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
@app.route('/queue')
def queue():
    queued_series = ShowDatabase().get_queued_by_series(user_id())
    return render_template(
        'queue.html',
        queued_series=queued_series,
        num_series=len(queued_series),
        num_episodes=sum(series['num_episodes'] for series in queued_series),
    )


@app.route('/login/<username>')
def login(username):
    resp = flask.make_response(flask.redirect('/'))
    resp.set_cookie('uid', str(ShowDatabase().get_user_id(username)))
    return resp


@app.route('/search')
def search():
    api = TvDbApi()
    query = request.args['q']
    results = api.search(query) if query else []
    subscribed_series_ids = set(ShowDatabase().get_subscription_series_ids(user_id()))
    for result in results:
        result['subscribed'] = result['id'] in subscribed_series_ids
    return render_template('search.html', results=results)


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


@app.route('/subscriptions')
def subscriptions():
    data = ShowDatabase().get_subscription_data(user_id())
    return render_template('search.html', results=data)


@app.route('/watch')
def watch():
    episode_id = request.args['episode_id']
    ShowDatabase().watch(user_id(), int(episode_id))
    return episode_id


@app.route('/watchuntil')
def watch_until():
    episode_id = request.args['episode_id']
    ShowDatabase().watch_until(user_id(), int(episode_id))
    return episode_id
