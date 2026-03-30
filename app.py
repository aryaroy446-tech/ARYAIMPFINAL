// Navigation Active State Handled Server-Side via HTML pages

// === Global Variables & Setup ===
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
// IMPORTANT: Paste your Render.com / PythonAnywhere LIVE URLs here before launching to Netlify!
const LIVE_BACKEND_URL = 'https://your-live-backend-api.onrender.com';
const API_BASE_URL = IS_LOCAL ? 'http://localhost:5001' : LIVE_BACKEND_URL;

// Authentication Check: Redirect unauthenticated users
if (!window.location.pathname.endsWith('/auth.html') && !localStorage.getItem('medicineGuardSession')) {
    window.location.href = '/auth.html';
}

function logout() {
    localStorage.removeItem('medicineGuardSession');
    sessionStorage.removeItem('medicineGuardSessionReport');
    window.location.href = '/auth.html';
}

// === Scanner Page Logic ===
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadForm = document.getElementById('uploadForm');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
const imagePreview = document.getElementById('imagePreview');
const scanBtn = document.getElementById('scanBtn');

// UI Elements for Scanner Results
const resultsPlaceholder = document.getElementById('resultsPlaceholder');
const loader = document.getElementById('loader');
const scanResults = document.getElementById('scanResults');
const scoreCircle = document.getElementById('scoreCircle');
const scoreValue = document.getElementById('scoreValue');
const riskLevel = document.getElementById('riskLevel');
const detailPackaging = document.getElementById('detailPackaging');
const detailBrand = document.getElementById('detailBrand');
const detailSafety = document.getElementById('detailSafety');
const infoCompany = document.getElementById('infoCompany');
const infoUsage = document.getElementById('infoUsage');
const infoStorage = document.getElementById('infoStorage');

if (dropZone && fileInput) {
    // Drag & Drop Events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (!file.type.startsWith('image/')) {
                alert('Please upload an image file.');
                return;
            }

            // Preview Image
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onloadend = () => {
                imagePreview.src = reader.result;
                imagePreviewContainer.style.display = 'block';
                scanBtn.style.display = 'flex';
                
                // Hide results if showing
                resetResultsView();
            };
            
            // Re-assign to file input if coming from drag
            if(fileInput.files !== files) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
            }
        }
    }

    // Process Form Submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;

        // UI State: Loading
        resultsPlaceholder.style.display = 'none';
        scanResults.style.display = 'none';
        loader.style.display = 'flex';
        scanBtn.disabled = true;

        const formData = new FormData();
        formData.append('medicineImage', file);

        try {
            const response = await fetch(`${API_BASE_URL}/api/scan`, {
                method: 'POST',
                body: formData
            });
            const resData = await response.json();

            if (resData.success) {
                displayResults(resData.data.result);
            } else {
                alert(resData.error || 'Failed to scan image.');
                resetResultsView();
            }
        } catch (error) {
            console.error('Scan Error:', error);
            alert('A server error occurred during analysis.');
            resetResultsView();
        } finally {
            scanBtn.disabled = false;
            loader.style.display = 'none';
        }
    });
}

function clearImage(e) {
    e.stopPropagation();
    fileInput.value = '';
    imagePreview.src = '';
    imagePreviewContainer.style.display = 'none';
    scanBtn.style.display = 'none';
    resetResultsView();
}

function resetResultsView() {
    resultsPlaceholder.style.display = 'block';
    loader.style.display = 'none';
    scanResults.style.display = 'none';
}

function displayResults(data) {
    // Populate Results
    scoreValue.innerText = `${data.score}%`;
    scoreCircle.style.setProperty('--score', data.score);
    
    // Set appropriate Class
    scoreCircle.className = `score-circle risk-${data.riskLevel}`;
    riskLevel.className = `badge badge-${data.riskLevel}`;
    riskLevel.innerText = data.riskLevel;

    detailPackaging.innerText = data.details.packagingQuality;
    detailBrand.innerText = data.details.brandAuthenticity;
    detailSafety.innerText = data.details.safetyMarkers;
    
    // New Medicine Info section
    if (data.medicineInfo) {
        infoCompany.innerText = data.medicineInfo.companyName || 'Not Detected';
        infoUsage.innerText = data.medicineInfo.usage || 'Not Detected';
        infoStorage.innerText = data.medicineInfo.storageInstructions || 'Not Detected';
    } else {
        infoCompany.innerText = 'Analysis Failed';
        infoUsage.innerText = 'Analysis Failed';
        infoStorage.innerText = 'Analysis Failed';
    }

    // Record to Session PDF Logger
    recordSessionAction('Image Scan', 'Analyzed Medicine Image', data.riskLevel + ' Risk Level (' + data.score + '%)');

    scanResults.style.display = 'block';
}

// === History Page Logic ===
const historyGrid = document.getElementById('historyGrid');
const historyLoader = document.getElementById('historyLoader');
const noHistory = document.getElementById('noHistory');

if (historyGrid) {
    fetchHistory();
}

async function fetchHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/history`);
        const resData = await response.json();

        historyLoader.style.display = 'none';

        if (resData.success && resData.data.length > 0) {
            renderHistory(resData.data);
            historyGrid.style.display = 'grid';
        } else {
            noHistory.style.display = 'block';
        }
    } catch (error) {
        console.error('Error fetching history:', error);
        historyLoader.style.display = 'none';
        noHistory.style.display = 'block';
    }
}

function renderHistory(records) {
    historyGrid.innerHTML = '';
    records.forEach(record => {
        const dateObj = new Date(record.date);
        const formattedDate = dateObj.toLocaleDateString() + ' at ' + dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const score = record.result.score;
        const riskLevel = record.result.riskLevel;
        
        const isAuthentic = riskLevel === 'Low';
        const colorAccent = riskLevel === 'High' ? 'var(--primary)' : (riskLevel === 'Medium' ? '#f59e0b' : '#10b981');

        const card = document.createElement('div');
        card.className = 'history-card';
        card.innerHTML = `
            <div class="history-header">
                <span>${record.filename}</span>
                <span>
                    ${formattedDate} 
                    <button onclick="deleteScan('${record.id}')" style="background: none; border: none; color: #ef4444; cursor: pointer; margin-left: 10px;" title="Delete this result">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </span>
            </div>
            <div class="history-score" style="color: ${colorAccent};">
                ${score}% <span class="badge badge-${riskLevel}">${riskLevel} Risk</span>
            </div>
            <div style="font-size: 0.9rem; color: var(--text-muted);">
                <i class="fa-solid ${isAuthentic ? 'fa-circle-check text-green' : 'fa-triangle-exclamation text-red'}"></i>
                ${isAuthentic ? 'Likely Authentic' : 'Suspicious Elements Detected'}
            </div>
        `;
        historyGrid.appendChild(card);
    });
}

// History Deletion Functions
async function deleteScan(id) {
    if (!confirm('Are you sure you want to delete this scan result?')) return;
    try {
        await fetch(`${API_BASE_URL}/api/history/${id}`, { method: 'DELETE' });
        fetchHistory(); // Refresh the list
    } catch (error) {
        console.error('Error deleting scan:', error);
        alert('Failed to delete the result.');
    }
}

async function clearAllHistory() {
    if (!confirm('Are you absolutely sure you want to clear your entire scan history? This cannot be undone.')) return;
    try {
        await fetch(`${API_BASE_URL}/api/history`, { method: 'DELETE' });
        fetchHistory(); // Refresh the list
    } catch (error) {
        console.error('Error clearing history:', error);
        alert('Failed to clear history.');
    }
}

// === Database Page Logic ===
async function searchMedicine(e) {
    e.preventDefault();
    const input = document.getElementById('searchInput').value.trim();
    if (!input) return;

    // UI State: Loading
    document.getElementById('dbStateEmpty').style.display = 'none';
    document.getElementById('dbResults').style.display = 'none';
    const loader = document.getElementById('dbLoader');
    if (loader) loader.style.display = 'flex';

    try {
        const response = await fetch(`${API_BASE_URL}/api/database?q=${encodeURIComponent(input)}`);
        const resData = await response.json();

        if (loader) loader.style.display = 'none';

        if (resData.success) {
            document.getElementById('dbTitle').innerText = input.toUpperCase();
            document.getElementById('dbCompany').innerText = resData.data.companyName || 'Not available';
            document.getElementById('dbUses').innerText = resData.data.primaryUses || 'Not available';
            document.getElementById('dbIngredients').innerText = resData.data.activeIngredients || 'Not available';
            document.getElementById('dbSideEffects').innerText = resData.data.sideEffects || 'Not available';
            document.getElementById('dbStorage').innerText = resData.data.storageInstructions || 'Not available';
            
            // Record to Session PDF Logger
            recordSessionAction('Database Search', input, resData.data.companyName || 'Successfully Retrieved Info');

            document.getElementById('dbResults').style.display = 'block';
        } else {
            alert(resData.error || 'Failed to retrieve medicine data.');
            document.getElementById('dbStateEmpty').style.display = 'block';
        }
    } catch (error) {
        console.error('Search Error:', error);
        if (loader) loader.style.display = 'none';
        alert('A server error occurred during database lookup.');
        document.getElementById('dbStateEmpty').style.display = 'block';
    }
}

// === Help Triage Page Logic ===
async function analyzeSymptoms(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('symptomsInput').value.trim();
    if (!input) return;

    // UI Loading state
    document.getElementById('helpResults').style.display = 'none';
    const loader = document.getElementById('helpLoader');
    if (loader) loader.style.display = 'flex';
    
    // Disable button to prevent double-calls
    const btn = document.getElementById('analyzeBtn');
    if (btn) btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/api/help?symptoms=${encodeURIComponent(input)}`);
        const resData = await response.json();

        if (loader) loader.style.display = 'none';
        if (btn) btn.disabled = false;

        if (resData.success) {
            const data = resData.data;
            
            // Set Badge
            const badge = document.getElementById('riskBadge');
            badge.className = 'risk-badge';
            badge.innerText = data.riskLevel + ' Risk';
            
            if (data.riskLevel === 'High') {
                badge.classList.add('risk-high');
                document.getElementById('urgentAlertBox').style.display = 'block';
                document.getElementById('resultCard').style.borderColor = '#ef4444';
            } else if (data.riskLevel === 'Medium') {
                badge.classList.add('risk-medium');
                document.getElementById('urgentAlertBox').style.display = 'none';
                document.getElementById('resultCard').style.borderColor = '#eab308';
            } else {
                badge.classList.add('risk-low');
                document.getElementById('urgentAlertBox').style.display = 'none';
                document.getElementById('resultCard').style.borderColor = '#22c55e';
            }

            // Set Advice
            document.getElementById('helpAdvice').innerText = data.advice || "No specific advice provided.";

            // Render Suggested Medicines
            const medContainer = document.getElementById('helpMedicinesContainer');
            const medSection = document.getElementById('medicationSection');
            medContainer.innerHTML = '';
            
            if (data.suggestedMedicines && data.suggestedMedicines.length > 0) {
                medSection.style.display = 'block';
                data.suggestedMedicines.forEach(med => {
                    const tag = document.createElement('span');
                    tag.className = 'medicine-tag';
                    tag.innerText = med;
                    medContainer.appendChild(tag);
                });
            } else {
                medSection.style.display = 'none'; // High risk usually means 0 suggestions
            }

            // Record to Session PDF Logger
            recordSessionAction('Symptom Triage', input, data.riskLevel + ' Risk Identified');

            document.getElementById('helpResults').style.display = 'block';
        } else {
            alert(resData.error || 'Failed to analyze symptoms.');
        }
    } catch (error) {
        console.error('Triage Error:', error);
        if (loader) loader.style.display = 'none';
        if (btn) btn.disabled = false;
        alert('A server error occurred during symptom triage.');
    }
}

// === Session PDF Report Engine ===
function recordSessionAction(type, query, result) {
    let sessionSearches = JSON.parse(sessionStorage.getItem('medicineGuardSessionReport')) || [];
    sessionSearches.push({
        time: new Date().toLocaleTimeString(),
        type: type,
        query: query,
        result: result
    });
    sessionStorage.setItem('medicineGuardSessionReport', JSON.stringify(sessionSearches));
}

function generatePDFReport() {
    let sessionSearches = JSON.parse(sessionStorage.getItem('medicineGuardSessionReport')) || [];
    let printWindow = window.open('', '_blank');
    
    let htmlContent = `
    <html>
    <head>
        <title>MedicineGuard AI - Session Report</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; color: #333; }
            h1 { color: #1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f8fafc; color: #0f172a; }
            .timestamp { color: #64748b; font-size: 0.9em; }
            .no-data { margin-top: 20px; font-style: italic; color: #64748b; }
        </style>
    </head>
    <body>
        <h1>MedicineGuard AI - Session Tracking Report</h1>
        <p>Generated on: ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}</p>
    `;

    if (sessionSearches.length === 0) {
        htmlContent += `<p class="no-data">No searches or scans were performed during this active session.</p>`;
    } else {
        htmlContent += `
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Action Type</th>
                    <th>Input / Query</th>
                    <th>AI Result / Insight</th>
                </tr>
            </thead>
            <tbody>
        `;
        sessionSearches.forEach(item => {
            htmlContent += `
                <tr>
                    <td class="timestamp">${item.time}</td>
                    <td><strong>${item.type}</strong></td>
                    <td>${item.query}</td>
                    <td>${item.result}</td>
                </tr>
            `;
        });
        htmlContent += `
            </tbody>
        </table>
        `;
    }

    htmlContent += `
    </body>
    </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
    
    // Allow rendering before print trigger
    setTimeout(() => {
        printWindow.focus();
        printWindow.print();
    }, 250);
}


