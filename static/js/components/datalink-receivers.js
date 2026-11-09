/* Explicit receiver identity for ACARS and VDL2; never inherit ADS-B routing. */
(() => {
    'use strict';
    const panels = Object.fromEntries(['acars', 'vdl2'].map(panel => [panel, {
        selected: null, running: false, active: null, source: 'local'
    }]));
    let receivers = [], pending = null;
    const agentNames = new Map();
    const key = r => `${r.source}|${r.sdr_type}:${r.device}`;
    const host = source => source === 'local' ? 'This server' : (agentNames.get(source) || 'Remote agent');
    function option(value, label, disabled = false) {
        const node = document.createElement('option');
        node.value = value;
        node.textContent = label;
        node.disabled = disabled;
        return node;
    }
    function render(panel) {
        const state = panels[panel], select = document.getElementById(`${panel}DeviceSelect`);
        if (!select) return;
        if (state.selected === null && receivers.length) state.selected = receivers.find(r => r.source === 'local')?.value || '';
        select.replaceChildren();
        for (const receiver of receivers) {
            const node = option(receiver.value, receiver.label);
            if (receiver.device_info) window.LocalSdrHealth?.label(node, receiver.device_info);
            select.append(node);
        }
        if (state.running && !receivers.some(r => r.value === state.selected)) {
            const label = state.active
                ? `${host(state.source)} — SDR ${state.active.device} (${state.active.sdr_type}) — running`
                : `Running receiver on ${host(state.source)}`;
            select.append(option(state.selected, label, true));
        } else if (state.selected && !receivers.some(r => r.value === state.selected)) {
            select.append(option(state.selected, 'Selected receiver unavailable', true));
        } else if (!state.selected) {
            select.prepend(option('', pending ? 'Loading receivers…' : (receivers.length ? 'Select a receiver' : 'No receivers available'), true));
        }
        select.value = state.selected || '';
        select.disabled = state.running;
    }
    function records(devices, source) {
        return (Array.isArray(devices) ? devices : []).flatMap((device, i) => {
            const index = device.index ?? i;
            if (!Number.isInteger(Number(index)) || Number(index) < 0) return [];
            const r = {source, device: String(index), sdr_type: device.sdr_type || 'rtlsdr'};
            r.value = key(r);
            r.label = `${host(source)} — SDR ${index}: ${device.name || device.type || r.sdr_type}`;
            if (source === 'local') r.device_info = device;
            return [r];
        });
    }
    async function json(url) {
        const response = await fetchJsonWithTimeout(url, {}, 6000);
        if (!response.ok) throw new Error('Receiver list unavailable');
        return response.json();
    }
    function refresh(force = false) {
        if (pending) return pending;
        pending = (async () => {
            const [local, registered] = await Promise.allSettled([
                getDetectedDevices(force), json('/controller/agents')
            ]);
            const next = records(local.status === 'fulfilled' ? local.value : [], 'local');
            if (!receivers.length && next.length) {
                receivers = next;
                for (const panel of Object.keys(panels)) render(panel);
            }
            const agents = registered.status === 'fulfilled' ? registered.value.agents || [] : [];
            const remote = await Promise.allSettled(agents.filter(a => a.healthy !== false).map(async agent => {
                const source = String(agent.id);
                agentNames.set(source, agent.name || 'Remote agent');
                const data = await json(`/controller/agents/${encodeURIComponent(source)}?refresh=true`);
                const interfaces = data.agent?.interfaces || {};
                return records(interfaces.sdr_devices || interfaces.devices || [], source);
            }));
            for (const result of remote) if (result.status === 'fulfilled') next.push(...result.value);
            receivers = next;
        })().catch(error => console.warn('Datalink receiver discovery failed:', error.message)).finally(() => {
            pending = null;
            for (const panel of Object.keys(panels)) {
                render(panel);
                const button = document.getElementById(`${panel}RefreshReceivers`);
                if (button) button.disabled = false;
            }
        });
        for (const panel of Object.keys(panels)) {
            const button = document.getElementById(`${panel}RefreshReceivers`);
            if (button) button.disabled = true;
        }
        return pending;
    }
    window.DatalinkReceivers = Object.freeze({
        refresh,
        get(panel) {
            const state = panels[panel];
            if (state.running) return state.active;
            const value = document.getElementById(`${panel}DeviceSelect`)?.value;
            return receivers.find(r => r.value === value) || null;
        },
        setRunning(panel, running, info = {}) {
            const state = panels[panel];
            if (running) {
                const source = String(info.source ?? 'local');
                if (info.device !== null && info.device !== undefined && info.sdr_type) {
                    state.active = {source, device: String(info.device), sdr_type: info.sdr_type};
                } else if (!state.running || state.source !== source) {
                    state.active = null;
                }
                state.source = source;
                state.selected = state.active ? key(state.active) : `running|${source}`;
            } else {
                state.active = null;
                if (state.selected?.startsWith('running|')) state.selected = null;
            }
            state.running = running;
            render(panel);
        }
    });
    document.addEventListener('DOMContentLoaded', () => {
        for (const panel of Object.keys(panels)) {
            document.getElementById(`${panel}DeviceSelect`)?.addEventListener('change', event => {
                if (!panels[panel].running) panels[panel].selected = event.target.value;
                else render(panel);
            });
            render(panel);
        }
        refresh();
    });
})();
