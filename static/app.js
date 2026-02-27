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
});

let allData = [];

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

        // Extract information from the expected path
        let data = [];
        if (responseData && responseData.data && Array.isArray(responseData.data.information)) {
            data = responseData.data.information;
        } else if (Array.isArray(responseData)) {
            data = responseData;
        } else {
            // Fallback for different response formats
            for (const key in responseData) {
                if (Array.isArray(responseData[key])) {
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
        statusBadge.textContent = 'Servicio Activo';
        statusBadge.classList.add('success');

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
