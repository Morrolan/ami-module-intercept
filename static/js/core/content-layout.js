/* Keep existing live-output scrolling usable with content-sized information.
   Callers retain their own auto-scroll preference and message ordering. */
(function () {
    'use strict';
    // The current split main-page bundle omits the legacy mobile-nav initializer.
    // Initialize its existing drawer only if no other bundle has provided it.
    document.addEventListener('DOMContentLoaded', () => queueMicrotask(() => {
        if (typeof window.toggleMobileDrawer === 'function') return;
        const button = document.getElementById('hamburgerBtn');
        const sidebar = document.getElementById('mainSidebar');
        const overlay = document.getElementById('drawerOverlay');
        if (!button || !sidebar || !overlay) return;
        let previousOverflow = '';
        const close = () => {
            if (!sidebar.classList.contains('open')) return;
            sidebar.classList.remove('open');
            overlay.classList.remove('visible');
            button.classList.remove('active');
            button.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = previousOverflow;
        };
        const toggle = () => {
            if (sidebar.classList.contains('open')) { close(); return; }
            previousOverflow = document.body.style.overflow;
            sidebar.classList.add('open');
            overlay.classList.add('visible');
            button.classList.add('active');
            button.setAttribute('aria-expanded', 'true');
            document.body.style.overflow = 'hidden';
        };
        button.setAttribute('aria-controls', 'mainSidebar');
        button.setAttribute('aria-expanded', 'false');
        button.addEventListener('click', toggle);
        overlay.addEventListener('click', close);
        document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
        window.addEventListener('resize', () => { if (innerWidth >= 1024) close(); });
        window.toggleMobileDrawer = toggle;
        window.closeMobileDrawer = close;
    }));
    window.InterceptLayout = Object.freeze({
        scrollToEdge(element, edge = 'end') {
            if (!element || !element.isConnected || !element.getClientRects().length) return;
            const style = getComputedStyle(element);
            // Explicitly bounded overlays still scroll locally.
            if (['auto', 'scroll'].includes(style.overflowY)) {
                element.scrollTop = edge === 'start' ? 0 : element.scrollHeight;
                return;
            }
            const rect = element.getBoundingClientRect();
            // Background messages must not move a page being read elsewhere.
            if (rect.bottom <= 0 || rect.top >= window.innerHeight) return;
            element.scrollIntoView({ block: edge, inline: 'nearest', behavior: 'instant' });
        }
    });
})();
