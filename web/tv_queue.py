from flask import Flask, render_template
from flask import make_response, request, redirect

from tv.db.db import ShowDatabase

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
