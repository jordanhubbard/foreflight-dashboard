// MVC Model/State Initialization for Flight Table
window.flightDashboardMVC = (() => {
    // Extract flights from DOM table on page load
    function extractFlights() {
        const flights = [];
        document.querySelectorAll('.flight-table tbody tr:not(.details-row)').forEach(row => {
            const cells = row.querySelectorAll('td');
            flights.push({
                id: row.id,
                // Extract only the date (YYYY-MM-DD) from the cell, ignoring icons or extra content
                date: (() => {
                    const cellText = cells[0]?.textContent || '';
                    const match = cellText.match(/(\d{4}-\d{2}-\d{2})/);
                    return match ? match[1] : cellText.trim();
                })(),
                route: cells[1]?.textContent.trim(),
                aircraft: cells[2]?.textContent.trim(),
                total: parseFloat(cells[3]?.textContent) || 0,
                day: parseFloat((cells[4]?.textContent.split('/')[0]) || 0),
                night: parseFloat((cells[4]?.textContent.split('/')[1]) || 0),
                ldg: parseInt(cells[5]?.textContent) || 0,
                role: cells[6]?.textContent.trim(),
                pic: parseFloat(cells[7]?.textContent) || 0,
                dual: parseFloat(cells[8]?.textContent) || 0,
                status: cells[9]?.textContent.trim(),
                ground: parseFloat(cells[10]?.textContent) || 0,
                asel: parseFloat(cells[11]?.textContent) || 0,
                xc: (() => {
    // Try to get from hidden .xc-time cell if present
    const xcCell = row.querySelector('.xc-time');
    if (xcCell) {
        const val = parseFloat(xcCell.textContent);
        return isNaN(val) ? 0 : val;
    }
    return parseFloat(cells[12]?.textContent) || 0;
})(),
                day_time: parseFloat(cells[13]?.textContent) || 0,
                night_time: parseFloat(cells[14]?.textContent) || 0,
                sim_inst: parseFloat(cells[15]?.textContent) || 0,
                dual_rcvd: parseFloat(cells[16]?.textContent) || 0,
                pic_time: parseFloat(cells[17]?.textContent) || 0,
                solo_time: (() => {
    const soloCell = row.querySelector('.solo-time');
    if (soloCell) {
        const val = parseFloat(soloCell.textContent);
        return isNaN(val) ? 0 : val;
    }
    return 0;
})(),
                rowHTML: row.outerHTML // for initial rendering, will be replaced
            });
        });
        return flights;
    }

    // State
    const state = {
        flights: [],
        filters: {
            all: true,
            pic: false,
            dual: false,
            solo: false,
            night: false,
            xc: false,
            instrument: false
        },
        search: '',
        sort: { column: 'date', direction: 'desc' }
    };

    // View stub
    function renderTable() {
        const tbody = document.querySelector('.flight-table tbody');
        if (!tbody) return;
        // Clear table
        tbody.innerHTML = '';
        // Apply search
        let filtered = state.flights.filter(flight => {
            if (!state.search) return true;
            const text = Object.values(flight).join(' ').toLowerCase();
            return text.includes(state.search.toLowerCase());
        });
        // Apply filters
        if (!state.filters.all) {
            const primaryChecked = state.filters.pic || state.filters.dual || state.filters.solo;
            filtered = filtered.filter(flight => {
                // Helper badge checks
                const hasNight = flight.night_time > 0;
                const hasXC = flight.xc > 0;
                const hasInstrument = flight.sim_inst > 0;
                // Primary logic
                if (primaryChecked) {
                    let match = false;
                    if (state.filters.pic && flight.pic > 0) match = true;
                    if (state.filters.dual && flight.dual_rcvd > 0) match = true;
                    if (state.filters.solo && flight.solo_time > 0) match = true;
                    if (!match) return false;
                    // Modifiers: must match all checked
                    if (state.filters.night && !hasNight) return false;
                    if (state.filters.xc && !hasXC) return false;
                    if (state.filters.instrument && !hasInstrument) return false;
                    return true;
                } else {
                    // No primary checked: modifiers act as primary
                    let match = false;
                    if (state.filters.night && hasNight) match = true;
                    if (state.filters.xc && hasXC) match = true;
                    if (state.filters.instrument && hasInstrument) match = true;
                    return match;
                }
            });
        }
        // Sort
        console.log('[Sort] Before:', filtered.map(f => f.date));
        filtered.sort((a, b) => {
            if (state.sort.column === 'date') {
                const result = state.sort.direction === 'asc'
                    ? new Date(a.date) - new Date(b.date)
                    : new Date(b.date) - new Date(a.date);
                return result;
            }
            // Add more sort options if needed
            return 0;
        });
        console.log('[Sort] After:', filtered.map(f => f.date), 'Direction:', state.sort.direction);
        // Render rows
        filtered.forEach(flight => {
            // Render main row
            let row = document.createElement('tr');
            row.id = flight.id;
            row.innerHTML = `
                <td>${flight.date}</td>
                <td>${flight.route}</td>
                <td>${flight.aircraft}</td>
                <td>${flight.total.toFixed(1)}</td>
                <td>${flight.day.toFixed(1)}/${flight.night.toFixed(1)}</td>
                <td>${flight.ldg}</td>
                <td>${flight.role}</td>
                <td>${flight.pic.toFixed(1)}</td>
                <td>${flight.dual.toFixed(1)}</td>
                <td>
                    ${flight.night > 0 ? '<span class="badge badge-night">Night</span>' : ''}
                    ${flight.xc > 0 ? '<span class="badge badge-xc">XC</span>' : ''}
                    ${(flight.pic > 0 && flight.solo_time > 0 && flight.dual_rcvd === 0) ? '<span class="badge badge-solo">Solo</span>' : ''}
                    ${(flight.dual > 0 && flight.solo_time === 0) ? '<span class="badge badge-dual">Dual</span>' : ''}
                    ${flight.pic > 0 ? '<span class="badge bg-success badge-pic">PIC</span>' : ''}
                </td>
                <td class="text-end running-total">${flight.ground.toFixed(1)}</td>
                <td class="text-end running-total">${flight.asel.toFixed(1)}</td>
                <td class="text-end running-total">${flight.xc.toFixed(1)}</td>
                <td class="text-end running-total">${flight.day_time.toFixed(1)}</td>
                <td class="text-end running-total">${flight.night_time.toFixed(1)}</td>
                <td class="text-end running-total">${flight.sim_inst.toFixed(1)}</td>
                <td class="text-end running-total">${flight.dual_rcvd.toFixed(1)}</td>
                <td class="text-end running-total">${flight.pic_time.toFixed(1)}</td>
            `;
            tbody.appendChild(row);
            // Details row could be added here if needed
        });
    }

    // On DOMContentLoaded, extract model and wire up UI
    document.addEventListener('DOMContentLoaded', function() {
        state.flights = extractFlights();
        // Wire up filter checkboxes
        document.querySelectorAll('.filter-checkbox').forEach(cb => {
            cb.addEventListener('change', function() {
                const id = this.id.replace('filter-', '');
                if (id === 'all') {
                    Object.keys(state.filters).forEach(k => state.filters[k] = false);
                    state.filters.all = this.checked;
                } else {
                    state.filters[id] = this.checked;
                    state.filters.all = false;
                    // If none checked, revert to all
                    if (!Object.keys(state.filters).some(k => k !== 'all' && state.filters[k])) {
                        state.filters.all = true;
                    }
                }
                renderTable();
            });
        });
        // Wire up search
        const searchBox = document.getElementById('flight-search');
        if (searchBox) {
            searchBox.addEventListener('input', function() {
                state.search = this.value;
                renderTable();
            });
        }
        // Wire up sort dropdown
        const sortSelect = document.getElementById('date-sort-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                console.log('[Sort Dropdown] Changed to:', this.value);
                state.sort.direction = this.value;
                renderTable();
            });
        }
        // Initial render
        renderTable();
    });

    // Expose for debugging
    return { state, renderTable };
})();
