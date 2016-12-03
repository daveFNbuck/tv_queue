import datetime
import json
from six.moves.urllib.error import HTTPError
import six.moves.urllib.parse
import six.moves.urllib.request

from retry_decorator import retry


with open('/etc/tvq/api_key') as api_fobj:
    API_KEY = api_fobj.read().rstrip('\n')

API_URL = 'https://api.thetvdb.com/'

SEARCH = 'search/series?name={}'
SERIES = 'series/{}'
EPISODES = 'series/{}/episodes?page={}'


class TvDbApi(object):
    def __init__(self, api_key=API_KEY):
        self._key = api_key
        self._get_token()

    def _get_token(self):
        # expire after 23 hours to avoid race conditions
        self._expiration = datetime.datetime.now() + datetime.timedelta(hours=23)

        data = json.dumps({'apikey': self._key})
        request = six.moves.urllib.request.Request(
            url=six.moves.urllib.parse.urljoin(API_URL, 'login'),
            data=str.encode(data),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
        )
        response = six.moves.urllib.request.urlopen(request).read()
        self._token = json.loads(response.decode('utf-8'))['token']

    def _update_token(self):
        if datetime.datetime.now() > self._expiration:
            self._get_token()

    def _headers(self):
        self._update_token()
        return {
            'Accept': 'application/json',
            'Authorization': 'Bearer {}'.format(self._token),
        }

    @retry(Exception, tries=3, timeout_secs=0.1)
    def _get(self, url_format, *parameters):
        assert not any('/' in param for param in parameters)
        safe_inputs = (six.moves.urllib.parse.quote(param, safe='') for param in parameters)
        url = six.moves.urllib.parse.urljoin(API_URL, url_format.format(*safe_inputs))
        request = six.moves.urllib.request.Request(url=url, headers=self._headers())
        try:
            response = six.moves.urllib.request.urlopen(request).read()
        except HTTPError as ex:
            if ex.code == 404:
                return None
            else:
                raise
        loaded_response = json.loads(response.decode('utf-8'))
        if 'errors' in loaded_response:
            raise RuntimeError('error loading {}: {}'.format(url, loaded_response['errors']))
        return loaded_response

    def search(self, query):
        results = self._get(SEARCH, query)
        return [] if results is None else results['data']

    def series(self, series_id):
        return self._get(SERIES, str(series_id))['data']

    def episodes(self, series_id):
        next_page = 1
        while next_page is not None:
            page = self._get(EPISODES, str(series_id), str(next_page))
            next_page = page['links']['next']
            for datum in page['data']:
                yield datum
