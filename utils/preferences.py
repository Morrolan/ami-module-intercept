"""Account preference registry, also served to the client in the first head script.

When adding a localStorage key, classify it here (including dynamic prefixes).
Only SYNCED_KEYS may enter the account store. Layout/audio/caches stay local.
"""

from utils.database import get_db

SYNCED_KEYS = frozenset({
    'observerLocation', 'observerLat', 'observerLon', 'ais_observerLocation',
    'radiosonde_observerLocation', 'intercept-theme', 'intercept-ui-tier',
    'intercept_map_theme_pref', 'interceptTimezone', 'interceptHour12', 'wxsatTimezone',
    'intercept.default_mode', 'intercept.setup.complete.v1', 'disclaimerAccepted',
    'intercept_update_check_enabled', 'intercept_settings', 'adsb_watchlist',
    'watchMacs', 'pagerPresets', 'pagerFilters', 'ookFreqPresets', 'wfBookmarks',
    'mutedAddresses', 'tscmIgnoreList', 'biasTEnabled', 'adsbBiasTEnabled',
    'reconEnabled', 'intercept.morse.settings.v3', 'satellite.dashboard.receiver',
    'adsb.limitRange', 'adsb.retentionMs', 'adsbHistoryWindowMinutes', 'adsb.remoteReceiver',
    'airband.frequencyPresets',
})
# LAYOUT_KEYS/LAYOUT_PREFIXES in settings-manager.js are all per device.
PER_DEVICE_KEYS = (
    'mainSidebarCollapsed', 'acarsSidebarCollapsed', 'vdl2SidebarCollapsed',
    'intercept_nav_groups', 'intercept.runState.expanded', 'intercept.gps.skyView',
    'intercept.spyStations.view', 'pagerView', 'intercept.map.labels', 'sensorView',
    'meshTextOnly', 'autoScroll', 'btLocateDebug', 'btLocateHeatmapEnabled',
    'btLocateMovementEnabled', 'btLocateFollowEnabled', 'btLocateSmoothingEnabled',
    'audioMuted', 'kiwiVolume', 'adsb_detectionSound', 'intercept-voice-muted',
    # Mixed speaker/voice/source configuration stays with this audio device.
    'intercept-voice-config', 'intercept.pendingWeatherSatHandoff',
    'depsCheckDismissed', 'user_session',
    # Legacy animation settings, migrated locally to the synced UI tier.
    'intercept-animations', 'animations', 'intercept.prefs.owner',
)
PER_DEVICE_PREFIXES = ('intercept.sidebar.open.', 'intercept.reach.', 'intercept.prefs.pending.')
# reach.<adsb|ais>.<rounded lat>,<rounded lon> is a measured reception cache.
MAX_VALUE_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 512 * 1024


def user_id(username):
    with get_db() as conn:
        row = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        return row['id'] if row else None


def get_preferences(account_id):
    with get_db() as conn:
        return {row['key']: row['value'] for row in conn.execute(
            'SELECT key, value FROM user_prefs WHERE user_id = ?', (account_id,)
        ) if row['key'] in SYNCED_KEYS}


def put_preferences(account_id, changes, *, import_only=False):
    """Validate and atomically merge; imports never overwrite existing keys/tombstones."""
    if not isinstance(changes, dict) or any(key not in SYNCED_KEYS for key in changes):
        raise ValueError('Unknown preference key or invalid object')
    for value in changes.values():
        if value is not None and not isinstance(value, str):
            raise ValueError('Preference values must be strings or null')
        if value is not None and len(value.encode('utf-8')) > MAX_VALUE_BYTES:
            raise ValueError('Preference exceeds 64 KB')
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        current = {row['key']: row['value'] for row in conn.execute(
            'SELECT key, value FROM user_prefs WHERE user_id = ?', (account_id,)
        )}
        changes = {k: v for k, v in changes.items() if not import_only or k not in current}
        current.update(changes)
        if sum(len(k.encode('utf-8')) + len((v or '').encode('utf-8')) for k, v in current.items()) > MAX_TOTAL_BYTES:
            raise ValueError('Preferences exceed 512 KB per account')
        conn.executemany('''INSERT INTO user_prefs (user_id, key, value) VALUES (?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP''',
            [(account_id, k, v) for k, v in changes.items()])
