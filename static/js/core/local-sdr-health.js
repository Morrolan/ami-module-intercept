/* Live health of the watched local RTL-SDR in device menus.
 * /devices marks that one device with `health` (only when the host watcher is set up);
 * menus pass each option here, and its text is kept current every 30 seconds. */
(() => {
    'use strict';
    const text = { online: 'Online', missing: 'Unplugged', not_reporting: 'Not reporting' };
    const tracked = new Set();
    let timer = null;

    const HEALTH = / — (Online|Unplugged|Not reporting)/;
    function apply(option, state) {
        // Keep a menu's own trailing tag (e.g. "[ADSB]" while in use) after the health text.
        const current = option.textContent.replace(HEALTH, '');
        const tag = (current.match(/ \[[^\]]*\]$/) || [''])[0];
        const base = tag ? current.slice(0, -tag.length) : current;
        option.dataset.health = state;
        option.textContent = `${base}${text[state] ? ' — ' + text[state] : ''}${tag}`;
    }

    async function poll() {
        for (const option of [...tracked]) if (!option.isConnected) tracked.delete(option);
        if (!tracked.size) {
            timer = null;
            return;
        }
        try {
            const response = await fetch('/devices/local-health', { credentials: 'same-origin' });
            if (response.ok) {
                const data = await response.json();
                if (data.enabled) for (const option of tracked) apply(option, data.state);
            }
        } catch (_) { /* Keep the last known text; the next poll may succeed. */ }
        timer = setTimeout(poll, 30000);
    }

    window.LocalSdrHealth = {
        /** Label one <option> for a /devices entry; a no-op for every other device. */
        label(option, device) {
            if (!option || !device || !text[device.health]) return option;
            apply(option, device.health);
            tracked.add(option);
            if (!timer) timer = setTimeout(poll, 30000);
            return option;
        },
        /** Label options already in a select, matching /devices entries by `match(option, device)`. */
        labelAll(select, devices, match) {
            if (!select || !Array.isArray(devices)) return;
            for (const device of devices) {
                if (!device || !device.health) continue;
                for (const option of select.options) if (match(option, device)) this.label(option, device);
            }
        }
    };
})();
