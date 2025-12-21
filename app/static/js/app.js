// Playlist Service - Main JavaScript

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type} px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3 toast-enter`;

    const iconMap = {
        success: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
        error: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
        warning: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>',
        info: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
    };

    const colorMap = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-500 text-white'
    };

    toast.className = `px-4 py-3 rounded-lg shadow-lg flex items-center space-x-3 toast-enter ${colorMap[type]}`;
    toast.innerHTML = `
        <span>${iconMap[type]}</span>
        <span class="flex-1">${escapeHtml(message)}</span>
        <button onclick="this.parentElement.remove()" class="opacity-70 hover:opacity-100">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
        </button>
    `;

    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Modal functions
function showModal(title, content, buttons = []) {
    closeModal();

    const backdrop = document.createElement('div');
    backdrop.id = 'modal-active';
    backdrop.className = 'modal-backdrop fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40';
    backdrop.onclick = (e) => {
        if (e.target === backdrop) closeModal();
    };

    const modal = document.createElement('div');
    modal.className = 'bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto';

    modal.innerHTML = `
        <div class="flex items-center justify-between px-6 py-4 border-b">
            <h3 class="text-lg font-semibold text-gray-900">${escapeHtml(title)}</h3>
            <button type="button" class="text-gray-400 hover:text-gray-600" data-modal-close>
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
        <div class="px-6 py-4" data-modal-content></div>
    `;

    const contentContainer = modal.querySelector('[data-modal-content]');
    if (contentContainer) {
        contentContainer.innerHTML = content;
    }

    const closeButton = modal.querySelector('[data-modal-close]');
    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }

    if (buttons.length > 0) {
        const footer = document.createElement('div');
        footer.className = 'px-6 py-4 border-t flex justify-end space-x-3';

        buttons.forEach(btn => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `px-4 py-2 rounded-md text-sm font-medium ${btn.class || ''}`;
            button.textContent = btn.text || '';

            if (typeof btn.onclick === 'function') {
                button.addEventListener('click', btn.onclick);
            } else if (typeof btn.onclick === 'string' && btn.onclick) {
                button.setAttribute('onclick', btn.onclick);
            }

            footer.appendChild(button);
        });

        modal.appendChild(footer);
    }

    backdrop.appendChild(modal);
    document.getElementById('modal-container').appendChild(backdrop);

    // Focus first input if exists
    const firstInput = modal.querySelector('input:not([readonly]), select, textarea');
    if (firstInput) firstInput.focus();
}

function closeModal() {
    const modal = document.getElementById('modal-active');
    if (modal) modal.remove();
}

// Confirmation dialog
function showConfirm(title, message, details, onConfirm) {
    const content = `
        <div class="flex items-start space-x-4">
            <div class="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
            </div>
            <div>
                <p class="text-gray-900">${escapeHtml(message)}</p>
                ${details ? `<p class="mt-2 text-sm text-gray-600">${escapeHtml(details)}</p>` : ''}
            </div>
        </div>
    `;

    showModal(title, content, [
        { text: 'Cancel', class: 'bg-gray-200 text-gray-800 hover:bg-gray-300', onclick: closeModal },
        {
            text: 'Delete',
            class: 'bg-red-600 text-white hover:bg-red-700',
            onclick: async () => {
                closeModal();
                if (typeof onConfirm === 'function') {
                    await onConfirm();
                }
            }
        }
    ]);
}

// Utility functions
function onDomReady(callback) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', callback, { once: true });
    } else {
        callback();
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initResizableTable(tableId, storageKey) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const key = storageKey || `${tableId}:column-widths`;
    let storedWidths = {};

    try {
        storedWidths = JSON.parse(localStorage.getItem(key) || '{}');
    } catch (error) {
        storedWidths = {};
    }

    const headers = table.querySelectorAll('thead th');
    headers.forEach(th => {
        const colKey = th.dataset.colKey;
        if (colKey && storedWidths[colKey]) {
            th.style.width = `${storedWidths[colKey]}px`;
            return;
        }
        th.style.width = `${th.offsetWidth}px`;
    });

    const handles = table.querySelectorAll('.resize-handle');
    handles.forEach(handle => {
        handle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const th = handle.parentElement;
            const startX = e.pageX;
            const startWidth = th.offsetWidth;

            handle.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            function onMouseMove(event) {
                const newWidth = startWidth + (event.pageX - startX);
                if (newWidth > 40) {
                    th.style.width = `${newWidth}px`;
                }
            }

            function onMouseUp() {
                handle.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);

                const colKey = th.dataset.colKey;
                if (!colKey) return;

                const widths = { ...storedWidths, [colKey]: th.offsetWidth };
                storedWidths = widths;
                try {
                    localStorage.setItem(key, JSON.stringify(widths));
                } catch (error) {
                    // Ignore storage failures (private mode or disabled storage).
                }
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    });
}

function initTableSort(tableId, options) {
    const table = document.getElementById(tableId);
    if (!table) return null;

    const resolvedOptions = options || {};
    let sortBy = resolvedOptions.sortBy || '';
    let sortDir = resolvedOptions.sortDir || 'asc';
    const onSortChange = resolvedOptions.onSortChange;

    function updateIndicators() {
        const indicators = table.querySelectorAll('[data-sort-indicator]');
        indicators.forEach(indicator => {
            const field = indicator.dataset.sortIndicator;
            if (field === sortBy) {
                indicator.textContent = sortDir === 'asc' ? '▲' : '▼';
            } else {
                indicator.textContent = '';
            }
        });
    }

    function setSort(field) {
        if (sortBy === field) {
            sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            sortBy = field;
            sortDir = 'asc';
        }

        updateIndicators();
        if (onSortChange) {
            onSortChange(sortBy, sortDir);
        }
    }

    const sortButtons = table.querySelectorAll('[data-sort-key]');
    sortButtons.forEach(button => {
        button.addEventListener('click', () => setSort(button.dataset.sortKey));
    });

    updateIndicators();
    return { getSort: () => ({ sortBy, sortDir }), setSort, updateIndicators };
}

// Handle 401 responses globally
document.addEventListener('htmx:responseError', function(event) {
    if (event.detail.xhr.status === 401) {
        window.location.href = '/login';
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeModal();
    }
});

// Check authentication on protected pages
document.addEventListener('DOMContentLoaded', function() {
    const isLoginPage = window.location.pathname === '/login';

    if (!isLoginPage) {
        fetch('/api/v1/auth/me')
            .then(response => {
                if (!response.ok) {
                    window.location.href = '/login';
                }
            })
            .catch(() => {
                window.location.href = '/login';
            });
    }
});
