const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/components/adsb-remote.js', 'utf8');
const key = 'adsb.remoteReceiver';
function browser(server = {}) {
    const elements = {}, events = {}, calls = [];
    for (const id of ['saveRemoteSbs', 'remoteSbsHost', 'remoteSbsPort', 'useRemoteDump1090', 'remoteSbsSaveStatus']) {
        elements[id] = { value: id === 'remoteSbsPort' ? '30003' : '', checked: false,
            textContent: '', listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; } };
    }
    elements['intercept-account-prefs'] = { textContent: JSON.stringify({ owner: '7', prefs: server }) };
    let fail = false;
    const context = vm.createContext({
        document: { getElementById: id => elements[id], addEventListener: (name, fn) => { events[name] = fn; } },
        fetch: async (url, options) => {
            calls.push({ url, options });
            if (fail) return { ok: false };
            Object.assign(server, JSON.parse(options.body));
            return { ok: true };
        },
        toggleRemoteDump1090: () => {}, InterceptPrefs: { apply: () => {} }
    });
    context.window = context;
    vm.runInContext(source, context);
    events.DOMContentLoaded();
    return { elements, calls, save: () => elements.saveRemoteSbs.listeners.click(), offline() { fail = true; } };
}
(async () => {
    const server = {}, first = browser(server), e = first.elements;
    e.remoteSbsHost.value = ' 10.10.42.10 ';
    e.useRemoteDump1090.checked = true;
    await first.save();
    assert.deepEqual(JSON.parse(server[key]), { host: '10.10.42.10', port: 30003, enabled: true });
    assert.equal(first.calls[0].options.headers['X-Intercept-Prefs-Owner'], '7');
    assert.match(e.remoteSbsSaveStatus.textContent, /Saved to your account/);
    const fresh = browser(server);
    assert.equal(fresh.elements.remoteSbsHost.value, '10.10.42.10');
    assert.equal(fresh.elements.useRemoteDump1090.checked, true);
    fresh.elements.useRemoteDump1090.checked = false;
    await fresh.save();
    assert.equal(browser(server).elements.useRemoteDump1090.checked, false);
    const invalid = browser();
    invalid.elements.remoteSbsHost.value = '10.10.42.10';
    invalid.elements.remoteSbsPort.value = '70000';
    await invalid.save();
    assert.equal(invalid.calls.length, 0);
    first.offline();
    e.remoteSbsHost.value = 'different.local';
    await first.save();
    assert.match(e.remoteSbsSaveStatus.textContent, /Could not save/);
    assert.equal(JSON.parse(server[key]).host, '10.10.42.10');
    assert.equal(e.saveRemoteSbs.disabled, false);
    assert.equal(browser({ [key]: '{broken' }).elements.remoteSbsHost.value, '');
    console.log('Remote ADS-B save, fresh-page restore, disabled selection, validation and failure checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
