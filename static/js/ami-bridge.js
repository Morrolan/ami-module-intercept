/* Embedded UI only. No bearer credentials or radio commands cross this bridge. */
(() => {
  'use strict';
  const configured = document.querySelector('meta[name="ami-origin"]')?.content;
  if (!configured || window.parent === window) return;
  let origin;
  try { origin = new URL(configured).origin; } catch { return; }
  // Per-tab frame state also covers existing programmatic mode/settings/logout navigation.
  // A standalone window never uses this state, and a configuration change invalidates it.
  let embedded = new URLSearchParams(location.search).get('ami') === '1';
  try {
    embedded ||= sessionStorage.getItem('intercept-ami-parent') === origin;
    if (embedded) sessionStorage.setItem('intercept-ami-parent', origin);
  } catch { /* Explicit ?ami=1 and link propagation still work without storage. */ }
  if (!embedded) return;
  const current = new URL(location.href);
  current.searchParams.set('ami', '1');
  history.replaceState(history.state, '', current);
  document.documentElement.classList.add('ami-embedded');
  let autoplay = false;
  let speechId = Date.now();
  const pending = new Map();
  const finish = id => {
    const item = pending.get(id);
    if (!item) return;
    pending.delete(id);
    clearTimeout(item.timer);
    item.done();
  };
  const voice = Object.freeze({
    get autoplay() { return autoplay; },
    speak(text, done = () => {}, automatic = false) {
      if (typeof text !== 'string' || !text.trim() || (automatic && !autoplay)) {
        queueMicrotask(done);
        return;
      }
      const id = ++speechId;
      pending.set(id, { done, timer: setTimeout(() => finish(id), 120000) });
      window.parent.postMessage({ type: 'ami-speak', id, text: text.slice(0, 20000) }, origin);
    },
    stop() {
      for (const item of pending.values()) clearTimeout(item.timer);
      pending.clear();
      window.parent.postMessage({ type: 'ami-stop' }, origin);
    }
  });
  window.InterceptAMI = voice;
  window.addEventListener('pagehide', () => voice.stop());
  const embedUrl = value => {
    const url = new URL(value, location.href);
    if (url.origin === location.origin) url.searchParams.set('ami', '1');
    return url;
  };
  // Keep embedding across local navigation and sign-in, without marking external links.
  document.addEventListener('click', e => {
    const link = e.target.closest('a[href]');
    if (!link || link.hasAttribute('download') || link.getAttribute('href').startsWith('#')) return;
    const url = embedUrl(link.href);
    if (url.origin === location.origin) link.href = url.href;
  }, true);
  document.querySelectorAll('form').forEach(form => {
    const url = embedUrl(form.action || location.href);
    if (url.origin === location.origin) {
      form.action = url.href;
      if (form.method.toLowerCase() === 'get') {
        const input = document.createElement('input');
        input.type = 'hidden'; input.name = 'ami'; input.value = '1'; form.append(input);
      }
    }
  });
  // AMI owns the theme while embedded. It is applied for this page only: the
  // standalone choice in localStorage ('intercept-theme') is left untouched and
  // nothing is sent back. Page start-up re-applies the local choice
  // (loadTheme on DOMContentLoaded), so AMI's theme is re-asserted after it.
  let amiTheme = null;
  const applyTheme = () => {
    if (!amiTheme) return;
    document.documentElement.setAttribute('data-theme', amiTheme);
    const btn = document.getElementById('themeToggle');
    if (btn) {
      const icons = window.Icons;
      btn.innerHTML = amiTheme === 'light' ? (icons ? icons.moon() : 'Dark') : (icons ? icons.sun() : 'Light');
    }
  };
  document.addEventListener('DOMContentLoaded', applyTheme, { once: true });
  window.addEventListener('load', applyTheme, { once: true });
  window.addEventListener('message', e => {
    if (e.origin !== origin || e.source !== window.parent || !e.data || typeof e.data !== 'object') return;
    if (e.data.type === 'ami-theme') {
      if (e.data.theme === 'light' || e.data.theme === 'dark') { amiTheme = e.data.theme; applyTheme(); }
    }
    else if (e.data.type === 'ami-settings') autoplay = e.data.autoplay === true;
    else if (e.data.type === 'ami-speech' && e.data.state === 'idle') finish(e.data.id);
    else if (e.data.type === 'ami-focus' || e.data.type === 'ami.focus') document.querySelector('main, .main-content, .dashboard-container')?.focus();
  });
  window.parent.postMessage({ type: 'ami-ready' }, origin);
})();
