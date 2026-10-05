window.dash_clientside = Object.assign({}, window.dash_clientside, {
    simulation_sharing: {
        auto_run: function(config, fieldIds, fieldValues, fieldClasses, settings) {
            const unchanged = window.dash_clientside.no_update;
            if (!config || config.started) return [unchanged, unchanged];
            const values = Array.prototype.slice.call(arguments, 5);
            const clicks = values.pop();
            if (clicks) return [unchanged, Object.assign({}, config, {started: true})];

            const actual = {};
            config.control_names.forEach((name, index) => { actual[name] = values[index]; });
            (fieldIds || []).forEach((id, index) => {
                const ordered = {};
                Object.keys(id).sort().forEach(key => { ordered[key] = id[key]; });
                actual[JSON.stringify(ordered)] = fieldValues[index];
            });
            // Field classes depend on the existing validation callbacks; this
            // also waits for dynamic fields and material-mode restoration.
            if (!fieldClasses || fieldClasses.length < config.field_keys.length ||
                !config.field_keys.every(key => Object.prototype.hasOwnProperty.call(actual, key))) {
                return [unchanged, unchanged];
            }
            const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
            if (!Object.entries(config.expected_controls).every(([key, value]) => same(actual[key], value))) {
                return [unchanged, unchanged];
            }
            const plot = (settings || {})[config.workspace] || {};
            if (!Object.entries(config.plot_settings).every(([key, value]) => same(plot[key], value))) {
                return [unchanged, unchanged];
            }
            // Both outputs update together. Later edits and callback updates
            // see the started flag and cannot launch a second automatic run.
            return [1, Object.assign({}, config, {started: true})];
        }
    }
});
