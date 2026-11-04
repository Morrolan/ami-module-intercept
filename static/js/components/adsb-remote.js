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
            input.addEventListener('input', () => { status.textContent = ''; });
            input.addEventListener('change', () => { status.textContent = ''; });
        }
        button.addEventListener('click', async () => {
            const value = { host: host.value.trim(), port: Number(port.value), enabled: enabled.checked };
            if (!valid(value)) {
                status.textContent = 'Enter a valid host and port (1–65535).';
                return;
            }
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
                status.textContent = 'Saved to your account.';
            } catch (_) {
                status.textContent = 'Could not save. Please try again.';
            } finally {
                button.disabled = false;
            }
        });
    });
})();
