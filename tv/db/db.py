import datetime
import itertools
import json
import os

import pymysql

import tvdb.api


_CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '.credentials')

EPISODE_REPLACE = '''
    INSERT INTO episode
    (id, series_id, season, episode, title, air_date)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE season=%s, episode=%s, title=%s, air_date=%s
'''

SERIES_REPLACE = '''
    INSERT INTO series
    (id, name, air_time, episode_length, last_updated, network)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE name=%s, air_time=%s, episode_length=%s, last_updated=%s, network=%s
'''

INSERT_NEW_UNSEEN = '''
    INSERT INTO unseen
    (user_id, episode_id)
    SELECT user_id, %s
    FROM subscription
    WHERE series_id = %s
'''

INSERT_UNSEEN_FOR_SUBSCRIPTION = '''
    INSERT INTO UNSEEN
    (user_id, episode_id)
    SELECT %s, id
    FROM episode
    WHERE series_id = %s
'''

SUBSCRIPTION_INSERT = 'INSERT INTO subscription (user_id, series_id) VALUES (%s, %s)'


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

    def update_series(self, series_id, force=False):
        series = self._api.series(series_id)
        last_update = self._get_last_updated(series_id)
        if last_update == series['lastUpdated'] and not force:
            return

        current_episodes = self._episode_ids(series_id)
        new_episodes = []
        with self._connection.cursor() as cursor:
            cursor.execute(SERIES_REPLACE, (
                series_id,
                series['seriesName'],
                datetime.datetime.strptime(series['airsTime'], '%I:%M %p').time(),
                int(series['runtime']),
                int(series['lastUpdated']),
                series['network'],
                series['seriesName'],
                datetime.datetime.strptime(series['airsTime'], '%I:%M %p').time(),
                int(series['runtime']),
                int(series['lastUpdated']),
                series['network'],
            ))
            for episode in self._api.episodes(series_id):
                if not episode['firstAired']:
                    continue
                episode_id = int(episode['id'])
                cursor.execute(EPISODE_REPLACE, (
                    episode_id,
                    series_id,
                    int(episode['airedSeason']),
                    int(episode['airedEpisodeNumber']),
                    episode['episodeName'],
                    datetime.datetime.strptime(episode['firstAired'], '%Y-%m-%d').date(),
                    int(episode['airedSeason']),
                    int(episode['airedEpisodeNumber']),
                    episode['episodeName'],
                    datetime.datetime.strptime(episode['firstAired'], '%Y-%m-%d').date(),
                ))
                if episode_id not in current_episodes:
                    new_episodes.append((episode_id, series_id))
            cursor.executemany(INSERT_NEW_UNSEEN, new_episodes)

        self._connection.commit()

    def subscribe(self, user_id, series_id):
        self.update_series(series_id)
        with self._connection.cursor() as cursor:
            cursor.execute(SUBSCRIPTION_INSERT, (user_id, series_id))
            cursor.execute(INSERT_UNSEEN_FOR_SUBSCRIPTION, (user_id, series_id))
        self._connection.commit()
