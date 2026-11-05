/* The key previews the same marker renderer and colours as the live map. */
(function () {
    'use strict';
    function sample(options) {
        const icon = TrackIcons.aircraft({type: 'jet', heading: 0, color: getAltitudeColor(15000), ...options});
        const preview = document.createElement('span');
        preview.className = 'aircraft-key-icon ' + icon.options.className;
        preview.setAttribute('aria-hidden', 'true');
        preview.innerHTML = icon.options.html;
        return preview;
    }

    function row(label, options, attributes = {}) {
        const item = document.createElement('li');
        for (const [key, value] of Object.entries(attributes)) item.dataset[key] = value;
        const text = document.createElement('span');
        text.textContent = label;
        item.append(sample(options), text);
        return item;
    }

    function open() {
        const dialog = document.getElementById('aircraftKeyDialog');
        const colours = dialog.querySelector('.aircraft-key-colours');
        colours.replaceChildren();
        for (const [altitude, label] of [
            [0, 'Grey — altitude unavailable, zero or below'],
            [5000, 'Green — above 0 and below 10,000 ft'],
            [15000, 'Cyan — 10,000–24,999 ft'],
            [30000, 'Yellow — 25,000–34,999 ft'],
            [40000, 'Orange — 35,000 ft and above'],
        ]) colours.append(row(label, {color: getAltitudeColor(altitude)}, {altitude}));

        dialog.querySelector('.aircraft-key-status').replaceChildren(
            row('Khaki — identified as military', {type: 'military', color: MILITARY_MAP_COLOR}, {key: 'military'}),
            row('Blue-grey, smaller icon — on the ground', {ground: true}, {key: 'ground'}),
            row('Red with alert ring — emergency squawk 7500, 7600 or 7700', {emergency: true}, {key: 'emergency'}),
            row('Concentric rings — selected aircraft', {selected: true}, {key: 'selected'}),
        );
        const shapes = dialog.querySelector('.aircraft-key-shapes');
        shapes.replaceChildren();
        for (const [type, label] of Object.entries({
            jet: 'Jet / default', widebody: 'Widebody jet', bizjet: 'Business jet',
            turboprop: 'Turboprop', prop: 'Light aircraft', helicopter: 'Helicopter',
            military: 'Military', glider: 'Glider',
        })) shapes.append(row(label, {type}));
        if (!dialog.open) dialog.showModal();
    }

    document.addEventListener('DOMContentLoaded', () => {
        const dialog = document.getElementById('aircraftKeyDialog');
        document.getElementById('aircraftKeyBtn').addEventListener('click', open);
        dialog.querySelector('button').addEventListener('click', () => dialog.close());
        dialog.addEventListener('click', event => {
            const box = dialog.getBoundingClientRect();
            if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right
                || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
        });
    });
})();
