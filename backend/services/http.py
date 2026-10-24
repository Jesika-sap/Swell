"""One place for every outside web request.

Every call goes through get_json / post_json so we get the same timeout,
User-Agent and error handling everywhere, and so tests can swap in fake
responses (see tests/fakes.py) without touching the internet.
"""
import requests

import config


class ServiceError(Exception):
    """An outside service failed. The app keeps working without that piece."""


_session = requests.Session()
_session.headers.update({"User-Agent": config.USER_AGENT})

# Tests replace this with a function(method, url, **kw) -> (status, json)
fake = None


def _do(method, url, **kw):
    if fake is not None:
        status, data = fake(method, url, **kw)
        if status >= 400:
            raise ServiceError(f"{url.split('/')[2]} answered {status}")
        return data
    try:
        r = _session.request(method, url, timeout=config.HTTP_TIMEOUT, **kw)
    except requests.RequestException as e:
        raise ServiceError(f"could not reach {url.split('/')[2]}") from e
    if r.status_code >= 400:
        raise ServiceError(f"{url.split('/')[2]} answered {r.status_code}")
    try:
        return r.json()
    except ValueError as e:
        raise ServiceError(f"{url.split('/')[2]} sent something that isn't JSON") from e


def get_json(url, params=None, headers=None):
    return _do("GET", url, params=params, headers=headers)


def post_json(url, body, headers=None):
    return _do("POST", url, json=body, headers=headers)
