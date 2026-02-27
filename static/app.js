document.addEventListener('DOMContentLoaded', () => {
    fetchData();

    // Event listener for search with a small debounce for smoothness
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filterTable(e.target.value.trim().toLowerCase());
        }, 300);
    });

    // Toggle Tabs
    const tabCIUU = document.getElementById('tabCIUU');
    const tabNIT = document.getElementById('tabNIT');
    const ciuuSection = document.getElementById('ciuuSearch');
    const nitSection = document.getElementById('nitSearch');
    const demoNotice = document.getElementById('demoNotice');

    tabCIUU.addEventListener('click', () => {
        tabCIUU.classList.add('active');
        tabNIT.classList.remove('active');
        ciuuSection.style.display = 'block';
        nitSection.style.display = 'none';
    });

    tabNIT.addEventListener('click', () => {
        tabNIT.classList.add('active');
        tabCIUU.classList.remove('active');
        nitSection.style.display = 'block';
        ciuuSection.style.display = 'none';

        // Show demo notice if on Render
        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            demoNotice.style.display = 'block';
        }
    });
});

let allData = [];

// ... [Keep existing functions: fetchData, renderTable, filterTable, updateRowCount, escapeHtml] ...

async function searchByNIT() {
    const nitInput = document.getElementById('nitInput');
    const nit = nitInput.value.trim();
    const modal = document.getElementById('nitModal');
    const modalBody = document.getElementById('modalBody');

    if (!nit) return;

    modalBody.innerHTML = '<div style="text-align:center; padding: 2rem;"><p>Consultando APIM...</p><div class="pulse-dot" style="margin: 1rem auto;"></div></div>';
    modal.style.display = 'flex';

    try {
        const response = await fetch(`/api/client/${encodeURIComponent(nit)}`);
        const result = await response.json();

        if (result.status === 'success') {
            const d = result.data;
            let sourceLabel = result.source.includes('demo') ? '<span style="color:var(--warning); font-size: 0.7rem; display:block; margin-bottom: 0.5rem;">[DEMO - SIMULACIÓN]</span>' : '';

            modalBody.innerHTML = `
                ${sourceLabel}
                <div class="detail-item"><span class="detail-label">NIT</span><span class="detail-val">${escapeHtml(d.nit)}</span></div>
                <div class="detail-item"><span class="detail-label">Razón Social</span><span class="detail-val">${escapeHtml(d.nombre)}</span></div>
                <div class="detail-item"><span class="detail-label">Estado</span><span class="detail-val" style="color:var(--success)">${escapeHtml(d.estado)}</span></div>
                <div class="detail-item"><span class="detail-label">Segmento</span><span class="detail-val">${escapeHtml(d.segmento)}</span></div>
                <div class="detail-item"><span class="detail-label">Dirección</span><span class="detail-val">${escapeHtml(d.direccion)}</span></div>
                <div class="detail-item"><span class="detail-label">Vinculación</span><span class="detail-val">${escapeHtml(d.fecha_vinculacion)}</span></div>
            `;
        } else if (result.status === 'not_found') {
            modalBody.innerHTML = `
                <div style="text-align:center; padding: 1rem;">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">❌</div>
                    <p style="font-weight:600;">NIT no encontrado</p>
                    <p style="color:var(--text-muted); font-size: 0.9rem;">${escapeHtml(result.message)}</p>
                </div>`;
        } else {
            modalBody.innerHTML = `
                <div style="text-align:center; color: var(--error); padding: 1rem;">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">⚠️</div>
                    <p style="font-weight:600;">Error en la API</p>
                    <p style="font-size: 0.8rem; margin-top: 0.5rem;">${escapeHtml(result.message)}</p>
                    <pre style="text-align:left; font-size: 0.7rem; background:#fee; padding: 1rem; margin-top: 1rem; border-radius: 8px; overflow-x: auto;">${escapeHtml(result.detail || '')}</pre>
                </div>`;
        }
    } catch (error) {
        modalBody.innerHTML = `<p style="color:var(--error)">Error de red al consultar el servidor.</p>`;
    }
}

function closeModal() {
    document.getElementById('nitModal').style.display = 'none';
}

async function fetchData() {
    const loader = document.getElementById('loader');
    const tableBody = document.getElementById('tableBody');
    const errorContainer = document.getElementById('errorContainer');
    const statusBadge = document.getElementById('statusBadge');
    const dataTable = document.getElementById('dataTable');
    const welcomeMessage = document.getElementById('welcomeMessage');

    // Reset state
    loader.style.display = 'block';
    errorContainer.style.display = 'none';
    tableBody.innerHTML = '';
    statusBadge.textContent = 'Conectando servicio...';
    statusBadge.classList.remove('success', 'error');
    dataTable.style.display = 'none';
    welcomeMessage.style.display = 'none';

    try {
        const response = await fetch('/api/data');
        if (!response.ok) {
            throw new Error(`Servidor APIM respondió con estado ${response.status}`);
        }

        const responseData = await response.json();
        const source = responseData.source || 'unknown';

        // Extract information from the expected path
        let data = [];
        if (responseData && responseData.data && Array.isArray(responseData.data.information)) {
            data = responseData.data.information;
        } else if (Array.isArray(responseData)) {
            data = responseData;
        } else {
            // Fallback for different response formats
            for (const key in responseData) {
                if (key !== "source" && Array.isArray(responseData[key])) {
                    data = responseData[key];
                    break;
                }
            }
        }

        if (!Array.isArray(data)) {
            throw new Error("El formato de respuesta de la API no es válido.");
        }

        allData = data;

        // Initialize UI after loading data
        loader.style.display = 'none';
        welcomeMessage.style.display = 'block';

        if (source === 'live') {
            statusBadge.innerHTML = '<span class="pulse-dot"></span> API en Vivo';
            statusBadge.classList.add('success');
        } else if (source === 'cache') {
            statusBadge.innerHTML = '⚠️ Modo Local (Datos de Respaldo)';
            statusBadge.classList.add('warning');
            statusBadge.style.background = 'rgba(255, 152, 0, 0.2)';
            statusBadge.style.color = '#ffb74d';
        } else {
            statusBadge.textContent = 'Servicio Activo';
            statusBadge.classList.add('success');
        }

    } catch (error) {
        console.error('Error fetching data:', error);
        loader.style.display = 'none';
        errorContainer.style.display = 'block';
        document.getElementById('errorMessage').textContent = error.message;

        statusBadge.textContent = 'Servicio Indisponible';
        statusBadge.classList.add('error');
        updateRowCount(0);
    }
}

function renderTable(dataArray) {
    const tableBody = document.getElementById('tableBody');
    const dataTable = document.getElementById('dataTable');
    const emptyState = document.getElementById('emptyState');

    tableBody.innerHTML = '';

    if (dataArray.length === 0) {
        emptyState.style.display = 'block';
        dataTable.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    dataTable.style.display = 'table';

    dataArray.forEach((item, index) => {
        const row = document.createElement('tr');
        row.style.animation = `fadeInUp 0.4s ease forwards ${index * 0.05}s`;
        row.innerHTML = `
            <td class="code-cell">${escapeHtml(item.dataField || '')}</td>
            <td class="desc-cell">${escapeHtml(item.descriptionField || '')}</td>
        `;
        tableBody.appendChild(row);
    });
}

function filterTable(searchTerm) {
    const dataTable = document.getElementById('dataTable');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const emptyState = document.getElementById('emptyState');

    if (!searchTerm) {
        dataTable.style.display = 'none';
        emptyState.style.display = 'none';
        welcomeMessage.style.display = 'block';
        updateRowCount(0, true);
        return;
    }

    welcomeMessage.style.display = 'none';

    const filteredData = allData.filter(item => {
        const code = (item.dataField || '').toLowerCase();
        const desc = (item.descriptionField || '').toLowerCase();
        return code.includes(searchTerm) || desc.includes(searchTerm);
    });

    renderTable(filteredData);
    updateRowCount(filteredData.length);
}

function updateRowCount(count, reset = false) {
    const rowCountElement = document.getElementById('rowCount');
    if (reset) {
        rowCountElement.textContent = 'Listo para buscar';
        return;
    }
    rowCountElement.textContent = `${count} resultado${count !== 1 ? 's' : ''} encontrado${count !== 1 ? 's' : ''}`;
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
