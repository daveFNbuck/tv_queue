import collections
import datetime
import json

import pymysql

import tvdb.api


_CREDENTIALS_FILE = '/etc/tvq/credentials'


DELETE_EPISODE = '''
    DELETE FROM episode WHERE episode_id = %s
'''

SUBSCRIPTION_INSERT = 'INSERT INTO subscription (user_id, series_id) VALUES (%s, %s)'

WATCH = 'INSERT INTO seen (user_id, episode_id) VALUES (%s, %s)'

GET_EPISODE_DATA = 'SELECT series_id, season, episode FROM episode WHERE id = %s'
EPISODES_UNTIL = '''
    SELECT id FROM episode
    WHERE
        series_id = %s AND (
            season < %s OR
            (season = %s AND episode <= %s)
        )
'''

UPDATE_SUBSCRIPTION = '''
    UPDATE subscription
    SET shift_len = %s, shift_type = %s, enabled = %s
    WHERE id = %s
'''

GET_SUBSCRIPTION_DATA = '''
    SELECT series_id, name, banner, subscription.id, shift_len, shift_type, enabled, network
    FROM
        subscription
        JOIN series ON subscription.series_id = series.id
    WHERE subscription.user_id = %s
    ORDER BY name
'''

Subscription = collections.namedtuple('Subscription', (
    'series_id',
    'name',
    'banner',
    'subscription_id',
    'shift_len',
    'shift_type',
    'enabled',
    'network',
))

GET_UNSEEN = '''
    SELECT
        episode.id,
        title,
        overview,
        banner,
        name,
        series.id,
        season,
        episode,
        air_date,
        air_time,
        episode_length,
        shift_len,
        shift_type
    FROM
        subscription
        JOIN episode USING(series_id)
        JOIN series ON series.id = subscription.series_id
        LEFT JOIN seen ON episode.id = episode_id
    WHERE
        subscription.enabled and subscription.user_id = %s
        AND seen.episode_id IS NULL
'''

TIME_PATTERNS = (
    '%I:%M %p',
    '%I:%M%p',
    '%H:%M',
    '%I%p',
)

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
    'shift_len',
    'shift_type',
))

IGNORED_SORTING_WORDS = ['A', 'AN', 'THE']

SEASON_KEY = 'airedSeason'
EPISODE_KEY = 'airedEpisodeNumber'

def make_unseen(row):
    start = Unseen(*row)
    if start.shift_type == 'HOURS':
        shift = datetime.timedelta(hours=start.shift_len)
    elif start.shift_type == 'DAYS':
        shift = datetime.timedelta(days=start.shift_len)
    air_time = datetime.datetime.combine(start.air_date, datetime.time()) + start.air_time + shift
    return start._replace(air_time=air_time.time(), air_date=air_time.date())


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


def decode_air_time(airtime):
    if not airtime:
        airtime = '12:00 AM'
    for pattern in TIME_PATTERNS:
        try:
            return datetime.datetime.strptime(airtime, pattern).time()
        except ValueError:
            pass
    raise ValueError('Cannot decode time string "{}"'.format(airtime))


class ShowDatabase(object):
    def __init__(self, api=None):
        if api is None:
            api = tvdb.api.TvDbApi()
        self._api = api
        with open(_CREDENTIALS_FILE) as cred_fobj:
            credentials = json.load(cred_fobj)
        self._connection = pymysql.connect(**credentials)
        self._unseen_cache = {}

    def clear_cache(self):
        self._unseen_cache.clear()

    def _get_last_updated(self, series_id):
        with self._connection.cursor() as cursor:
            results = cursor.execute('SELECT last_updated FROM series WHERE id = %s', (series_id,))
            if results:
                return cursor.fetchone()[0]
            else:
                return -1

    def _episode_ids(self, series_id):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT id, season, episode FROM episode WHERE series_id = %s', (series_id,))
            return {
                (season, episode): episode_id
                for episode_id, season, episode in cursor.fetchall()
            }

    @staticmethod
    def _insert_update(cursor, table, keys, **fields):
        query = 'INSERT INTO {} ({}) VALUES ({}) ON DUPLICATE KEY UPDATE {}'.format(
            table,
            ', '.join(fields.keys()),
            ', '.join('%s' for _ in fields),
            ', '.join(map('{}=%s'.format, [key for key in fields.keys() if key not in keys])),
        )
        non_keys = tuple(value for key, value in fields.items() if key not in keys)
        cursor.execute(query, tuple(fields.values()) + non_keys)

    def update_series(self, series_id, force=False):
        series = self._api.series(series_id)
        last_update = self._get_last_updated(series_id)
        if last_update == series['lastUpdated'] and not force:
            return

        current_episodes = self._episode_ids(series_id)
        removed_episodes = []
        with self._connection.cursor() as cursor:
            self._insert_update(
                cursor=cursor,
                table='series',
                keys=('id',),
                id=series_id,
                name=series['seriesName'],
                air_time=decode_air_time(series['airsTime']),
                episode_length=int(series['runtime'] or '0'),
                last_updated=int(series['lastUpdated']),
                network=series['network'][:20] if series['network'] else None,
                banner=series['banner'],
            )
            for episode in self._api.episodes(series_id):
                if episode[SEASON_KEY] is None or episode[EPISODE_KEY] is None:
                    continue
                season_number = int(episode[SEASON_KEY])
                episode_number = int(episode[EPISODE_KEY])
                if not episode['firstAired']:
                    key = (season_number, episode_number)
                    if key in current_episodes:
                        removed_episodes.append(current_episodes[key])
                    continue
                self._insert_update(
                    cursor=cursor,
                    table='episode',
                    keys=('series_id', 'season', 'episode'),
                    series_id=series_id,
                    season=season_number,
                    episode=episode_number,
                    title=episode['episodeName'][:50] if episode['episodeName'] else None,
                    air_date=datetime.datetime.strptime(episode['firstAired'], '%Y-%m-%d').date(),
                    overview=episode['overview'],
                )
            cursor.executemany(DELETE_EPISODE, removed_episodes)

        self._connection.commit()

    def update_all_series(self, force=False):
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT id FROM series')
            series_ids = cursor.fetchall()
        for series_id, in series_ids:
            try:
                self.update_series(series_id, force)
            except Exception as e:
                print('Cannot update series {}: {}'.format(series_id, e))

    def subscribe(self, user_id, series_id):
        self.update_series(series_id)
        with self._connection.cursor() as cursor:
            try:
                cursor.execute(SUBSCRIPTION_INSERT, (user_id, series_id))
            except pymysql.err.IntegrityError:
                return
        self._connection.commit()

    def unsubscribe(self, user_id, series_id):
        with self._connection.cursor() as cursor:
            cursor.execute('DELETE FROM subscription WHERE user_id = %s AND series_id = %s', (user_id, series_id))
        self._connection.commit()

    def watch(self, user_id, episode_id):
        with self._connection.cursor() as cursor:
            cursor.execute(WATCH, (user_id, episode_id))
        self._connection.commit()

    def update_subscription(self, subscription_id, shift_len, shift_type, enabled):
        with self._connection.cursor() as cursor:
            cursor.execute(UPDATE_SUBSCRIPTION, (shift_len, shift_type, enabled, subscription_id))
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
        if uid is None:
            return []
        with self._connection.cursor() as cursor:
            cursor.execute('SELECT series_id FROM subscription WHERE user_id = %s', uid)
            return [user_id for user_id, in cursor.fetchall()]

    def get_subscription_data(self, uid):
        with self._connection.cursor() as cursor:
            cursor.execute(GET_SUBSCRIPTION_DATA, (uid,))
            return [Subscription(*row) for row in sorted(cursor.fetchall(), key=_series_key)]

    def get_unseen_episodes(self, uid):
        if uid is None:
            return []
        if uid not in self._unseen_cache:
            with self._connection.cursor() as cursor:
                cursor.execute(GET_UNSEEN, uid)
                self._unseen_cache[uid] = [make_unseen(row) for row in cursor.fetchall()]
        return self._unseen_cache[uid]

    def get_queued_by_series(self, uid):
        if uid is None:
            return []
        now = datetime.datetime.now()
        series = collections.defaultdict(list)
        for unseen in self.get_unseen_episodes(uid):
            if _start_time(unseen) > now:
                continue
            series[(_sorting_key(unseen.series_name), unseen.series_id)].append(unseen)
        queued = [
            {
                'name': group[0].series_name,
                'id': group[0].series_id,
                'banner': group[0].series_banner,
                'num_episodes': len(group),
                'episodes': list(sorted(group, key=lambda episode: (episode.season, episode.episode))),
            }
            for _, group in sorted(series.items())
        ]
        queued.sort(key=lambda group: _start_time(group['episodes'][-1]), reverse=True)
        return queued

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

    def num_recording(self, uid):
        now = datetime.datetime.now()
        return sum(_start_time(episode) <= now <= _end_time(episode) for episode in self.get_unseen_episodes(uid))
