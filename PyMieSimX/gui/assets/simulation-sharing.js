window.dash_clientside = Object.assign({}, window.dash_clientside, {
    simulation_sharing: {
        copy_feedback: function(clicks, status) {
            const sharing = window.dash_clientside.simulation_sharing;
            const base = 'toolbar-button toolbar-button-secondary simulation-copy-button';
            const title = 'Copy a link to this simulation setup';
            window.clearTimeout(sharing.feedbackTimer);
            if (!clicks) return [base, title];
            if (!status || status.clicks !== clicks) {
                return [base + ' simulation-copy-pending', 'Copying the simulation link…'];
            }
            const button = document.getElementById('simulation-clipboard');
            sharing.feedbackTimer = window.setTimeout(function() {
                if (document.getElementById('simulation-clipboard') === button) {
                    window.dash_clientside.set_props('simulation-clipboard', {className: base, title: title});
                }
            }, 2000);
            return status.copied
                ? [base + ' simulation-copy-success', 'Simulation link copied to clipboard']
                : [base + ' simulation-copy-error', 'Unable to copy. Try again or check clipboard permissions.'];
        },
        copy_link: async function(link) {
            if (!link) return window.dash_clientside.no_update;
            if (!link.url) return {clicks: link.clicks, copied: false};
            if (window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText) {
                try {
                    await navigator.clipboard.writeText(link.url);
                    return {clicks: link.clicks, copied: true};
                } catch (error) {
                    // Older browsers and denied clipboard permissions can
                    // still support copying through the document selection.
                }
            }
            const field = document.createElement('textarea');
            const focused = document.activeElement;
            field.value = link.url;
            field.setAttribute('readonly', '');
            field.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none;';
            document.body.appendChild(field);
            let copied = false;
            try {
                field.select();
                copied = document.execCommand('copy');
            } catch (error) {
                copied = false;
            } finally {
                field.remove();
                if (focused && focused.focus) focused.focus({preventScroll: true});
            }
            return {clicks: link.clicks, copied: copied};
        },
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
