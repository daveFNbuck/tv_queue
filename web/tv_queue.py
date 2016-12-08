import flask
from flask import request

from tv.db.db import ShowDatabase
from tvdb.api import TvDbApi

app = flask.Flask(__name__)

TVDB_API = None
SHOW_DB = None


def get_api():
    global TVDB_API
    if TVDB_API is None:
        TVDB_API = TvDbApi()
    return TVDB_API


@app.before_request
def clear_cache():
    global SHOW_DB
    SHOW_DB = ShowDatabase(api=False)


def render_template(*args, **kwargs):
    uid = user_id()
    if uid is None:
        return flask.render_template(
            'login.html',
            num_queued=-1,
            num_recording=0,
            users=SHOW_DB.user_names(),
        )

    username = SHOW_DB.get_user_name(uid) if uid else None
    kwargs.update({
        'users': SHOW_DB.user_names(),
        'user': username,
        'num_queued': SHOW_DB.num_queued(uid),
        'num_recording': SHOW_DB.num_recording(uid),
    })
    return flask.render_template(*args, **kwargs)


def user_id():
    cookie = request.cookies.get('uid')
    return int(cookie) if isinstance(cookie, str) else cookie


@app.route('/')
@app.route('/queue')
def queue():
    queued_series = SHOW_DB.get_queued_by_series(user_id())
    return render_template(
        'queue.html',
        queued_series=queued_series,
        num_series=len(queued_series),
        num_episodes=sum(series['num_episodes'] for series in queued_series),
    )


@app.route('/login/<username>')
def login(username):
    resp = flask.make_response(flask.redirect('/'))
    resp.set_cookie('uid', str(SHOW_DB.get_user_id(username)))
    return resp


@app.route('/search')
def search():
    query = request.args['q']
    results = get_api().search(query) if query else []
    subscribed_series_ids = set(SHOW_DB.get_subscription_series_ids(user_id()))
    for result in results:
        result['subscribed'] = result['id'] in subscribed_series_ids
    return render_template('search.html', results=results, is_search=True)


@app.route('/subscribe')
def subscribe():
    series_id = request.args['series_id']
    ShowDatabase(get_api()).subscribe(user_id(), int(series_id))
    return series_id


@app.route('/unsubscribe')
def unsubscribe():
    series_id = request.args['series_id']
    SHOW_DB.unsubscribe(user_id(), int(series_id))
    return series_id


@app.route('/subscriptions')
def subscriptions():
    data = SHOW_DB.get_subscription_data(user_id())
    return render_template('search.html', results=data)


@app.route('/watch')
def watch():
    episode_id = request.args['episode_id']
    SHOW_DB.watch(user_id(), int(episode_id))
    return episode_id


@app.route('/watchuntil')
def watch_until():
    episode_id = request.args['episode_id']
    SHOW_DB.watch_until(user_id(), int(episode_id))
    return episode_id


@app.route('/preview')
def preview():
    return render_template('preview.html', **SHOW_DB.get_preview(user_id(), days=7))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
