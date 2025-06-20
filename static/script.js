// Zambia Data Collection Tool - Frontend JavaScript

// Global variables
let currentData = null;
let currentMetadata = null;
let allSourcesData = {};
let currentChart = null;

// DOM elements
const dataForm = document.getElementById('dataForm');
const dataSource = document.getElementById('dataSource');
const dataType = document.getElementById('dataType');
const fetchBtn = document.getElementById('fetchBtn');
const downloadBtn = document.getElementById('downloadBtn');
const emailBtn = document.getElementById('emailBtn');
const visualizeBtn = document.getElementById('visualizeBtn');
const compareBtn = document.getElementById('compareBtn');
const bulkFetchBtn = document.getElementById('bulkFetchBtn');

// Advanced options
const startYear = document.getElementById('startYear');
const endYear = document.getElementById('endYear');
const compareMultipleSources = document.getElementById('compareMultipleSources');
const dataFormat = document.getElementById('dataFormat');

// State elements
const loadingState = document.getElementById('loadingState');
const emptyState = document.getElementById('emptyState');
const errorState = document.getElementById('errorState');
const resultsContainer = document.getElementById('resultsContainer');

// Results elements
const statusBadge = document.getElementById('statusBadge');
const recordCount = document.getElementById('recordCount');
const dataSourceInfo = document.getElementById('dataSourceInfo');
const dateRangeInfo = document.getElementById('dateRangeInfo');
const lastFetchTime = document.getElementById('lastFetchTime');
const tableHeaders = document.getElementById('tableHeaders');
const tableBody = document.getElementById('tableBody');
const lastUpdated = document.getElementById('lastUpdated');

// View elements
const tableView = document.getElementById('tableView');
const chartView = document.getElementById('chartView');
const summaryView = document.getElementById('summaryView');
const tableViewContainer = document.getElementById('tableViewContainer');
const chartViewContainer = document.getElementById('chartViewContainer');
const summaryViewContainer = document.getElementById('summaryViewContainer');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Set up event listeners with null checks
    if (dataForm) dataForm.addEventListener('submit', handleFetchData);
    if (downloadBtn) downloadBtn.addEventListener('click', handleDownloadExcel);
    if (emailBtn) emailBtn.addEventListener('click', handleSendEmail);
    if (visualizeBtn) visualizeBtn.addEventListener('click', handleVisualize);
    if (compareBtn) compareBtn.addEventListener('click', handleCompare);
    if (bulkFetchBtn) bulkFetchBtn.addEventListener('click', handleBulkFetch);
    
    // View mode listeners with null checks
    if (tableView) tableView.addEventListener('change', () => switchView('table'));
    if (chartView) chartView.addEventListener('change', () => switchView('chart'));
    if (summaryView) summaryView.addEventListener('change', () => switchView('summary'));
    
    // Update last updated time
    updateLastUpdatedTime();
    
    // Show initial empty state
    showEmptyState();
    
    console.log('Zambia Data Collection Tool initialized');
}

function updateLastUpdatedTime() {
    const now = new Date();
    lastUpdated.textContent = now.toLocaleString();
}

// Handle data fetching
async function handleFetchData(event) {
    event.preventDefault();
    
    const source = dataSource.value;
    const type = dataType.value;
    
    if (!source || !type) {
        showError('Please select both a data source and data type');
        return;
    }
    
    try {
        showLoadingState(getSourceDisplayName(source));
        
        const response = await fetch('/api/fetch_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                source: source,
                data_type: type
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentData = data.data;
            currentMetadata = data.metadata;
            showResults(data.data, data.metadata, source, type);
            updateLastUpdatedTime();
        } else {
            showError(data.error || 'Failed to fetch data');
        }
        
    } catch (error) {
        console.error('Fetch error:', error);
        showError('Network error: Unable to connect to the server');
    }
}

// Handle Excel download
async function handleDownloadExcel() {
    if (!currentData || currentData.length === 0) {
        showError('No data available for download');
        return;
    }
    
    try {
        const formatElement = document.getElementById('dataFormat');
        const selectedFormat = formatElement ? formatElement.value : 'excel';
        
        // Disable download button temporarily
        downloadBtn.disabled = true;
        const formatText = selectedFormat === 'csv' ? 'CSV' : selectedFormat === 'json' ? 'JSON' : 'Excel';
        downloadBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>Generating ${formatText}...`;
        
        const response = await fetch('/download_excel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                data: currentData,
                source: dataSource ? getSourceDisplayName(dataSource.value) : 'Multiple Sources',
                data_type: dataType ? dataType.value : 'Various',
                format: selectedFormat
            })
        });
        
        if (response.ok) {
            // Create download link
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            
            // Get filename from response headers or create default
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'zambia_data.xlsx';
            if (contentDisposition) {
                const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (matches && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }
            
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            // Show success message based on format
            const formatText = selectedFormat === 'csv' ? 'CSV file' : selectedFormat === 'json' ? 'JSON file' : 'Excel file';
            showSuccessMessage(`${formatText} downloaded successfully!`);
            
        } else {
            const errorData = await response.json();
            showError(errorData.error || 'Failed to generate Excel file');
        }
        
    } catch (error) {
        console.error('Download error:', error);
        showError('Failed to download Excel file');
    } finally {
        // Re-enable download button
        downloadBtn.disabled = false;
        const formatElement = document.getElementById('dataFormat');
        const selectedFormat = formatElement ? formatElement.value : 'excel';
        const iconClass = selectedFormat === 'csv' ? 'fas fa-file-csv' : selectedFormat === 'json' ? 'fas fa-file-code' : 'fas fa-file-excel';
        const formatText = selectedFormat === 'csv' ? 'CSV' : selectedFormat === 'json' ? 'JSON' : 'Excel';
        downloadBtn.innerHTML = `<i class="${iconClass} me-2"></i>Download ${formatText}`;
    }
}

// Handle email sending
async function handleSendEmail() {
    if (!currentData || currentData.length === 0) {
        showError('No data available to send');
        return;
    }
    
    const emailAddress = document.getElementById('emailAddress').value.trim();
    if (!emailAddress) {
        showError('Please enter an email address in Advanced Options');
        return;
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailAddress)) {
        showError('Please enter a valid email address');
        return;
    }
    
    try {
        const formatElement = document.getElementById('dataFormat');
        const selectedFormat = formatElement ? formatElement.value : 'csv';
        
        // Disable email button temporarily
        emailBtn.disabled = true;
        emailBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending Email...';
        
        const response = await fetch('/send_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: emailAddress,
                data: currentData,
                source: dataSource ? getSourceDisplayName(dataSource.value) : 'Multiple Sources',
                data_type: dataType ? dataType.value : 'Various',
                format: selectedFormat
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            showSuccessMessage(`Report sent successfully to ${emailAddress}`);
        } else {
            showError(result.error || 'Failed to send email');
        }
        
    } catch (error) {
        console.error('Email sending error:', error);
        showError('Failed to send email. Please check your connection.');
    } finally {
        // Re-enable email button
        emailBtn.disabled = false;
        emailBtn.innerHTML = '<i class="fas fa-envelope me-2"></i>Send Email';
    }
}

// State management functions
function showEmptyState() {
    hideAllStates();
    emptyState.style.display = 'block';
    downloadBtn.disabled = true;
    emailBtn.disabled = true;
    statusBadge.innerHTML = '';
}

function showLoadingState(sourceName) {
    hideAllStates();
    loadingState.style.display = 'block';
    document.getElementById('loadingSource').textContent = sourceName;
    downloadBtn.disabled = true;
    emailBtn.disabled = true;
    
    statusBadge.innerHTML = '<span class="badge bg-warning status-loading"><i class="fas fa-spinner fa-spin me-1"></i>Loading</span>';
}

function showError(message) {
    hideAllStates();
    errorState.style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
    downloadBtn.disabled = true;
    emailBtn.disabled = true;
    
    statusBadge.innerHTML = '<span class="badge bg-danger status-error"><i class="fas fa-exclamation-triangle me-1"></i>Error</span>';
}

function showResults(data, metadata, source, type) {
    hideAllStates();
    resultsContainer.style.display = 'block';
    
    // Update metadata display
    recordCount.textContent = data.length.toLocaleString();
    dataSourceInfo.textContent = getSourceDisplayName(source);
    
    // Update date range info
    const years = extractYears(data);
    if (years.length > 0) {
        dateRangeInfo.textContent = `${Math.min(...years)} - ${Math.max(...years)}`;
    } else {
        dateRangeInfo.textContent = 'Various dates';
    }
    
    // Update last fetch time
    lastFetchTime.textContent = new Date().toLocaleTimeString();
    
    // Create table
    createResultsTable(data);
    
    // Enable action buttons
    downloadBtn.disabled = false;
    emailBtn.disabled = false;
    visualizeBtn.disabled = false;
    compareBtn.disabled = false;
    
    // Store data for comparison
    allSourcesData[source] = { data, metadata, type };
    
    // Update status badge
    statusBadge.innerHTML = `<span class="badge bg-success status-success"><i class="fas fa-check me-1"></i>Success</span>`;
    
    // Initialize chart if chart view is selected
    if (chartView.checked) {
        switchView('chart');
    } else if (summaryView.checked) {
        switchView('summary');
    }
}

function hideAllStates() {
    emptyState.style.display = 'none';
    loadingState.style.display = 'none';
    errorState.style.display = 'none';
    resultsContainer.style.display = 'none';
}

// Table creation functions
function createResultsTable(data) {
    if (!data || data.length === 0) {
        showError('No data received from the source');
        return;
    }
    
    // Get all unique keys from the data
    const allKeys = new Set();
    data.forEach(row => {
        Object.keys(row).forEach(key => allKeys.add(key));
    });
    
    const headers = Array.from(allKeys);
    
    // Create table headers
    tableHeaders.innerHTML = '';
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = formatHeaderName(header);
        th.scope = 'col';
        tableHeaders.appendChild(th);
    });
    
    // Create table body
    tableBody.innerHTML = '';
    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        
        headers.forEach(header => {
            const td = document.createElement('td');
            const value = row[header];
            td.textContent = formatCellValue(value);
            
            // Add specific styling for certain data types
            if (header.toLowerCase().includes('value') && !isNaN(value)) {
                td.classList.add('text-end', 'font-monospace');
            }
            
            tr.appendChild(td);
        });
        
        tableBody.appendChild(tr);
    });
}

// Utility functions
function getSourceDisplayName(source) {
    const sourceNames = {
        'world_bank': 'World Bank',
        'imf': 'International Monetary Fund',
        'usaid': 'USAID',
        'un': 'UN Agencies',
        'afdb': 'African Development Bank',
        'zambian_stats': 'Zambian Statistics Office'
    };
    return sourceNames[source] || source;
}

function formatHeaderName(header) {
    return header.split('_')
                 .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                 .join(' ');
}

function formatCellValue(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    
    if (typeof value === 'number') {
        // Format large numbers with commas
        if (value >= 1000) {
            return value.toLocaleString();
        }
        // Format decimals to 2 places if they have decimals
        if (value % 1 !== 0) {
            return value.toFixed(2);
        }
    }
    
    return String(value);
}

function showSuccessMessage(message) {
    // Create temporary success alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.marginTop = '20px';
    alertDiv.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 3000);
}

function clearResults() {
    currentData = null;
    currentMetadata = null;
    showEmptyState();
}

// Form validation
dataSource.addEventListener('change', function() {
    validateForm();
});

dataType.addEventListener('change', function() {
    validateForm();
});

function validateForm() {
    const isValid = dataSource.value && dataType.value;
    fetchBtn.disabled = !isValid;
    
    if (isValid) {
        fetchBtn.classList.remove('btn-secondary');
        fetchBtn.classList.add('btn-primary');
    } else {
        fetchBtn.classList.remove('btn-primary');
        fetchBtn.classList.add('btn-secondary');
    }
}

// Initialize form validation
validateForm();

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + Enter to fetch data
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        if (!fetchBtn.disabled) {
            handleFetchData(event);
        }
    }
    
    // Ctrl/Cmd + D to download (if data available)
    if ((event.ctrlKey || event.metaKey) && event.key === 'd') {
        event.preventDefault();
        if (!downloadBtn.disabled) {
            handleDownloadExcel();
        }
    }
});

// Add tooltips for better UX
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips if available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// Advanced functionality implementations

// Handle data visualization
async function handleVisualize() {
    if (!currentData || currentData.length === 0) {
        showError('No data available for visualization');
        return;
    }
    
    chartView.checked = true;
    switchView('chart');
}

// Handle data comparison
async function handleCompare() {
    if (Object.keys(allSourcesData).length < 2) {
        showError('Need data from at least 2 sources for comparison');
        return;
    }
    
    // Create comparison view
    createComparisonView();
}

// Handle bulk data fetching
async function handleBulkFetch() {
    const type = dataType.value;
    if (!type) {
        showError('Please select a data type first');
        return;
    }
    
    const sources = ['world_bank', 'imf', 'usaid', 'un', 'afdb', 'zambian_stats'];
    bulkFetchBtn.disabled = true;
    bulkFetchBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Fetching from all sources...';
    
    let successCount = 0;
    
    for (const source of sources) {
        try {
            const response = await fetch('/api/fetch_data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({source, data_type: type})
            });
            
            const data = await response.json();
            if (data.success) {
                allSourcesData[source] = {
                    data: data.data,
                    metadata: data.metadata,
                    type: type
                };
                successCount++;
            }
        } catch (error) {
            console.warn(`Failed to fetch from ${source}:`, error);
        }
    }
    
    bulkFetchBtn.disabled = false;
    bulkFetchBtn.innerHTML = '<i class="fas fa-layer-group me-2"></i>Fetch All Sources';
    
    if (successCount > 0) {
        showSuccessMessage(`Successfully fetched data from ${successCount} sources`);
        
        // Combine all data for display
        let combinedData = [];
        let totalRecords = 0;
        
        Object.entries(allSourcesData).forEach(([source, sourceData]) => {
            sourceData.data.forEach(record => {
                combinedData.push({
                    ...record,
                    Data_Source: getSourceDisplayName(source)
                });
            });
            totalRecords += sourceData.data.length;
        });
        
        // Update current data for display and download
        currentData = combinedData;
        currentMetadata = {
            sources: Object.keys(allSourcesData),
            total_records: totalRecords,
            fetch_time: new Date().toISOString()
        };
        
        // Show results in comparison view
        createComparisonView();
        compareBtn.disabled = false;
        
        // Enable other buttons
        downloadBtn.disabled = false;
        emailBtn.disabled = false;
        visualizeBtn.disabled = false;
        
        // Update summary display
        recordCount.textContent = totalRecords.toLocaleString();
        dataSourceInfo.textContent = `${successCount} sources combined`;
        lastFetchTime.textContent = new Date().toLocaleTimeString();
        
        // Show results container
        hideAllStates();
        resultsContainer.style.display = 'block';
        statusBadge.innerHTML = `<span class="badge bg-success status-success"><i class="fas fa-check me-1"></i>Bulk Fetch Complete</span>`;
        
        // Create table view with combined data
        createResultsTable(combinedData);
        
        // Switch to table view by default
        tableView.checked = true;
        switchView('table');
        
    } else {
        showError('Failed to fetch data from any source');
    }
}

// Switch between different view modes
function switchView(mode) {
    tableViewContainer.style.display = mode === 'table' ? 'block' : 'none';
    chartViewContainer.style.display = mode === 'chart' ? 'block' : 'none';
    summaryViewContainer.style.display = mode === 'summary' ? 'block' : 'none';
    
    if (mode === 'chart' && currentData) {
        createChart(currentData);
    } else if (mode === 'summary' && currentData) {
        createSummaryView(currentData);
    }
}

// Create data visualization chart
function createChart(data) {
    const canvas = document.getElementById('dataChart');
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart
    if (currentChart) {
        currentChart.destroy();
    }
    
    // Prepare chart data
    const chartData = prepareChartData(data);
    
    currentChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Zambia ${dataType.value.charAt(0).toUpperCase() + dataType.value.slice(1)} Data`
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Year'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Value'
                    }
                }
            }
        }
    });
}

// Prepare data for chart visualization
function prepareChartData(data) {
    const datasets = {};
    const labels = new Set();
    
    data.forEach(row => {
        const year = extractYear(row);
        const value = extractNumericValue(row);
        const indicator = row.Indicator || row.indicator || 'Data';
        
        if (year && value !== null) {
            labels.add(year);
            
            if (!datasets[indicator]) {
                datasets[indicator] = {
                    label: indicator,
                    data: [],
                    borderColor: getRandomColor(),
                    backgroundColor: getRandomColor(0.2),
                    fill: false
                };
            }
            
            datasets[indicator].data.push({x: year, y: value});
        }
    });
    
    return {
        labels: Array.from(labels).sort(),
        datasets: Object.values(datasets)
    };
}

// Create summary view with key statistics
function createSummaryView(data) {
    const container = document.getElementById('summaryCards');
    container.innerHTML = '';
    
    const summary = generateDataSummary(data);
    
    Object.entries(summary).forEach(([key, value]) => {
        const cardHtml = `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${formatHeaderName(key)}</h5>
                        <p class="card-text display-6">${value}</p>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += cardHtml;
    });
}

// Create comparison view for multiple data sources
function createComparisonView() {
    const container = document.getElementById('summaryCards');
    container.innerHTML = '';
    
    // Switch to summary view
    summaryView.checked = true;
    switchView('summary');
    
    Object.entries(allSourcesData).forEach(([source, sourceData]) => {
        const summary = generateDataSummary(sourceData.data);
        const recordCount = sourceData.data.length;
        
        const cardHtml = `
            <div class="col-lg-6 mb-3">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="card-title mb-0">${getSourceDisplayName(source)}</h5>
                        <small class="text-muted">${recordCount} records</small>
                    </div>
                    <div class="card-body">
                        ${Object.entries(summary).slice(0, 4).map(([key, value]) => 
                            `<div class="d-flex justify-content-between mb-2">
                                <span>${formatHeaderName(key)}:</span>
                                <strong>${value}</strong>
                            </div>`
                        ).join('')}
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += cardHtml;
    });
}

// Utility functions for data processing
function extractYears(data) {
    const years = [];
    data.forEach(row => {
        const year = extractYear(row);
        if (year) years.push(year);
    });
    return years;
}

function extractYear(row) {
    const yearFields = ['Year', 'year', 'Date', 'date'];
    for (const field of yearFields) {
        if (row[field]) {
            const match = String(row[field]).match(/\d{4}/);
            if (match) return parseInt(match[0]);
        }
    }
    return null;
}

function extractNumericValue(row) {
    const valueFields = ['Value', 'value', 'Amount', 'amount'];
    for (const field of valueFields) {
        if (row[field]) {
            const numericMatch = String(row[field]).match(/[\d,]+\.?\d*/);
            if (numericMatch) {
                return parseFloat(numericMatch[0].replace(/,/g, ''));
            }
        }
    }
    return null;
}

function generateDataSummary(data) {
    const summary = {
        total_records: data.length,
        unique_indicators: new Set(data.map(row => row.Indicator || row.indicator || 'N/A')).size,
        date_range: 'N/A',
        latest_year: 'N/A'
    };
    
    const years = extractYears(data);
    if (years.length > 0) {
        summary.date_range = `${Math.min(...years)} - ${Math.max(...years)}`;
        summary.latest_year = Math.max(...years);
    }
    
    // Add specific summary based on data type
    const numericValues = data.map(row => extractNumericValue(row)).filter(v => v !== null);
    if (numericValues.length > 0) {
        summary.average_value = (numericValues.reduce((a, b) => a + b, 0) / numericValues.length).toFixed(2);
        summary.max_value = Math.max(...numericValues).toLocaleString();
        summary.min_value = Math.min(...numericValues).toLocaleString();
    }
    
    return summary;
}

function getRandomColor(alpha = 1) {
    const colors = [
        `rgba(255, 99, 132, ${alpha})`,
        `rgba(54, 162, 235, ${alpha})`,
        `rgba(255, 205, 86, ${alpha})`,
        `rgba(75, 192, 192, ${alpha})`,
        `rgba(153, 102, 255, ${alpha})`,
        `rgba(255, 159, 64, ${alpha})`
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

console.log('Zambia Data Collection Tool frontend initialized successfully');
