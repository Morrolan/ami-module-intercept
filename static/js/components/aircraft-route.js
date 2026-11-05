/* On-demand, transient enrichment. A callsign route is not a current flight plan. */
(() => {
    'use strict';
    const entries = new Map();
    const normal = value => String(value || '').trim().toUpperCase();
    function show(icao, callsign, registration) {
        const key = normal(callsign);
        function paint(data) {
            if (selectedIcao !== icao || normal(aircraft[icao]?.callsign) !== key) return;
            for (const [id, airport] of [['selectedOrigin', data.origin], ['selectedDestination', data.destination]]) {
                const target = document.getElementById(id);
                if (target) target.textContent = airport ? `${airport.iata || airport.icao} · ${airport.name}` : 'Unknown';
            }
            const source = document.getElementById('selectedRouteSource');
            if (source) source.textContent = data.available ? 'Callsign route · adsbdb · may differ from this flight' : data.message;
        }
        if (window.TeessideAirport?.isDraken(registration)) {
            paint({message: 'No verified route for this Draken aircraft.'});
            return;
        }
        if (!/^[A-Z]{2,3}\d[A-Z0-9]{0,5}$/.test(key) || key.length > 8) {
            paint({message: 'Route unavailable — no airline callsign.'});
            return;
        }
        if (selectedIcao !== icao) return;
        let entry = entries.get(key);
        if (!entry || entry.expires <= Date.now()) {
            entry = {expires: Infinity, data: null};
            entry.promise = fetchJsonWithTimeout('/adsb/route/' + encodeURIComponent(key), {}, 10000)
                .then(response => { if (!response.ok) throw new Error('Lookup failed'); return response.json(); })
                .catch(() => ({available: false, message: 'Route lookup temporarily unavailable.'}))
                .then(data => {
                    entry.data = data;
                    entry.expires = Date.now() + (data.available ? 900000 : 60000);
                    return data;
                });
            entries.delete(key);
            entries.set(key, entry);
            while (entries.size > 512) entries.delete(entries.keys().next().value);
        }
        if (entry.data) paint(entry.data);
        else {
            const source = document.getElementById('selectedRouteSource');
            if (source) source.textContent = 'Looking up callsign route…';
            entry.promise.then(paint);
        }
    }
    window.AircraftRoute = Object.freeze({show});
})();
