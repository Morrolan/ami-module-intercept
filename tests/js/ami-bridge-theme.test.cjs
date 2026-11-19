/* Real ami-bridge.js in an isolated frame: AMI's theme message, its origin checks, and the standalone toggle. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const bridge = fs.readFileSync('static/js/ami-bridge.js', 'utf8');
const app = fs.readFileSync('static/js/core/app.js', 'utf8');
const AMI = 'https://ami.example';

function frame({ embedded = true, theme = 'dark', stored = null } = {}) {
    const attrs = { 'data-theme': theme };
    const local = stored === null ? {} : { 'intercept-theme': stored };
    const listeners = { window: {}, document: {} }, posted = [];
    const on = target => (name, fn) => { (listeners[target][name] ||= []).push(fn); };
    const button = { innerHTML: '' };
    const document = {
        readyState: 'interactive',
        documentElement: {
            classList: { add() {} },
            getAttribute: name => attrs[name] ?? null,
            setAttribute: (name, value) => { attrs[name] = String(value); }
        },
        querySelector: sel => (sel === 'meta[name="ami-origin"]' ? { content: AMI } : null),
        querySelectorAll: () => [],
        getElementById: id => (id === 'themeToggle' ? button : null),
        addEventListener: on('document')
    };
    const storage = data => ({
        getItem: k => (Object.hasOwn(data, k) ? data[k] : null),
        setItem: (k, v) => { data[k] = String(v); },
        removeItem: k => { delete data[k]; }
    });
    const parent = { postMessage: (data, target) => posted.push({ data, target }) };
    const context = vm.createContext({
        URL, URLSearchParams, queueMicrotask, setTimeout, clearTimeout, console,
        location: { href: `http://intercept.test/${embedded ? '?ami=1' : ''}`, search: embedded ? '?ami=1' : '', origin: 'http://intercept.test' },
        history: { state: null, replaceState() {} },
        localStorage: storage(local), sessionStorage: storage({}),
        document, addEventListener: on('window')
    });
    context.window = context;
    context.parent = embedded ? parent : context;
    vm.runInContext(bridge, context);
    const fire = (target, name, event = {}) => (listeners[target][name] || []).forEach(fn => fn(event));
    return {
        context, local, posted, button,
        theme: () => attrs['data-theme'],
        setTheme: value => { attrs['data-theme'] = value; },
        send: (data, { origin = AMI, source = parent } = {}) => fire('window', 'message', { origin, source, data }),
        fire,
        listens: name => (listeners.window[name] || []).length > 0
    };
}

// AMI's choice applies in both directions, without touching the standalone setting or echoing back.
let f = frame({ stored: 'dark' });
assert.deepEqual(f.posted.map(p => p.data.type), ['ami-ready']);
f.send({ type: 'ami-theme', theme: 'light' });
assert.equal(f.theme(), 'light');
assert.equal(f.button.innerHTML, 'Dark');
f.send({ type: 'ami-theme', theme: 'dark' });
assert.equal(f.theme(), 'dark');
assert.equal(f.button.innerHTML, 'Light');
assert.equal(f.local['intercept-theme'], 'dark', 'the standalone choice is never overwritten');
assert.deepEqual(f.posted.map(p => p.data.type), ['ami-ready'], 'the theme is not echoed to AMI');

// Only AMI's own window, at its configured origin, with a known value, can change the theme.
f = frame();
f.send({ type: 'ami-theme', theme: 'light' }, { origin: 'https://evil.example' });
f.send({ type: 'ami-theme', theme: 'light' }, { source: {} });
f.send({ type: 'ami-theme', theme: 'blue' });
f.send({ type: 'ami-theme', theme: '' });
f.send({ type: 'ami-theme' });
f.send('ami-theme');
assert.equal(f.theme(), 'dark');

// A message that lands before the page's own start-up loader is re-asserted after it.
f = frame({ stored: 'dark' });
f.send({ type: 'ami-theme', theme: 'light' });
f.setTheme('dark'); // loadTheme() re-applying localStorage on DOMContentLoaded
f.fire('document', 'DOMContentLoaded');
assert.equal(f.theme(), 'light');
f.setTheme('dark');
f.fire('window', 'load');
assert.equal(f.theme(), 'light');
// Before any AMI message, the start-up hooks leave the local theme alone.
f = frame({ theme: 'light' });
f.fire('document', 'DOMContentLoaded');
f.fire('window', 'load');
assert.equal(f.theme(), 'light');

// Standalone: the bridge never listens, and the local toggle still flips and persists.
f = frame({ embedded: false, stored: 'dark' });
assert.equal(f.listens('message'), false);
assert.equal(f.context.InterceptAMI, undefined);
assert.deepEqual(f.posted, []);
vm.runInContext(app, f.context);
f.context.toggleTheme();
assert.equal(f.theme(), 'light');
assert.equal(f.local['intercept-theme'], 'light');
f.context.toggleTheme();
assert.equal(f.theme(), 'dark');
assert.equal(f.local['intercept-theme'], 'dark');

console.log('ami-bridge theme: ok');
