import datetime
import json

import collections
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

GET_SUBSCRIPTION_DATA = '''
    SELECT series_id, name, banner
    FROM
        subscription
        JOIN series ON subscription.series_id = series.id
    WHERE subscription.user_id = %s
    ORDER BY name
'''

GET_UNSEEN = '''
    SELECT episode_id, title, overview, banner, name, series_id, season, episode, air_date, air_time, episode_length
    FROM
        unseen
        JOIN episode ON episode_id = episode.id
        JOIN series ON series_id = series.id
    WHERE user_id = %s
'''

Unseen = collections.namedtuple('Unseen', (
    'episode_id',
    'episode_title',
    'overview',
    'series_banner',
    'series_name',
    'series_id',
    'season',
    'episode',
    'air_date',
    'air_time',
    'episode_length',
))

IGNORED_SORTING_WORDS = ['A', 'AN', 'THE']


def make_unseen(row):
    start = Unseen(*row)
    return start._replace(air_time=(datetime.datetime(2000, 1, 1) + start.air_time).time())


def _start_time(episode):
    return datetime.datetime.combine(episode.air_date, episode.air_time)


def _end_time(episode):
    return _start_time(episode) + datetime.timedelta(minutes=episode.episode_length)


def _sorting_key(title):
    title = title.upper()
    for ignored_word in IGNORED_SORTING_WORDS:
        if title.startswith(ignored_word + ' '):
            title = title[len(ignored_word) + 1:]
    return title


def _series_key(series_tuple):
    return _sorting_key(series_tuple[1])


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
                air_time=datetime.datetime.strptime(series['airsTime'] or '12:01 AM', '%I:%M %p').time(),
                episode_length=int(series['runtime'] or '0'),
                last_updated=int(series['lastUpdated']),
                network=series['network'],
                banner=series['banner'],
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
                    title=episode['episodeName'][:50] if episode['episodeName'] else None,
                    air_date=datetime.datetime.strptime(episode['firstAired'], '%Y-%m-%d').date(),
                    overview=episode['overview'],
                )
                if episode_id not in current_episodes:
                    new_episodes.append((episode_id, series_id))
            cursor.executemany(INSERT_NEW_UNSEEN, new_episodes)

        self._connection.commit()

    def update_all_series(self, force=False):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT id FROM series')
            series_ids = cursor.fetchall()
        for series_id, in series_ids:
            self.update_series(series_id, force)

    def subscribe(self, user_id, series_id):
        self.update_series(series_id)
        with self._connection.cursor() as cursor:
            try:
                cursor.execute(SUBSCRIPTION_INSERT, (user_id, series_id))
            except pymysql.err.IntegrityError:
                return
            cursor.execute(INSERT_UNSEEN_FOR_SUBSCRIPTION, (user_id, cursor.lastrowid, series_id))
        self._connection.commit()

    def unsubscribe(self, user_id, series_id):
        with self._connection.cursor() as cursor:
            cursor.execute('DELETE FROM subscription WHERE user_id = %s AND series_id = %s', (user_id, series_id))
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

    def get_subscription_series_ids(self, uid):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT series_id FROM subscription WHERE user_id = %s', uid)
            return [user_id for user_id, in cursor.fetchall()]

    def get_subscription_data(self, uid):
        with self._connection.cursor() as cursor:
            cursor.execute(GET_SUBSCRIPTION_DATA, (uid,))
            return [
                {
                    'seriesName': name,
                    'id': series_id,
                    'banner': banner,
                    'subscribed': True,
                }
                for series_id, name, banner in sorted(cursor.fetchall(), key=_series_key)
            ]

    def get_unseen_episodes(self, uid):
        with self._connection.cursor() as cursor:
            cursor.execute(GET_UNSEEN, uid)
            return map(make_unseen, cursor.fetchall())

    def get_queued_by_series(self, uid):
        if uid is None:
            return []
        now = datetime.datetime.now()
        series = collections.defaultdict(list)
        for unseen in self.get_unseen_episodes(uid):
            if _end_time(unseen) > now:
                continue
            series[(_sorting_key(unseen.series_name), unseen.series_id)].append(unseen)
        return [
            {
                'name': group[0].series_name,
                'id': group[0].series_id,
                'banner': group[0].series_banner,
                'num_episodes': len(group),
                'episodes': list(sorted(group, key=lambda episode: (episode.season, episode.episode))),
            }
            for _, group in sorted(series.items())
        ]

    def get_preview(self, uid, days):
        now = datetime.datetime.now()
        episodes = [
            episode for episode in self.get_unseen_episodes(uid)
            if _end_time(episode) > now
        ]
        episodes_now = [episode for episode in episodes if _start_time(episode) <= now]
        episodes_now.sort(key=_start_time)
        episodes_later = (episode for episode in episodes if _start_time(episode) > now)

        preview_list = [[] for _ in range(days)]
        for episode in sorted(episodes_later, key=_start_time):
            num_days = (_start_time(episode).date() - now.date()).days
            if num_days >= days:
                break
            preview_list[num_days].append(episode)

        tomorrow = now.date() + datetime.timedelta(days=1)

        def day_name(episode):
            start_date = _start_time(episode).date()
            if start_date == now.date():
                return 'Today'
            elif start_date == tomorrow:
                return 'Tomorrow'
            else:
                return _start_time(episode).strftime('%A')

        preview_days = [
            {
                'day': day_name(day[0]),
                'episodes': day,
            }
            for day in preview_list if day
        ]
        return {'recording': episodes_now, 'preview': preview_days}

    def num_queued(self, uid):
        if uid is None:
            return -1
        return sum(series['num_episodes'] for series in self.get_queued_by_series(uid))
