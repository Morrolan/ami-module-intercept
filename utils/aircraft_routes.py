"""On-selection public callsign lookup; no flight-route database is built."""
import json
import re
import threading
import time
from collections import OrderedDict

import requests

SOURCE = 'https://www.adsbdb.com/'
API = 'https://api.adsbdb.com/v0/callsign/'


def _airport(value):
    if not isinstance(value, dict):
        return None
    iata, icao = value.get('iata_code'), value.get('icao_code')
    if not isinstance(icao, str) or not re.fullmatch(r'[A-Z0-9]{4}', icao):
        return None
    return {'iata': iata if isinstance(iata, str) and re.fullmatch(r'[A-Z0-9]{3}', iata) else '',
            'icao': icao, 'name': str(value.get('name') or '')[:160]}


class RouteCache:
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def get(self, callsign):
        if not re.fullmatch(r'[A-Z]{2,3}\d[A-Z0-9]{0,5}', callsign) or len(callsign) > 8:
            raise ValueError('Invalid airline callsign')
        with self.lock:
            cached = self.entries.get(callsign)
            if cached and time.monotonic() < cached[0]:
                self.entries.move_to_end(callsign)
                return cached[1]
            result = {'callsign': callsign, 'available': False, 'origin': None, 'destination': None,
                      'source': SOURCE, 'message': 'No callsign route available.'}
            ttl, response = 300, None
            try:
                response = requests.get(API + callsign, timeout=(3, 5), stream=True, allow_redirects=False,
                                        headers={'User-Agent': 'Intercept personal selected-aircraft lookup'})
                if response.status_code == 404:
                    pass
                elif response.status_code != 200:
                    raise ValueError('Lookup unavailable')
                else:
                    chunks, size = [], 0
                    for chunk in response.iter_content(chunk_size=8192):
                        size += len(chunk)
                        if size > 65536:
                            raise ValueError('Route response too large')
                        chunks.append(chunk)
                    raw = json.loads(b''.join(chunks))['response']['flightroute']
                    if callsign not in (raw.get('callsign'), raw.get('callsign_icao'), raw.get('callsign_iata')):
                        raise ValueError('Mismatched callsign route')
                    origin, destination = _airport(raw.get('origin')), _airport(raw.get('destination'))
                    if origin and destination:
                        result.update(available=True, origin=origin, destination=destination,
                                      message='Callsign route; may differ from the current flight.')
                        ttl = 900
            except Exception:
                ttl = 60
                result['message'] = 'Route lookup temporarily unavailable.'
            finally:
                if response is not None:
                    response.close()
            self.entries[callsign] = (time.monotonic() + ttl, result)
            self.entries.move_to_end(callsign)
            while len(self.entries) > 512:
                self.entries.popitem(last=False)
            return result


route_cache = RouteCache()
