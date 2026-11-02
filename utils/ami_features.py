"""Public, static feature descriptions. Never describe live data or identities."""

# Names/locations follow the navigation; SPACE WX is the on-screen indicator.
# Keep this explicit: importing or executing the browser registry is unnecessary.
_CATALOG = [
    ('pager', 'Pager', 'Signals > Pager', ['pagers', 'POCSAG', 'FLEX'], 'Decode pager signals; AMI exposes activity counts only, never message payloads.'),
    ('sensor', '433MHz', 'Signals > 433MHz', ['433 MHz', '433MHz sensors', 'weather stations', 'rtl_433'], 'Receive 433 MHz sensor and meter broadcasts, including receive-only Flipper input.'),
    ('rtlamr', 'Meters', 'Signals > Meters', ['utility meters', 'rtlamr', 'meter readings'], 'Receive compatible utility-meter broadcasts.'),
    ('subghz', 'SubGHz', 'Signals > SubGHz', ['sub-ghz', 'sub GHz', 'Flipper'], 'Sub-GHz radio controls and signal reception; AMI only reads activity.'),
    ('waterfall', 'Waterfall', 'Signals > Waterfall', ['spectrum', 'spectrum analyser', 'frequency spectrum'], 'View signal strength across frequencies in a spectrum waterfall.'),
    ('morse', 'Morse', 'Signals > Morse', ['CW', 'Morse code'], 'Receive and decode CW Morse signals.'),
    ('ook', 'OOK Decoder', 'Signals > OOK Decoder', ['on-off keying', 'OOK', 'remote signals'], 'Inspect and decode on-off keyed radio signals.'),
    ('adsb', 'Aircraft', 'Tracking > Aircraft', ['ADS-B', 'ADSB', 'planes', 'aircraft', 'flights'], 'Track ADS-B aircraft; exact retained and fresh aircraft counts with a recent contact sample.'),
    ('ais', 'Vessels', 'Tracking > Vessels', ['AIS', 'ships', 'vessels', 'boats'], 'Track AIS vessels; exact retained and fresh vessel counts with a recent contact sample.'),
    ('acars', 'ACARS', 'Tracking > Aircraft > ACARS', ['aircraft messages', 'aircraft datalink', 'ACARS messages'], 'Receive ACARS aircraft datalink messages; AMI exposes activity counts only.'),
    ('vdl2', 'VDL2', 'Tracking > Aircraft > VDL2', ['VDL Mode 2', 'VDL-2', 'digital aircraft messages'], 'Receive VDL Mode 2 aircraft datalink; AMI exposes activity counts only.'),
    ('aprs', 'APRS', 'Tracking > APRS', ['packet radio', 'amateur radio tracking'], 'Receive amateur packet-radio station reports and positions.'),
    ('gps', 'GPS', 'Tracking > GPS', ['GNSS', 'GPS receiver', 'GPSD'], 'View the connected GPS receiver; AMI never shares observer coordinates.'),
    ('radiosonde', 'Radiosonde', 'Tracking > Radiosonde', ['weather balloons', 'sondes', 'balloons'], 'Decode and track radiosonde weather balloons.'),
    ('satellite', 'Satellite', 'Space > Satellite', ['satellites', 'satellite passes', 'orbital tracking'], 'Predict satellite passes and monitor ground-station activity.'),
    ('iss', 'ISS Live', 'Space > ISS Live', ['ISS', 'International Space Station', 'space station'], 'View the International Space Station orbit and live tracking display.'),
    ('sstv', 'ISS SSTV', 'Space > ISS SSTV', ['ISS images', 'space station pictures'], 'Receive slow-scan television images transmitted by the ISS.'),
    ('weathersat', 'Weather Sat', 'Space > Weather Sat', ['weather satellites', 'NOAA APT', 'Meteor LRPT', 'HRPT'], 'Decode weather-satellite imagery from live reception or supported recordings.'),
    ('wefax', 'WeFax', 'Space > WeFax', ['weather fax', 'HF fax', 'weather charts'], 'Receive radio weather-fax charts.'),
    ('sstv-general', 'HF SSTV', 'Space > HF SSTV', ['slow scan television', 'SSTV', 'HF images'], 'Receive amateur-radio slow-scan television images.'),
    ('spaceweather', 'SPACE WX', 'Space > Space Weather (SPACE WX)', ['Space Weather', 'space weather', 'aurora', 'Kp', 'solar flares', 'geomagnetic storm'], 'Read NOAA SWPC Kp, three-day forecast, R/S/G scales, solar flux, alerts and solar wind.'),
    ('meteor', 'Meteor Scatter', 'Space > Meteor Scatter', ['meteor scatter', 'meteor detection', 'meteors'], 'Monitor meteor-scatter radio echoes.'),
    ('wifi', 'WiFi', 'Wireless > WiFi', ['Wi-Fi', 'wireless networks', 'WiFi presence'], 'Monitor WiFi presence; AMI exposes counts only, never network or device identities.'),
    ('bluetooth', 'Bluetooth', 'Wireless > Bluetooth', ['BLE', 'Bluetooth presence'], 'Monitor Bluetooth presence; AMI exposes counts only, never device identities.'),
    ('bt-locate', 'BT Locate', 'Wireless > BT Locate', ['Bluetooth locate', 'BLE locate', 'SAR tracker'], 'Locate Bluetooth signals; AMI only reports activity, never identities or observer coordinates.'),
    ('wifi-locate', 'WF Locate', 'Wireless > WF Locate', ['WiFi Locate', 'Wi-Fi locate'], 'Locate WiFi signals; AMI only reports activity, never identities or observer coordinates.'),
    ('meshtastic', 'Meshtastic', 'LoRa > Meshtastic', ['LoRa mesh', 'Meshtastic mesh'], 'Monitor Meshtastic mesh-radio activity; AMI does not expose message content.'),
    ('meshcore', 'Meshcore', 'LoRa > Meshcore', ['MeshCore', 'Meshcore mesh'], 'Monitor MeshCore mesh-radio activity; AMI does not expose message content.'),
    ('tscm', 'TSCM', 'Intel > TSCM', ['counter surveillance', 'bug detection', 'RF survey'], 'Survey radio activity for counter-surveillance; AMI reports activity only.'),
    ('tscmsurvey', 'TSCM Survey', 'Intel > TSCM Survey', ['survey workspace', 'TSCM cases'], 'Organize counter-surveillance surveys and cases.'),
    ('activity', 'Activity', 'Intel > Activity', ['activity feed', 'observations'], 'Review the unified signal-observation feed.'),
    ('spystations', 'Spy Stations', 'Intel > Spy Stations', ['number stations', 'numbers stations'], 'Browse known spy and numbers-station information.'),
    ('websdr', 'WebSDR', 'Intel > WebSDR', ['shortwave', 'remote HF', 'HF receiver'], 'Listen to remote HF and shortwave receivers in the browser.'),
    ('drone', 'Drone Intel', 'Intel > Drone Intel', ['drones', 'drone detection', 'Remote ID'], 'Monitor drone signals and correlate detections.'),
    ('identity-management', 'Identity Management', 'System > Identity Management', ['accounts', 'users', 'account management'], 'Manage local Intercept accounts; AMI read tools never change accounts.'),
    ('system', 'Health', 'System > Health', ['System', 'system health', 'system monitor'], 'Inspect Intercept host and service health in the application.'),
]


def features():
    """Fresh objects prevent callers mutating the public catalog."""
    return [{'id': ident, 'name': name, 'aliases': list(aliases), 'where': where,
             'summary': summary, 'tools': ['get_space_weather'] if ident == 'spaceweather' else
             ['get_overview', 'get_contacts'] if ident in ('adsb', 'ais') else ['get_overview']}
            for ident, name, where, aliases, summary in _CATALOG]
