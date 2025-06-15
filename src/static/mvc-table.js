// Clean JavaScript for ForeFlight Dashboard
// Server-side rendering with minimal client-side interactivity
window.foreflightDashboard = (() => {
    'use strict';

    // Initialize all interactive features
    function init() {
        console.log('[Dashboard] Initializing client-side interactivity...');
        
        try {
            // Initialize tooltips (Bootstrap requirement)
            initTooltips();
            
            // Initialize disclosure triangles for expandable rows
            initDisclosureTriangles();
            
            // Initialize table expansion toggle
            initTableExpansion();
            
            // Initialize search and filters
            initSearchAndFilters();
            
            // Initialize student pilot features
            initStudentPilotFeatures();
            
            // Initialize error navigation
            initErrorNavigation();
            
            console.log('[Dashboard] Client-side interactivity initialized successfully');
        } catch (error) {
            console.error('[Dashboard] Error during initialization:', error);
        }
    }

    // Initialize Bootstrap tooltips with error handling
    function initTooltips() {
        try {
            // Check if Bootstrap is available
            if (typeof bootstrap === 'undefined') {
                console.warn('[Dashboard] Bootstrap not available, skipping tooltip initialization');
                return;
            }

            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
            console.log('[Dashboard] Initialized', tooltipTriggerList.length, 'tooltips');
        } catch (error) {
            console.error('[Dashboard] Error initializing tooltips:', error);
        }
    }

    // Initialize disclosure triangles for expandable content
    function initDisclosureTriangles() {
        try {
            const triangles = document.querySelectorAll('.disclosure-triangle');
            
            triangles.forEach((triangle, index) => {
                const detailsId = triangle.getAttribute('data-target');
                
                triangle.addEventListener('click', function(e) {
                    e.stopPropagation(); // Prevent row click from also firing
                    toggleDetails(this, detailsId);
                });
            });

            // Also allow clicking on flight rows to expand details
            const flightRows = document.querySelectorAll('.flight-table tbody tr:not(.details-row)');
            
            flightRows.forEach((row, index) => {
                row.addEventListener('click', function(e) {
                    // Don't toggle if clicking on a link, input, or triangle
                    if (e.target.tagName === 'A' || e.target.tagName === 'INPUT' || e.target.classList.contains('disclosure-triangle')) {
                        return;
                    }
                    
                    const rowId = this.id.split('-')[1];
                    const detailsRow = document.getElementById(`flight-details-${rowId}`);
                    const triangle = this.querySelector('.disclosure-triangle');
                    
                    if (triangle && detailsRow) {
                        toggleDetails(triangle, detailsRow.id);
                    }
                });
            });
            console.log('[Dashboard] Initialized disclosure triangles');
        } catch (error) {
            console.error('[Dashboard] Error initializing disclosure triangles:', error);
        }
    }

    // Toggle details visibility
    function toggleDetails(triangle, detailsId) {
        try {
            const detailsElement = document.getElementById(detailsId);
            
            if (!detailsElement) {
                console.warn('[Dashboard] Details element not found for ID:', detailsId);
                return;
            }
            
            // The detailsElement is a <td>, we need to show/hide its parent <tr>
            const detailsRow = detailsElement.closest('tr.details-row');
            
            if (!detailsRow) {
                console.warn('[Dashboard] Details row not found for element:', detailsId);
                return;
            }
            
            const isCurrentlyVisible = detailsRow.classList.contains('show');
            
            if (isCurrentlyVisible) {
                detailsRow.classList.remove('show');
                triangle.textContent = '▶';
            } else {
                detailsRow.classList.add('show');
                triangle.textContent = '▼';
            }
        } catch (error) {
            console.error('[Dashboard] Error toggling details:', error);
        }
    }

    // Initialize table expansion (show/hide running totals)
    function initTableExpansion() {
        try {
            const toggleButton = document.getElementById('toggleTables');
            if (!toggleButton) {
                console.log('[Dashboard] Toggle button not found, skipping table expansion init');
                return;
            }

            toggleButton.addEventListener('click', function() {
                const detailsRows = document.querySelectorAll('.details-row');
                const triangles = document.querySelectorAll('.disclosure-triangle');
                const buttonSpan = toggleButton.querySelector('span');
                
                // Check if any details are currently shown
                const anyDetailsShown = Array.from(detailsRows).some(row => 
                    row.classList.contains('show')
                );
                
                if (anyDetailsShown) {
                    // Collapse all details
                    detailsRows.forEach(row => {
                        row.classList.remove('show');
                    });
                    triangles.forEach(triangle => {
                        triangle.textContent = '▶';
                    });
                    if (buttonSpan) buttonSpan.textContent = 'Expand Tables';
                    toggleButton.classList.remove('btn-secondary');
                    toggleButton.classList.add('btn-outline-success');
                } else {
                    // Expand all details
                    detailsRows.forEach(row => {
                        row.classList.add('show');
                    });
                    triangles.forEach(triangle => {
                        triangle.textContent = '▼';
                    });
                    if (buttonSpan) buttonSpan.textContent = 'Collapse Tables';
                    toggleButton.classList.remove('btn-outline-success');
                    toggleButton.classList.add('btn-secondary');
                }
            });
            console.log('[Dashboard] Initialized table expansion toggle');
        } catch (error) {
            console.error('[Dashboard] Error initializing table expansion:', error);
        }
    }

    // Initialize search and filter functionality
    function initSearchAndFilters() {
        try {
            // Search functionality
            const searchInput = document.getElementById('flight-search');
            if (searchInput) {
                searchInput.addEventListener('input', applyFiltersAndSearch);
                console.log('[Dashboard] Initialized search input');
            }

            // Filter checkboxes
            const filterCheckboxes = document.querySelectorAll('.filter-checkbox');
            console.log('[Dashboard] Found', filterCheckboxes.length, 'filter checkboxes');
            
            filterCheckboxes.forEach((checkbox, index) => {
                console.log('[Dashboard] Setting up checkbox', index, ':', checkbox.id);
                checkbox.addEventListener('change', function() {
                    console.log('[Dashboard] Filter changed:', this.id, 'checked:', this.checked);
                    handleFilterChange(this);
                    applyFiltersAndSearch();
                });
            });

            // Sort dropdown
            const sortSelect = document.getElementById('date-sort-select');
            if (sortSelect) {
                sortSelect.addEventListener('change', function() {
                    applySorting(this.value);
                });
                console.log('[Dashboard] Initialized sort dropdown');
            }

            // Initial filter application - only if we have a table
            const flightTable = document.querySelector('.flight-table tbody');
            if (flightTable && flightTable.children.length > 0) {
                console.log('[Dashboard] Found flight table with data, applying initial filters');
                applyFiltersAndSearch();
            } else {
                console.log('[Dashboard] No flight table data found, skipping initial filter application');
            }
            console.log('[Dashboard] Initialized search and filters');
        } catch (error) {
            console.error('[Dashboard] Error initializing search and filters:', error);
        }
    }

    // Handle filter checkbox logic with mutual exclusivity rules
    function handleFilterChange(checkbox) {
        try {
            console.log('[Dashboard] handleFilterChange called for:', checkbox.id, 'checked:', checkbox.checked);
            const filterCheckboxes = document.querySelectorAll('.filter-checkbox');
            
            if (checkbox.id === 'filter-all' && checkbox.checked) {
                // If 'All' is checked, uncheck other filters
                filterCheckboxes.forEach(cb => {
                    if (cb.id !== 'filter-all') cb.checked = false;
                });
            } else if (checkbox.id !== 'filter-all' && checkbox.checked) {
                // If any other filter is checked, uncheck 'All'
                const allCheckbox = document.getElementById('filter-all');
                if (allCheckbox) allCheckbox.checked = false;
                
                // Apply mutual exclusivity rules
                const picCheckbox = document.getElementById('filter-pic');
                const dualCheckbox = document.getElementById('filter-dual');
                const soloCheckbox = document.getElementById('filter-solo');
                
                if (checkbox.id === 'filter-pic' && checkbox.checked) {
                    // PIC is mutually exclusive with dual
                    if (dualCheckbox) dualCheckbox.checked = false;
                } else if (checkbox.id === 'filter-dual' && checkbox.checked) {
                    // Dual is mutually exclusive with PIC and solo
                    if (picCheckbox) picCheckbox.checked = false;
                    if (soloCheckbox) soloCheckbox.checked = false;
                } else if (checkbox.id === 'filter-solo' && checkbox.checked) {
                    // Solo is mutually exclusive with dual
                    if (dualCheckbox) dualCheckbox.checked = false;
                }
            }
            
            // If no filters are checked, check 'All' by default
            const anyOtherChecked = Array.from(filterCheckboxes).some(cb => 
                cb.id !== 'filter-all' && cb.checked
            );
            if (!anyOtherChecked) {
                const allCheckbox = document.getElementById('filter-all');
                if (allCheckbox) allCheckbox.checked = true;
            }
        } catch (error) {
            console.error('[Dashboard] Error handling filter change:', error);
        }
    }

    // Apply search and filters via server-side request
    function applyFiltersAndSearch() {
        try {
            // Get filter states
            const filters = {
                all: document.getElementById('filter-all')?.checked || false,
                pic: document.getElementById('filter-pic')?.checked || false,
                dual: document.getElementById('filter-dual')?.checked || false,
                solo: document.getElementById('filter-solo')?.checked || false,
                night: document.getElementById('filter-night')?.checked || false,
                xc: document.getElementById('filter-xc')?.checked || false,
                instrument: document.getElementById('filter-instrument')?.checked || false
            };
            
            console.log('[Dashboard] Applying filters:', filters);
            
            // Show loading state
            const tbody = document.querySelector('.flight-table tbody');
            const countDisplay = document.getElementById('visible-row-count');
            
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="100%" class="text-center">Loading filtered results...</td></tr>';
            }
            
            // Send filter request to server
            fetch('/filter-flights', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(filters)
            })
            .then(response => response.json())
                         .then(data => {
                 if (data.success) {
                     // Check if details were expanded before replacing content
                     const detailsRows = document.querySelectorAll('.details-row');
                     const wereDetailsExpanded = Array.from(detailsRows).some(row => 
                         row.classList.contains('show')
                     );
                     
                     // Replace table content with filtered results
                     if (tbody) {
                         tbody.innerHTML = data.table_html;
                     }
                     
                     // Restore details expansion state if they were expanded before
                     if (wereDetailsExpanded) {
                         const newDetailsRows = document.querySelectorAll('.details-row');
                         const newTriangles = document.querySelectorAll('.disclosure-triangle');
                         newDetailsRows.forEach(row => {
                             row.classList.add('show');
                         });
                         newTriangles.forEach(triangle => {
                             triangle.textContent = '▼';
                         });
                         console.log('[Dashboard] Restored expanded details state');
                     }
                     
                     // Update count display
                     if (countDisplay) {
                         countDisplay.textContent = `Showing ${data.total_entries} of ${data.original_total} entries`;
                     }
                     
                     // Re-initialize disclosure triangles for new content
                     initDisclosureTriangles();
                     
                     // Re-initialize tooltips for new content
                     initTooltips();
                     
                     console.log('[Dashboard] Successfully applied filters:', data.total_entries, 'entries shown');
                 } else {
                    console.error('[Dashboard] Filter request failed:', data.error);
                    if (tbody) {
                        tbody.innerHTML = `<tr><td colspan="100%" class="text-center text-danger">Error: ${data.error}</td></tr>`;
                    }
                }
            })
            .catch(error => {
                console.error('[Dashboard] Error sending filter request:', error);
                if (tbody) {
                    tbody.innerHTML = `<tr><td colspan="100%" class="text-center text-danger">Error loading filtered results</td></tr>`;
                }
            });
            
        } catch (error) {
            console.error('[Dashboard] Error applying filters and search:', error);
        }
    }

    // Apply sorting to table
    function applySorting(direction) {
        try {
            const tbody = document.querySelector('.flight-table tbody');
            if (!tbody) return;
            
            const rows = Array.from(tbody.querySelectorAll('tr:not(.details-row)'));
            const detailsRows = Array.from(tbody.querySelectorAll('tr.details-row'));
            
            // Sort rows by date
            rows.sort((a, b) => {
                const dateA = new Date(a.cells[0].textContent.trim());
                const dateB = new Date(b.cells[0].textContent.trim());
                
                return direction === 'asc' ? dateA - dateB : dateB - dateA;
            });
            
            // Clear and re-append in sorted order
            tbody.innerHTML = '';
            rows.forEach(row => {
                tbody.appendChild(row);
                // Find and append corresponding details row
                const detailsRow = detailsRows.find(dr => 
                    dr.querySelector('td[id]')?.id === `flight-details-${row.id.split('-')[1]}`
                );
                if (detailsRow) {
                    tbody.appendChild(detailsRow);
                }
            });
            
            // Reapply filters after sorting
            applyFiltersAndSearch();
        } catch (error) {
            console.error('[Dashboard] Error applying sorting:', error);
        }
    }

    // Initialize student pilot specific features
    function initStudentPilotFeatures() {
        try {
            const studentCheckbox = document.getElementById('studentPilotCheck');
            const endorsementCard = document.getElementById('endorsement-summary-card');
            const verifyPICButton = document.getElementById('verifyPICButton');
            
            if (studentCheckbox) {
                studentCheckbox.addEventListener('change', function() {
                    const isStudentPilot = this.checked;
                    
                    if (endorsementCard) {
                        endorsementCard.style.display = isStudentPilot ? 'block' : 'none';
                    }
                    
                    if (verifyPICButton) {
                        verifyPICButton.style.display = isStudentPilot ? 'inline-block' : 'none';
                    }
                    
                    toggleEndorsementsTab(isStudentPilot);
                });
            }
            console.log('[Dashboard] Initialized student pilot features');
        } catch (error) {
            console.error('[Dashboard] Error initializing student pilot features:', error);
        }
    }

    // Toggle endorsements tab visibility
    function toggleEndorsementsTab(show) {
        try {
            // Check if Bootstrap is available for tab functionality
            if (typeof bootstrap === 'undefined') {
                console.warn('[Dashboard] Bootstrap not available, skipping endorsements tab toggle');
                return;
            }

            const mainTabs = document.getElementById('mainTabs');
            const mainTabsContent = document.getElementById('mainTabsContent');
            const tabId = 'endorsements-tab';
            const paneId = 'endorsements';
            
            let tab = document.getElementById(tabId);
            let pane = document.getElementById(paneId);
            
            if (show && !tab) {
                // Create endorsements tab
                const li = document.createElement('li');
                li.className = 'nav-item';
                li.role = 'presentation';
                li.innerHTML = `<button class="nav-link" id="${tabId}" data-bs-toggle="tab" data-bs-target="#${paneId}" type="button" role="tab">Endorsements</button>`;
                mainTabs.appendChild(li);
                
                // Create endorsements pane
                const endorsementsPane = document.createElement('div');
                endorsementsPane.className = 'tab-pane fade';
                endorsementsPane.id = paneId;
                endorsementsPane.role = 'tabpanel';
                endorsementsPane.innerHTML = document.getElementById('endorsements-tab-content-template').innerHTML;
                mainTabsContent.appendChild(endorsementsPane);
                
                // Auto-switch to the tab
                const endorsementsTabBtn = document.getElementById(tabId);
                if (endorsementsTabBtn) {
                    new bootstrap.Tab(endorsementsTabBtn).show();
                }
            } else if (!show) {
                // Remove endorsements tab and pane
                if (tab) tab.parentElement.remove();
                if (pane) pane.remove();
            }
        } catch (error) {
            console.error('[Dashboard] Error toggling endorsements tab:', error);
        }
    }

    // Initialize error navigation
    function initErrorNavigation() {
        try {
            const errorEntries = document.querySelectorAll('.has-error');
            let currentErrorIndex = 0;

            if (errorEntries.length === 0) {
                console.log('[Dashboard] No error entries found, skipping error navigation init');
                return;
            }

            function updateErrorCounter() {
                const counter = document.getElementById('error-counter');
                if (counter) {
                    counter.textContent = `${currentErrorIndex + 1}/${errorEntries.length}`;
                }
            }

            function navigateError(direction) {
                // Remove highlight from current error
                errorEntries[currentErrorIndex].classList.remove('current-error');
                
                // Update index
                currentErrorIndex = (currentErrorIndex + direction + errorEntries.length) % errorEntries.length;
                
                // Highlight new current error and scroll to it
                errorEntries[currentErrorIndex].classList.add('current-error');
                errorEntries[currentErrorIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                updateErrorCounter();
            }

            // Initialize error counter
            updateErrorCounter();

            // Keyboard navigation
            document.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowLeft') {
                    navigateError(-1);
                } else if (e.key === 'ArrowRight') {
                    navigateError(1);
                }
            });

            // Expose navigation function globally for button clicks
            window.navigateError = navigateError;
            console.log('[Dashboard] Initialized error navigation for', errorEntries.length, 'errors');
        } catch (error) {
            console.error('[Dashboard] Error initializing error navigation:', error);
        }
    }

    // Track if already initialized to prevent double initialization
    let isInitialized = false;
    
    // Wrapper function to prevent double initialization
    function safeInit() {
        if (isInitialized) {
            console.log('[Dashboard] Already initialized, skipping');
            return;
        }
        isInitialized = true;
        init();
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', safeInit);

    // Expose public API
    return {
        init: safeInit,
        applyFiltersAndSearch,
        applySorting
    };
})();
