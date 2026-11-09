/* Remote ADS-B feeds come from the admin-managed shared receiver list (Settings).
 * The account preference only remembers which one this user last chose. */
(() => {
    'use strict';
    const key = 'adsb.remoteReceiver';
    const prefix = 'remote-sbs:';
    const unlistedValue = 'remote-sbs-unlisted';
    const stateText = { online: 'Online', offline: 'Offline', unknown: 'Not checked yet' };
    const refreshMs = 30000;

    document.addEventListener('DOMContentLoaded', () => {
        const select = document.getElementById('adsbDeviceSelect');
        const host = document.getElementById('remoteSbsHost');
        const port = document.getElementById('remoteSbsPort');
        const enabled = document.getElementById('useRemoteDump1090');
        const status = document.getElementById('remoteSbsSaveStatus');
        const health = document.getElementById('remoteSbsHealth');
        if (!select || !host || !port || !enabled) return;
        const bootstrap = document.getElementById('intercept-account-prefs');
        let config = null;
        try { config = bootstrap ? JSON.parse(bootstrap.textContent) : null; } catch (_) { config = null; }

        let receivers = [];
        let chosenId = null;          // id from the shared list
        let unlisted = null;          // {host, port, running} when not in the list
        let locked = false;
        const localMode = () => typeof adsbCurrentAgent === 'undefined' || adsbCurrentAgent === 'local';
        const say = text => { if (status) status.textContent = text; };
        const chosen = () => receivers.find(r => r.id === chosenId) || null;
        const sameFeed = (r, h, p) => typeof h === 'string' && r.host.toLowerCase() === h.trim().toLowerCase() && r.port === Number(p);

        function setHidden(value) {
            enabled.checked = Boolean(value);
            host.value = value ? value.host : '';
            port.value = value ? value.port : 30003;
        }

        function showHealth() {
            if (!health) return;
            const current = enabled.checked && localMode() ? chosen() : null;
            if (!current && !(enabled.checked && unlisted && localMode())) {
                health.hidden = true;
                return;
            }
            const state = current ? (current.state || 'unknown') : 'unlisted';
            health.hidden = false;
            health.dataset.state = state;
            health.textContent = current ? `● ${stateText[state] || stateText.unknown}` : '● Not in shared list';
            health.title = current
                ? `${current.name} (${current.host}:${current.port}) — port check only, not proof of data`
                : 'This feed is not in the shared receiver list. An admin can add it under Settings.';
        }

        function refresh() {
            for (const option of Array.from(select.options)) {
                if (option.value.startsWith(prefix) || option.value === unlistedValue) option.remove();
            }
            for (const input of ['adsbGainInput', 'adsbBiasT'].map(id => document.getElementById(id))) {
                if (input) input.disabled = locked || (localMode() && enabled.checked);
            }
            if (!localMode()) {
                showHealth();
                return;
            }
            for (const receiver of receivers) {
                const option = document.createElement('option');
                option.value = prefix + receiver.id;
                option.dataset.sdrType = 'remote';
                option.textContent = `Remote: ${receiver.name} — ${stateText[receiver.state] || stateText.unknown}`;
                select.appendChild(option);
            }
            if (unlisted) {
                const option = document.createElement('option');
                option.value = unlistedValue;
                option.dataset.sdrType = 'remote';
                option.disabled = !unlisted.running;
                option.textContent = `Remote SBS ${unlisted.host}:${unlisted.port} (not in shared list)`;
                select.appendChild(option);
            }
            if (enabled.checked && chosen()) select.value = prefix + chosenId;
            else if (enabled.checked && unlisted) select.value = unlistedValue;
            else if (select.value.startsWith(prefix) || select.value === unlistedValue || !select.value) {
                select.value = Array.from(select.options).find(o => o.dataset.sdrType !== 'remote')?.value || '';
            }
            showHealth();
        }

        function choose(receiver) {
            chosenId = receiver ? receiver.id : null;
            if (receiver) unlisted = null;
            setHidden(receiver);
        }

        async function remember() {
            if (!config) return;
            const current = chosen();
            const value = current
                ? { id: current.id, host: current.host, port: current.port, enabled: true }
                : { enabled: false };
            const changes = { [key]: JSON.stringify(value) };
            try {
                const response = await fetch('/api/me/prefs', {
                    method: 'PUT', credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', 'X-Intercept-Prefs': '1',
                        'X-Intercept-Prefs-Owner': config.owner },
                    body: JSON.stringify(changes)
                });
                if (!response.ok) throw new Error('Save failed');
                window.InterceptPrefs?.apply(changes);
                say('');
            } catch (_) {
                say('Could not remember your choice. Please try again.');
            }
        }

        // Apply the saved choice: new shape {id, ...}, or the old {host, port, enabled}.
        function applySaved(saved) {
            if (!saved || typeof saved !== 'object' || saved.enabled !== true) return;
            const match = receivers.find(r => r.id === saved.id) ||
                receivers.find(r => sameFeed(r, saved.host, saved.port));
            if (match) {
                choose(match);
            } else if (typeof saved.host === 'string' && saved.host) {
                // Never quietly fall back to a local SDR the user did not choose.
                chosenId = null;
                unlisted = { host: saved.host, port: Number(saved.port) || 30003, running: false };
                setHidden(unlisted);
            }
        }

        let savedChoice = null;
        try { savedChoice = JSON.parse((config && config.prefs[key]) || 'null'); } catch (_) { savedChoice = null; }

        async function load(first) {
            try {
                const response = await fetch('/settings/remote-receivers?type=adsb_sbs', { credentials: 'same-origin' });
                if (!response.ok) throw new Error('unavailable');
                const data = await response.json();
                receivers = Array.isArray(data.entries) ? data.entries : [];
            } catch (_) {
                if (first) receivers = [];
            }
            // A running session may have been restored before the list arrived.
            if (unlisted) {
                const match = receivers.find(r => sameFeed(r, unlisted.host, unlisted.port));
                if (match) choose(match);
            }
            if (first) {
                if (!locked && !enabled.checked) applySaved(savedChoice);
                window.toggleRemoteDump1090?.();
                window.updateSourceIndicator?.();
            } else if (chosenId && !chosen() && !locked) {
                // The admin removed it; stop pointing at it.
                const gone = { host: host.value, port: Number(port.value) };
                chosenId = null;
                unlisted = { ...gone, running: false };
            }
            refresh();
        }

        window.AdsbRemoteReceiver = {
            refresh,
            getConfig() {
                if (!enabled.checked) return null;
                const current = chosen();
                if (!current) {
                    say('That remote feed is not in the shared receiver list. Choose another receiver, or ask an admin to add it in Settings.');
                    return false;
                }
                return { host: current.host, port: current.port };
            },
            getLabel() {
                if (!localMode() || !enabled.checked) return null;
                const current = chosen();
                if (current) return `Remote: ${current.name} (${current.host}:${current.port})`;
                return unlisted ? `Remote SBS: ${unlisted.host}:${unlisted.port}` : null;
            },
            restoreSession(session) {
                if (session.sdr_type !== 'remote') {
                    choose(null);
                    unlisted = null;
                } else {
                    const match = receivers.find(r => sameFeed(r, session.remote_host, session.remote_port || 30003));
                    if (match) choose(match);
                    else {
                        chosenId = null;
                        unlisted = { host: session.remote_host || '', port: session.remote_port || 30003, running: true };
                        setHidden(unlisted);
                    }
                }
                window.toggleRemoteDump1090?.();
            },
            setTracking(value) {
                locked = value;
                if (!value && unlisted && unlisted.running) unlisted.running = false;
                for (const input of [select, document.getElementById('agentSelect')]) {
                    if (input) input.disabled = locked;
                }
            }
        };

        select.addEventListener('change', () => {
            if (!localMode() || locked) {
                refresh();
                return;
            }
            const value = select.value;
            const before = chosenId;
            if (value.startsWith(prefix)) {
                choose(receivers.find(r => r.id === value.slice(prefix.length)) || null);
            } else if (value !== unlistedValue) {
                choose(null);
                unlisted = null;
            }
            say('');
            refresh();
            window.updateSourceIndicator?.();
            if (before !== chosenId) remember();
        });

        load(true);
        setInterval(() => load(false), refreshMs);
    });
})();
