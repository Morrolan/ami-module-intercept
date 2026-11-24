/* Airport details for a selected aircraft's route: bundled reference data, never flight status. */
(() => {
    'use strict';
    const SIZES = {large: 'Large airport', medium: 'Medium airport', small: 'Small airport',
        heliport: 'Heliport', seaplane: 'Seaplane base'};
    const cache = new Map();
    let dialog, current = '';
    const el = id => document.getElementById(id);
    const node = (tag, text, className) => {
        const value = document.createElement(tag);
        value.textContent = text;
        if (className) value.className = className;
        return value;
    };
    const count = value => Math.round(value).toLocaleString('en-GB');
    const metres = feet => count(feet * 0.3048);
    const finite = value => value !== null && value !== '' && Number.isFinite(Number(value));

    function lookup(icao) {
        if (!cache.has(icao)) {
            cache.set(icao, fetchJsonWithTimeout('/adsb/airport/' + encodeURIComponent(icao), {}, 8000)
                .then(response => response.status === 404 ? null : response.ok ? response.json() : Promise.reject(new Error('Lookup failed')))
                .catch(error => { cache.delete(icao); throw error; }));
        }
        return cache.get(icao);
    }

    function fromObserver(lat, lon) {
        const here = typeof observerLocation === 'undefined' ? null : observerLocation;
        if (!here || ![here.lat, here.lon, lat, lon].every(finite)) return '';
        const rad = Math.PI / 180, p1 = here.lat * rad, p2 = lat * rad, dl = (lon - here.lon) * rad;
        const a = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
        const nm = 3440.065 * 2 * Math.asin(Math.sqrt(a));
        const bearing = (Math.atan2(Math.sin(dl) * Math.cos(p2),
            Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl)) / rad + 360) % 360;
        const point = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round(bearing / 45) % 8];
        return `${count(nm)} nm (${count(nm * 1.852)} km) · ${point} (${Math.round(bearing)}°)`;
    }

    function link(text, href) {
        if (!/^https?:\/\//.test(href || '')) return null;
        const anchor = node('a', text);
        anchor.href = href;
        anchor.target = '_blank';
        anchor.rel = 'noopener';
        return anchor;
    }

    async function listen(frequency) {
        const status = el('airportInfoRadioStatus');
        if (typeof adsbCurrentAgent !== 'undefined' && adsbCurrentAgent !== 'local') {
            status.textContent = 'Select a receiver on this server in Airband to listen.';
            return;
        }
        if (!(frequency > 0)) return;
        if (isAirbandPlaying) {
            await stopAirband();
            if (isAirbandPlaying) { status.textContent = 'Could not stop the current audio receiver.'; return; }
        }
        el('airbandFreqSelect').value = 'custom';
        el('airbandCustomFreq').value = frequency;
        updateAirbandFreq();
        updateAirbandChip();
        dialog.close();
        if (el('airbandPanel').hidden) toggleAirbandPanel();
        await window.startAirband();
    }

    function render(route, details, status) {
        // Bundled details first; the route lookup's own fields fill any gaps.
        const airport = {...route};
        for (const [key, value] of Object.entries(details || {})) {
            if (value !== null && value !== '') airport[key] = value;
        }
        el('airportInfoTitle').textContent = airport.name || airport.icao;
        el('airportInfoCodes').textContent = [airport.role, airport.iata && `IATA ${airport.iata}`, `ICAO ${airport.icao}`]
            .filter(Boolean).join(' · ');
        el('airportInfoStatus').textContent = status;
        el('airportInfoStatus').hidden = !status;

        const facts = [
            ['Size', SIZES[airport.type] || ''],
            ['Scheduled flights', details ? (airport.scheduled ? 'Yes' : 'No') : ''],
            ['Town or city', airport.municipality],
            ['Region', airport.region],
            ['Country', airport.country ? `${airport.country}${airport.country_code ? ` (${airport.country_code})` : ''}` : airport.country_code],
            ['Elevation', finite(airport.elevation_ft) ? `${count(airport.elevation_ft)} ft (${metres(airport.elevation_ft)} m)` : ''],
            ['Position', finite(airport.lat) && finite(airport.lon) ? `${Number(airport.lat).toFixed(4)}°, ${Number(airport.lon).toFixed(4)}°` : ''],
            ['From your location', fromObserver(Number(airport.lat), Number(airport.lon))],
        ].filter(([, value]) => value);
        el('airportInfoFacts').replaceChildren(...facts.flatMap(([term, value]) => [node('dt', term), node('dd', value)]));

        const runways = details?.runways || [];
        el('airportInfoRunwaysSection').hidden = !runways.length;
        el('airportInfoRunways').replaceChildren(...runways.map(runway => node('li', [
            runway.ident || 'Runway',
            finite(runway.length_ft) && `${count(runway.length_ft)} ft (${metres(runway.length_ft)} m)${finite(runway.width_ft) ? ` × ${count(runway.width_ft)} ft` : ''}`,
            runway.surface,
            runway.lighted ? 'lit' : '',
        ].filter(Boolean).join(' · '))));

        const frequencies = details?.frequencies || [];
        el('airportInfoFreqSection').hidden = !frequencies.length;
        el('airportInfoRadioStatus').textContent = '';
        el('airportInfoFreqs').replaceChildren(...frequencies.map(frequency => {
            const mhz = Number(frequency.mhz);
            const row = node('li', '');
            const label = `${frequency.type} · ${mhz.toFixed(3)} MHz`;
            row.append(node('span', frequency.desc && frequency.desc !== frequency.type ? `${label} · ${frequency.desc}` : label));
            const button = node('button', 'Listen', 'strip-btn');
            button.type = 'button';
            button.setAttribute('aria-label', `Listen to ${label}`);
            button.addEventListener('click', () => listen(mhz));
            row.append(button);
            return row;
        }));

        const links = [link('Wikipedia', airport.wikipedia), link('Airport website', airport.home),
            details ? link('OurAirports page', `https://ourairports.com/airports/${encodeURIComponent(airport.icao)}/`) : null]
            .filter(Boolean);
        el('airportInfoLinks').replaceChildren(...links.flatMap((anchor, index) => index ? [' · ', anchor] : [anchor]));
    }

    function show(route, role) {
        if (!dialog || !route?.icao) return;
        const icao = route.icao;
        current = icao;
        const base = {...route, role};
        render(base, null, 'Loading airport details…');
        if (!dialog.open) dialog.showModal();
        lookup(icao)
            .then(details => {
                if (current !== icao) return;
                render(base, details, details ? '' : 'Not in Intercept’s bundled airport reference; showing the route lookup’s details only.');
            })
            .catch(() => {
                if (current === icao) render(base, null, 'Airport details unavailable; showing the route lookup’s details only.');
            });
    }

    window.AirportInfo = Object.freeze({show});
    document.addEventListener('DOMContentLoaded', () => {
        dialog = el('airportInfoDialog');
        if (!dialog) return;
        dialog.addEventListener('close', () => { current = ''; });
        el('airportInfoClose').addEventListener('click', () => dialog.close());
        dialog.addEventListener('click', event => {
            const box = dialog.getBoundingClientRect();
            if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
        });
    });
})();
