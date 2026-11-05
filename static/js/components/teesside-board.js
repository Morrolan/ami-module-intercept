/* Official passenger board and independently received aircraft, never inferred schedules. */
(() => {
    'use strict';
    // Exact public operator registrations, checked 2026-11-05 against the linked fleet reference.
    // This is a recognition list, not a live fleet database or an airport-residency claim.
    const registrations = new Set([
        'G-BJEC','G-BJED','G-BJOH','G-BJYT','G-BLNT','G-BLNU','G-BLNY','G-BRPC','G-BSAH',
        'G-DRAK','G-DOSB','G-FFMV','G-FFRA','G-FRAD','G-FRAF','G-FRAH','G-FRAI','G-FRAJ',
        'G-FRAK','G-FRAL','G-FRAP','G-FRAR','G-FRAS','G-FRAT','G-FRAU','G-FRAW',
        'G-DKNA','G-DKNB','G-DKNC','G-DKND','G-DKNE','G-DKNF','G-DKNG','G-DKNH',
        'G-DKNK','G-DKNN','G-DKNO','G-DKNR','G-DKNT',
    ].map(value => value.replaceAll('-', '')));
    const isDraken = value => registrations.has(String(value || '').toUpperCase().replace(/[\s-]/g, ''));
    let dialog, data = null, mode = 'arrivals', pending = false, timers = [];
    const el = id => document.getElementById(id);
    const node = (tag, text, className) => {
        const value = document.createElement(tag);
        value.textContent = text;
        if (className) value.className = className;
        return value;
    };
    const time = value => new Date(value).toLocaleTimeString('en-GB', {timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit'});

    function flightCard(row, direction, countdown) {
        const card = node('li', '', 'teesside-flight');
        card.append(node('strong', row.flight), node('span', `Scheduled ${row.scheduled}`),
            node('span', `${direction === 'arrivals' ? 'From' : 'To'} ${row.place}`), node('span', row.status));
        if (countdown) card.append(node('span', `${row.date} · ${countdown}`, 'teesside-note'));
        if (row.remarks && row.remarks !== '-') card.append(node('span', row.remarks, 'teesside-note'));
        return card;
    }

    function nextMovements() {
        const target = el('teessideNext');
        target.replaceChildren();
        if (!data?.available) { target.append(node('li', 'Airport schedule unavailable.')); return; }
        if (data.stale) { target.append(node('li', 'Airport data is stale; check the official board before relying on these times.')); return; }
        const rows = ['arrivals', 'departures'].flatMap(direction => data[direction].map(row => ({...row, direction})))
            .map(row => ({...row, movementTime: Date.parse(row.expected_at || row.scheduled_at)}))
            .filter(row => Number.isFinite(row.movementTime) && row.movementTime >= Date.now() - 30 * 60000
                && !/landed|departed|cancel/i.test(row.status))
            .sort((a, b) => a.movementTime - b.movementTime).slice(0, 3);
        for (const row of rows) {
            const minutes = Math.ceil((row.movementTime - Date.now()) / 60000);
            const remaining = minutes < 0 ? 'Scheduled time passed — check status' : minutes === 0 ? 'Due now' :
                minutes < 60 ? `In ${minutes} min` : `In ${Math.floor(minutes / 60)} hr ${minutes % 60} min`;
            target.append(flightCard(row, row.direction, `${row.direction === 'arrivals' ? 'Arrival' : 'Departure'} · ${row.expected_at ? 'Expected ' + remaining.toLowerCase() : remaining}`));
        }
        if (!rows.length) target.append(node('li', 'No upcoming published movements in the available board.'));
    }

    function receivedDraken() {
        const target = el('teessideFlights');
        target.replaceChildren();
        const tracks = typeof aircraft === 'undefined' ? [] : Object.values(aircraft);
        const rows = tracks.filter(ac => isDraken(ac.registration) && Number.isFinite(ac.lastSeen)
            && Date.now() - ac.lastSeen <= aircraftRetentionMs).sort((a, b) => b.lastSeen - a.lastSeen);
        for (const ac of rows) {
            const card = node('li', '', 'teesside-flight');
            card.append(node('strong', ac.registration), node('span', ac.callsign || ac.icao),
                node('span', ac.on_ground ? 'Reported on ground' : ac.altitude != null ? `${Number(ac.altitude).toLocaleString()} ft` : 'Altitude unknown'),
                node('span', `Last heard ${time(ac.lastSeen)}`));
            target.append(card);
        }
        if (!rows.length) target.append(node('li', 'No matching Draken aircraft in the received tracks. Aircraft without a known registration cannot be matched.'));
    }

    function render() {
        nextMovements();
        const observed = mode === 'draken';
        el('teessideAirportControls').hidden = observed;
        el('teessideDrakenNote').hidden = !observed;
        el('teessideFreshness').hidden = observed;
        dialog.querySelectorAll('[data-board]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.board === mode)));
        if (observed) { receivedDraken(); return; }
        const target = el('teessideFlights');
        target.replaceChildren();
        const status = el('teessideFreshness');
        status.textContent = !data ? 'Checking airport board…' : !data.available ? 'Airport board unavailable.' :
            `${data.stale ? 'Stale airport data — last checked' : 'Official board checked'} ${time(data.fetched_at)}.`;
        if (!data) return;
        if (!data.available) { target.append(node('li', data.error || 'Airport board unavailable.')); return; }
        const rows = data[mode].filter(row => row.date === el('teessideDate').value)
            .sort((a, b) => a.scheduled.localeCompare(b.scheduled));
        for (const row of rows) target.append(flightCard(row, mode));
        if (!rows.length) target.append(node('li', 'No published flights for this date in the available board.'));
        if (data.error) status.textContent += ' ' + data.error;
    }

    async function load() {
        if (pending) return;
        pending = true;
        el('teessideRefresh').disabled = true;
        try {
            const response = await fetchJsonWithTimeout('/adsb/teesside', {}, 12000);
            if (!response.ok) throw new Error('Unavailable');
            const incoming = await response.json();
            if (!Array.isArray(incoming.arrivals) || !Array.isArray(incoming.departures)) throw new Error('Invalid board');
            data = incoming;
            const select = el('teessideDate'), selected = select.value;
            const dates = [...new Set([...data.arrivals, ...data.departures].map(row => row.date))].sort();
            select.replaceChildren(...dates.map(date => {
                const option = node('option', date);
                option.value = date;
                return option;
            }));
            const today = new Intl.DateTimeFormat('en-CA', {timeZone: 'Europe/London', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date(Date.now()));
            select.value = dates.includes(selected) ? selected : dates.includes(today) ? today : dates[0] || '';
        } catch {
            data = {...(data || {available: false, arrivals: [], departures: []}), stale: true,
                error: 'Airport board unavailable. Please try again later.'};
        } finally {
            pending = false;
            el('teessideRefresh').disabled = false;
            render();
        }
    }

    async function listen(kind) {
        if (typeof adsbCurrentAgent !== 'undefined' && adsbCurrentAgent !== 'local') {
            el('teessideRadioStatus').textContent = 'Select a receiver on this server in Airband to listen.';
            return;
        }
        const frequency = {tower: 119.8, approach: 118.85}[kind];
        if (!frequency) return;
        if (isAirbandPlaying) {
            await stopAirband();
            if (isAirbandPlaying) { el('teessideRadioStatus').textContent = 'Could not stop the current audio receiver.'; return; }
        }
        el('airbandFreqSelect').value = 'custom';
        el('airbandCustomFreq').value = frequency;
        updateAirbandFreq();
        updateAirbandChip();
        dialog.close();
        if (el('airbandPanel').hidden) toggleAirbandPanel();
        await window.startAirband();
    }

    window.TeessideAirport = Object.freeze({isDraken});
    document.addEventListener('DOMContentLoaded', () => {
        dialog = el('teessideDialog');
        el('teessideBoardBtn').addEventListener('click', () => {
            dialog.showModal();
            render();
            load();
            timers = [VisibleInterval.set(render, 10000), VisibleInterval.set(load, 300000)];
        });
        const close = () => { timers.forEach(VisibleInterval.clear); timers = []; };
        dialog.addEventListener('close', close);
        window.addEventListener('pagehide', close);
        el('teessideClose').addEventListener('click', () => dialog.close());
        el('teessideDate').addEventListener('change', render);
        el('teessideRefresh').addEventListener('click', load);
        dialog.querySelectorAll('[data-board]').forEach(button => button.addEventListener('click', () => { mode = button.dataset.board; render(); }));
        dialog.querySelectorAll('[data-radio]').forEach(button => button.addEventListener('click', () => listen(button.dataset.radio)));
        dialog.addEventListener('click', event => {
            const box = dialog.getBoundingClientRect();
            if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
        });
    });
})();
