const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/components/adsb-remote.js', 'utf8');
const key = 'adsb.remoteReceiver';
const roof = { id: 'a'.repeat(32), name: 'Roof Pi', host: '10.10.42.6', port: 30003, type: 'adsb_sbs', state: 'online', last_seen: null };
const shed = { id: 'b'.repeat(32), name: 'Shed', host: 'shed.local', port: 30003, type: 'adsb_sbs', state: 'offline', last_seen: null };
const plain = value => JSON.parse(JSON.stringify(value));
const tick = () => new Promise(resolve => setImmediate(resolve));

function element(extra = {}) {
    return { value: '', checked: false, hidden: false, disabled: false, textContent: '', title: '',
        dataset: {}, listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; }, ...extra };
}
function selectElement() {
    const select = element({ options: [] });
    select.appendChild = option => { option.remove = () => { select.options = select.options.filter(o => o !== option); }; select.options.push(option); };
    Object.defineProperty(select, 'value', {
        get() { return this._value ?? ''; },
        set(v) { this._value = this.options.some(o => o.value === v) ? v : ''; }
    });
    select.appendChild(element({ value: 'rtlsdr:0', dataset: { sdrType: 'rtlsdr' } }));
    select.value = 'rtlsdr:0';
    return select;
}

async function browser({ prefs = {}, account = true, receivers = [roof, shed], listOk = true } = {}) {
    const elements = { adsbDeviceSelect: selectElement() };
    for (const id of ['remoteSbsHost', 'remoteSbsPort', 'useRemoteDump1090', 'remoteSbsSaveStatus', 'remoteSbsHealth']) {
        elements[id] = element();
    }
    elements.remoteSbsPort.value = '30003';
    if (account) elements['intercept-account-prefs'] = { textContent: JSON.stringify({ owner: '7', prefs }) };
    const events = {}, saves = [];
    let failSave = false;
    const context = vm.createContext({
        document: {
            getElementById: id => elements[id],
            addEventListener: (name, fn) => { events[name] = fn; },
            createElement: () => element()
        },
        fetch: async (url, options = {}) => {
            if (url.startsWith('/settings/remote-receivers')) {
                assert.equal(url, '/settings/remote-receivers?type=adsb_sbs');
                return listOk ? { ok: true, json: async () => ({ entries: receivers }) } : { ok: false };
            }
            saves.push(JSON.parse(options.body));
            if (failSave) return { ok: false };
            Object.assign(prefs, JSON.parse(options.body));
            return { ok: true };
        },
        setInterval: () => 0,
        toggleRemoteDump1090: () => {}, InterceptPrefs: { apply: () => {} }
    });
    context.window = context;
    vm.runInContext(source, context);
    events.DOMContentLoaded();
    await tick();
    const select = elements.adsbDeviceSelect;
    return {
        e: elements, select, saves, prefs, api: context.AdsbRemoteReceiver,
        values: () => select.options.map(o => o.value),
        async pick(value) { select.value = value; select.listeners.change(); await tick(); },
        offline() { failSave = true; }
    };
}

(async () => {
    // The device menu lists shared ADS-B feeds with their health in the text.
    const page = await browser();
    assert.deepEqual(page.values(), ['rtlsdr:0', 'remote-sbs:' + roof.id, 'remote-sbs:' + shed.id]);
    assert.match(page.select.options[1].textContent, /Roof Pi — Online/);
    assert.match(page.select.options[2].textContent, /Shed — Offline/);
    assert.equal(page.select.value, 'rtlsdr:0');
    assert.equal(page.api.getConfig(), null);
    assert.equal(page.e.remoteSbsHealth.hidden, true);

    // Choosing one remembers it in the account and starts from the listed host and port.
    await page.pick('remote-sbs:' + roof.id);
    assert.deepEqual(plain(page.api.getConfig()), { host: '10.10.42.6', port: 30003 });
    assert.equal(page.e.remoteSbsHealth.hidden, false);
    assert.equal(page.e.remoteSbsHealth.dataset.state, 'online');
    assert.match(page.e.remoteSbsHealth.textContent, /Online/);
    assert.deepEqual(JSON.parse(page.prefs[key]), { id: roof.id, host: '10.10.42.6', port: 30003, enabled: true });
    assert.match(page.api.getLabel(), /Roof Pi/);

    // A fresh page restores the choice; switching back to local is remembered too.
    const fresh = await browser({ prefs: page.prefs });
    assert.equal(fresh.select.value, 'remote-sbs:' + roof.id);
    await fresh.pick('rtlsdr:0');
    assert.equal(fresh.api.getConfig(), null);
    assert.deepEqual(JSON.parse(fresh.prefs[key]), { enabled: false });
    assert.equal((await browser({ prefs: fresh.prefs })).select.value, 'rtlsdr:0');

    // The old {host, port, enabled} preference maps onto the matching shared entry.
    const legacy = await browser({ prefs: { [key]: JSON.stringify({ host: 'SHED.local', port: 30003, enabled: true }) } });
    assert.equal(legacy.select.value, 'remote-sbs:' + shed.id);

    // A saved feed missing from the list is shown as unavailable, never swapped for a local SDR.
    const missing = await browser({ prefs: { [key]: JSON.stringify({ host: 'gone.local', port: 30003, enabled: true }) } });
    assert.equal(missing.select.value, 'remote-sbs-unlisted');
    assert.equal(missing.select.options.at(-1).disabled, true);
    assert.equal(missing.api.getConfig(), false);
    assert.match(missing.e.remoteSbsSaveStatus.textContent, /not in the shared receiver list/);
    assert.equal(missing.e.remoteSbsHealth.dataset.state, 'unlisted');

    // A running session on a listed feed selects it; an unlisted running feed is still shown.
    const running = await browser();
    running.api.restoreSession({ sdr_type: 'remote', remote_host: 'shed.local', remote_port: 30003 });
    running.api.refresh();
    assert.equal(running.select.value, 'remote-sbs:' + shed.id);
    running.api.restoreSession({ sdr_type: 'remote', remote_host: 'old.local', remote_port: 30003 });
    running.api.refresh();
    assert.equal(running.select.value, 'remote-sbs-unlisted');
    assert.match(running.api.getLabel(), /old\.local:30003/);

    // Locked while tracking.
    running.api.setTracking(true);
    assert.equal(running.select.disabled, true);

    // Save failures are reported; no account means nothing is saved but the menu still works.
    const failing = await browser();
    failing.offline();
    await failing.pick('remote-sbs:' + roof.id);
    assert.match(failing.e.remoteSbsSaveStatus.textContent, /Could not remember/);
    const anonymous = await browser({ account: false });
    await anonymous.pick('remote-sbs:' + shed.id);
    assert.deepEqual(plain(anonymous.api.getConfig()), { host: 'shed.local', port: 30003 });
    assert.equal(anonymous.saves.length, 0);

    // The list being unavailable leaves only local devices, without errors.
    const down = await browser({ listOk: false });
    assert.deepEqual(down.values(), ['rtlsdr:0']);
    assert.equal((await browser({ prefs: { [key]: '{broken' } })).select.value, 'rtlsdr:0');
    console.log('Shared remote ADS-B feed picker: listing, health, choice memory, legacy and unlisted feeds, sessions passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
