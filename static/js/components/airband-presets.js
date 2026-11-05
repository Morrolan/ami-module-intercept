/* Account-synced names for airband frequencies; editing never starts a radio. */
(function () {
    'use strict';
    const KEY = 'airband.frequencyPresets';
    let presets = [];
    const select = () => document.getElementById('airbandFreqSelect');
    const current = () => presets.find(p => 'saved:' + p.id === select()?.value);
    const validFrequency = n => Number.isFinite(n) && n >= 118 && n <= 137;
    const status = text => { document.getElementById('airbandPresetStatus').textContent = text; };

    function syncSelection() {
        const preset = current();
        document.getElementById('airbandPresetName').value = preset?.name || '';
        document.getElementById('airbandPresetRemove').disabled = !preset;
        status('');
    }

    function render() {
        const menu = select();
        const selected = menu.value;
        const previousFrequency = window.getAirbandFrequency();
        menu.querySelector('[data-saved-airband]')?.remove();
        const group = document.createElement('optgroup');
        group.label = 'Saved frequencies';
        group.dataset.savedAirband = 'true';
        for (const p of presets) {
            const option = document.createElement('option');
            option.value = 'saved:' + p.id;
            option.textContent = `${p.name} · ${p.frequency.toFixed(3)} MHz`;
            group.append(option);
        }
        if (presets.length) menu.insertBefore(group, menu.querySelector('[value="custom"]'));
        menu.value = selected;
        if (!menu.value) {
            menu.value = 'custom';
            document.getElementById('airbandCustomFreq').value = previousFrequency;
            document.getElementById('airbandCustomFreq').style.display = 'inline-block';
            document.getElementById('airbandSpacing').style.display = 'inline-block';
        }
        syncSelection();
        window.updateAirbandChip();
    }

    function load() {
        let stored;
        try { stored = JSON.parse(localStorage.getItem(KEY) || '[]'); } catch { stored = []; }
        const seen = new Set();
        const clean = Array.isArray(stored) ? stored.filter(p => {
            if (!p || typeof p.id !== 'string' || !/^[\w-]{1,80}$/.test(p.id) || seen.has(p.id)
                || typeof p.name !== 'string' || !p.name.trim() || p.name.length > 60
                || !validFrequency(p.frequency)) return false;
            seen.add(p.id);
            return true;
        }).slice(0, 100).map(p => ({id: p.id, name: p.name.trim(), frequency: p.frequency})) : [];
        // Preserve the old selected frequency even if another tab removes its preset.
        const frequency = window.getAirbandFrequency();
        if (current() && !clean.some(p => p.id === current().id)) {
            select().value = 'custom';
            document.getElementById('airbandCustomFreq').value = frequency;
            document.getElementById('airbandCustomFreq').style.display = 'inline-block';
            document.getElementById('airbandSpacing').style.display = 'inline-block';
        }
        presets = clean;
        render();
    }

    function persist(next) {
        try { localStorage.setItem(KEY, JSON.stringify(next)); }
        catch { status('Could not save frequencies. Please try again.'); return false; }
        presets = next;
        return true;
    }

    function save() {
        const name = document.getElementById('airbandPresetName').value.trim();
        const frequency = window.getAirbandFrequency();
        if (!validFrequency(frequency)) { status('Enter an airband frequency from 118 to 137 MHz.'); return; }
        if (!name || name.length > 60) { status('Enter a name of 1–60 characters.'); return; }
        const existing = current();
        if (!existing && presets.length >= 100) { status('Remove a saved frequency before adding another (maximum 100).'); return; }
        const id = existing?.id || crypto.randomUUID?.() || `preset-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const record = {id, name, frequency};
        const next = existing ? presets.map(p => p.id === existing.id ? record : p) : [...presets, record];
        if (!persist(next)) return;
        render();
        select().value = 'saved:' + record.id;
        // Selecting after saving only updates the form; it never retunes the radio.
        document.getElementById('airbandCustomFreq').style.display = 'none';
        document.getElementById('airbandSpacing').style.display = 'none';
        syncSelection();
        window.updateAirbandChip();
        status('Saved to your frequency presets.');
    }

    function remove() {
        const record = current();
        if (!record || !persist(presets.filter(p => p.id !== record.id))) return;
        select().value = 'custom';
        document.getElementById('airbandCustomFreq').value = record.frequency;
        document.getElementById('airbandCustomFreq').style.display = 'inline-block';
        document.getElementById('airbandSpacing').style.display = 'inline-block';
        render();
        status('Removed. The current frequency is unchanged.');
    }

    window.AirbandPresets = Object.freeze({syncSelection, frequency: () => current()?.frequency});
    document.addEventListener('DOMContentLoaded', () => {
        load();
        document.getElementById('airbandPresetSave').addEventListener('click', save);
        document.getElementById('airbandPresetRemove').addEventListener('click', remove);
        window.addEventListener('storage', event => { if (event.key === KEY || event.key === null) load(); });
    });
})();
