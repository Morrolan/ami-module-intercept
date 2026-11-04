/* Explicit, account-scoped persistence for the remote ADS-B receiver. */
(() => {
    'use strict';
    const key = 'adsb.remoteReceiver';
    function valid(value) {
        return value && typeof value.host === 'string' &&
            /^[a-zA-Z0-9._:\-]+$/.test(value.host) && value.host.length <= 253 &&
            Number.isInteger(value.port) && value.port >= 1 && value.port <= 65535 &&
            typeof value.enabled === 'boolean';
    }
    document.addEventListener('DOMContentLoaded', () => {
        const button = document.getElementById('saveRemoteSbs');
        if (!button) return;
        const bootstrap = document.getElementById('intercept-account-prefs');
        if (!bootstrap) {
            button.hidden = true;
            return;
        }
        const host = document.getElementById('remoteSbsHost');
        const port = document.getElementById('remoteSbsPort');
        const enabled = document.getElementById('useRemoteDump1090');
        const status = document.getElementById('remoteSbsSaveStatus');
        const config = JSON.parse(bootstrap.textContent);
        const select = document.getElementById('adsbDeviceSelect');
        const remoteValue = 'remote-sbs';
        let locked = false, saving = false;
        const localMode = () => typeof adsbCurrentAgent === 'undefined' || adsbCurrentAgent === 'local';
        const formValue = () => ({ host: host.value.trim(), port: Number(port.value), enabled: enabled.checked });
        function refresh() {
            if (!select) return;
            let option = Array.from(select.options).find(o => o.value === remoteValue);
            const value = formValue();
            if (!localMode() || !valid(value)) {
                option?.remove();
                return;
            }
            if (!option) {
                option = document.createElement('option');
                option.value = remoteValue;
                option.dataset.sdrType = 'remote';
                select.appendChild(option);
            }
            option.textContent = `Remote SBS: ${value.host}:${value.port}`;
            if (enabled.checked) select.value = remoteValue;
            else if (select.value === remoteValue) {
                select.value = Array.from(select.options).find(o => o.value !== remoteValue)?.value || '';
            }
            for (const id of ['adsbGainInput', 'adsbBiasT']) {
                const input = document.getElementById(id);
                if (input) input.disabled = locked || enabled.checked;
            }
        }
        window.AdsbRemoteReceiver = {
            refresh,
            getConfig() {
                if (!enabled.checked) return null;
                const value = formValue();
                if (!valid(value)) {
                    status.textContent = 'Enter a valid remote host and port before starting.';
                    return false;
                }
                return { host: value.host, port: value.port };
            },
            getLabel() {
                const value = formValue();
                return localMode() && enabled.checked && valid(value)
                    ? `Remote SBS: ${value.host}:${value.port}` : null;
            },
            restoreSession(session) {
                enabled.checked = session.sdr_type === 'remote';
                if (enabled.checked) {
                    host.value = session.remote_host || '';
                    port.value = session.remote_port || 30003;
                }
                window.toggleRemoteDump1090();
            },
            setTracking(value) {
                locked = value;
                for (const input of [host, port, enabled]) input.disabled = locked;
                button.disabled = locked || saving;
            }
        };
        select?.addEventListener('change', () => {
            if (!localMode()) return;
            enabled.checked = select.value === remoteValue;
            window.toggleRemoteDump1090();
        });
        try {
            const saved = JSON.parse(config.prefs[key] || 'null');
            if (valid(saved)) {
                host.value = saved.host;
                port.value = saved.port;
                enabled.checked = saved.enabled;
                window.toggleRemoteDump1090();
            }
        } catch (_) { /* Ignore a malformed saved value without breaking tracking. */ }
        for (const input of [host, port, enabled]) {
            const changed = () => {
                status.textContent = '';
                refresh();
                window.updateSourceIndicator?.();
            };
            input.addEventListener('input', changed);
            input.addEventListener('change', changed);
        }
        refresh();
        button.addEventListener('click', async () => {
            const value = { host: host.value.trim(), port: Number(port.value), enabled: enabled.checked };
            if (!valid(value)) {
                status.textContent = 'Enter a valid host and port (1–65535).';
                return;
            }
            saving = true;
            button.disabled = true;
            status.textContent = 'Saving…';
            try {
                const changes = { [key]: JSON.stringify(value) };
                const response = await fetch('/api/me/prefs', {
                    method: 'PUT', credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', 'X-Intercept-Prefs': '1',
                        'X-Intercept-Prefs-Owner': config.owner },
                    body: JSON.stringify(changes)
                });
                if (!response.ok) throw new Error('Save failed');
                window.InterceptPrefs?.apply(changes);
                refresh();
                status.textContent = 'Saved to your account.';
            } catch (_) {
                status.textContent = 'Could not save. Please try again.';
            } finally {
                saving = false;
                button.disabled = locked;
            }
        });
    });
})();
