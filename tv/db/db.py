import datetime
import json
import os

import pymysql

import tvdb.api


_CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '.credentials')


INSERT_NEW_UNSEEN = '''
    INSERT INTO unseen
    (user_id, episode_id, subscription_id)
    SELECT user_id, %s, id
    FROM subscription
    WHERE series_id = %s
'''

INSERT_UNSEEN_FOR_SUBSCRIPTION = '''
    INSERT INTO UNSEEN
    (user_id, episode_id, subscription_id)
    SELECT %s, id, %s
    FROM episode
    WHERE series_id = %s
'''

SUBSCRIPTION_INSERT = 'INSERT INTO subscription (user_id, series_id) VALUES (%s, %s)'

WATCH = 'DELETE FROM unseen WHERE user_id = %s AND episode_id = %s'

GET_EPISODE_DATA = 'SELECT series_id, season, episode FROM episode WHERE id = %s'
EPISODES_UNTIL = '''
    SELECT id FROM episode
    WHERE
        series_id = %s AND (
            season < %s OR
            (season = %s AND episode <= %s)
        )
'''


class ShowDatabase(object):
    def __init__(self):
        self._api = tvdb.api.TvDbApi()
        with open(_CREDENTIALS_FILE) as cred_fobj:
            credentials = json.load(cred_fobj)
        self._connection = pymysql.connect(**credentials)

    def _get_last_updated(self, series_id):
        with self._connection.cursor() as cursor:
            results = cursor.execute('SELECT last_updated FROM series WHERE id = %s', (series_id,))
            if results:
                return cursor.fetchone()[0]
            else:
                return -1

    def _episode_ids(self, series_id):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT id FROM episode WHERE series_id = %s', (series_id,))
            return {row[0] for row in cursor.fetchall()}

    @staticmethod
    def _insert_update(cursor, table, row_id, **fields):
        query = 'INSERT INTO {} (id, {}) VALUES (%s, {}) ON DUPLICATE KEY UPDATE {}'.format(
            table,
            ', '.join(fields.keys()),
            ', '.join('%s' for _ in fields),
            ', '.join(map('{}=%s'.format, fields.keys())),
        )
        cursor.execute(query, (row_id,) + tuple(fields.values()) + tuple(fields.values()))

    def update_series(self, series_id, force=False):
        series = self._api.series(series_id)
        last_update = self._get_last_updated(series_id)
        if last_update == series['lastUpdated'] and not force:
            return

        current_episodes = self._episode_ids(series_id)
        new_episodes = []
        with self._connection.cursor() as cursor:
            self._insert_update(
                cursor=cursor,
                table='series',
                row_id=series_id,
                name=series['seriesName'],
                air_time=datetime.datetime.strptime(series['airsTime'], '%I:%M %p').time(),
                episode_length=int(series['runtime']),
                last_updated=int(series['lastUpdated']),
                network=series['network'],
            )
            for episode in self._api.episodes(series_id):
                if not episode['firstAired']:
                    continue
                episode_id = int(episode['id'])
                self._insert_update(
                    cursor=cursor,
                    table='episode',
                    row_id=episode_id,
                    series_id=series_id,
                    season=int(episode['airedSeason']),
                    episode=int(episode['airedEpisodeNumber']),
                    title=episode['episodeName'],
                    air_date=datetime.datetime.strptime(episode['firstAired'], '%Y-%m-%d').date(),
                )
                if episode_id not in current_episodes:
                    new_episodes.append((episode_id, series_id))
            cursor.executemany(INSERT_NEW_UNSEEN, new_episodes)

        self._connection.commit()

    def subscribe(self, user_id, series_id):
        self.update_series(series_id)
        with self._connection.cursor() as cursor:
            cursor.execute(SUBSCRIPTION_INSERT, (user_id, series_id))
            cursor.execute(INSERT_UNSEEN_FOR_SUBSCRIPTION, (user_id, cursor.lastrowid, series_id))
        self._connection.commit()

    def watch(self, user_id, episode_id):
        with self._connection.cursor() as cursor:
            cursor.execute(WATCH, (user_id, episode_id))
        self._connection.commit()

    def watch_until(self, user_id, episode_id):
        with self._connection.cursor() as cursor:
            cursor.execute(GET_EPISODE_DATA, (episode_id,))
            series_id, season, episode = cursor.fetchone()
            cursor.execute(EPISODES_UNTIL, (series_id, season, season, episode))
            episode_ids = cursor.fetchall()
            cursor.executemany(WATCH, ((user_id, episode_id) for episode_id in episode_ids))
        self._connection.commit()

    def user_names(self):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT name FROM user ORDER BY id')
            return [name for name, in cursor.fetchall()]

    def get_user_id(self, username):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT id FROM user WHERE name = %s', username)
            return cursor.fetchone()[0]

    def get_user_name(self, uid):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT name FROM user WHERE id = %s', uid)
            return cursor.fetchone()[0]
