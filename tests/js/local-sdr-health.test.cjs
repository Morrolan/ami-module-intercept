const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/core/local-sdr-health.js', 'utf8');

const timers = [];
let state = 'online', ok = true;
const context = vm.createContext({
    fetch: async url => {
        assert.equal(url, '/devices/local-health');
        return ok ? { ok: true, json: async () => ({ enabled: true, state }) } : { ok: false };
    },
    setTimeout: fn => { timers.push(fn); return timers.length; }
});
context.window = context;
vm.runInContext(source, context);
const api = context.LocalSdrHealth;
const option = (text, value = '0', sdrType = 'rtlsdr') => ({ textContent: text, value, dataset: { sdrType }, isConnected: true });
const runTimers = async () => { while (timers.length) await timers.shift()(); };

(async () => {
    // Only the device /devices marked gets a label.
    const local = option('SDR 0: Generic RTL');
    const other = option('SDR 1: Second', '1');
    api.label(local, { index: 0, health: 'online' });
    api.label(other, { index: 1 });
    assert.equal(local.textContent, 'SDR 0: Generic RTL — Online');
    assert.equal(other.textContent, 'SDR 1: Second');

    // A menu's own trailing tag (in-use marker) stays after the health text.
    local.textContent += ' [ADSB]';
    state = 'missing';
    timers.splice(1);
    await timers.shift()();
    assert.equal(local.textContent, 'SDR 0: Generic RTL — Unplugged [ADSB]');

    // A failed poll keeps the last text; options removed from the page stop being polled.
    ok = false;
    await timers.shift()();
    assert.equal(local.textContent, 'SDR 0: Generic RTL — Unplugged [ADSB]');
    ok = true;
    local.isConnected = false;
    await runTimers();
    assert.equal(timers.length, 0);

    // labelAll matches prebuilt options by the caller's rule.
    const select = { options: [option('0: A', '0', 'rtlsdr'), option('0: H', '0', 'hackrf')] };
    api.labelAll(select, [{ index: 0, sdr_type: 'rtlsdr', health: 'not_reporting' }, { index: 0, sdr_type: 'hackrf' }],
        (o, d) => o.value === String(d.index) && o.dataset.sdrType === (d.sdr_type || 'rtlsdr'));
    assert.deepEqual(select.options.map(o => o.textContent), ['0: A — Not reporting', '0: H']);
    console.log('Local RTL-SDR menu health: marked device only, tags kept, polling and matching passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
