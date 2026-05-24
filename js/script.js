// State
let currentCode = '';
let currentLanguage = 'auto';

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // File upload handler
    document.getElementById('fileUpload').addEventListener('change', handleFileUpload);
    
    // Language selector
    document.getElementById('languageSelect').addEventListener('change', function(e) {
        currentLanguage = e.target.value;
    });
    
    // Code input with line numbers
    const textarea = document.getElementById('codeInput');
    textarea.addEventListener('input', updateLineNumbers);
    textarea.addEventListener('scroll', syncScroll);
    
    // Initial line numbers
    updateLineNumbers();
});

// Handle file upload
function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    document.getElementById('fileName').textContent = file.name;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('codeInput').value = e.target.result;
        currentCode = e.target.result;
        updateLineNumbers();
        
        // Detect language from extension
        const ext = file.name.split('.').pop().toLowerCase();
        const langMap = {
            'py': 'python',
            'js': 'javascript',
            'java': 'java',
            'cpp': 'cpp',
            'cxx': 'cpp',
            'cc': 'cpp',
            'cs': 'csharp'
        };
        if (langMap[ext]) {
            document.getElementById('languageSelect').value = langMap[ext];
            currentLanguage = langMap[ext];
        }
    };
    reader.readAsText(file);
}

// Update line numbers
function updateLineNumbers() {

const textarea = document.getElementById('codeInput');
const lines = textarea.value.split('\n');
const lineCount = lines.length;

let lineNumbers = "";

for (let i = 1; i <= lineCount; i++) {
    lineNumbers += i + "<br>";
}

document.getElementById('lineNumbers').innerHTML = lineNumbers;

}

// Sync scroll
function syncScroll() {
    const textarea = document.getElementById('codeInput');
    document.getElementById('lineNumbers').scrollTop = textarea.scrollTop;
}

// Clear code
function clearCode() {
    document.getElementById('codeInput').value = '';
    document.getElementById('fileName').textContent = 'No file selected';
    document.getElementById('fileUpload').value = '';
    currentCode = '';
    updateLineNumbers();
    document.getElementById('results').classList.add('hidden');
}



// Analyze code
async function analyzeCode() {
    const code = document.getElementById('codeInput').value;
    
    if (!code.trim()) {
        alert('Please enter code to analyze');
        return;
    }
    
    // Show loading
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');
    document.getElementById('analyzeBtn').disabled = true;
    
    try {
        const response = await fetch('http://localhost:5000/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                language: currentLanguage
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            displayResults(data);
        }
    } catch (error) {
        alert('Failed to connect to server. Make sure the backend is running on port 5000');
        console.error(error);
    } finally {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('analyzeBtn').disabled = false;
    }
}

// Display results
function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    
    // Bug counts
    const counts = data.summary.bug_counts;
    
    // Risk class
    const riskClass = data.summary.risk_level.replace(' ', '-');
    
    // Build bugs HTML
    let bugsHtml = '';
    if (data.bugs && data.bugs.length > 0) {
        data.bugs.forEach(bug => {
            bugsHtml += `
                <div class="bug-item ${bug.severity}">
                    <div class="bug-header">
                        <span class="bug-type">${bug.type}</span>
                        <span class="bug-severity">${bug.severity}</span>
                    </div>
                    <div class="bug-line">Line ${bug.line}</div>
                    <div class="bug-message">${bug.message}</div>
                    <div class="bug-suggestion">${bug.suggestion}</div>
                </div>
            `;
        });
    } else {
        bugsHtml = '<p style="text-align: center; color: var(--success); padding: 2rem;">No bugs detected! Clean code </p>';
    }
    
    // Build suggestions HTML
    let suggestionsHtml = '';
    if (data.suggestions && data.suggestions.length > 0) {
        data.suggestions.forEach(suggestion => {
            suggestionsHtml += `<li>${suggestion}</li>`;
        });
    }
    
    // Build metrics HTML
    let metricsHtml = '';
    const metricItems = [
        { label: 'Lines of Code', value: data.metrics.lines_of_code },
        { label: 'Functions', value: data.metrics.functions },
        { label: 'Classes', value: data.metrics.classes },
        { label: 'Loops', value: data.metrics.loops },
        { label: 'Conditionals', value: data.metrics.conditionals },
        { label: 'Comments', value: data.metrics.comments },
        { label: 'Imports', value: data.metrics.imports }
    ];
    
    metricItems.forEach(item => {
        metricsHtml += `
            <div class="metric-item">
                <div class="metric-label">${item.label}</div>
                <div class="metric-value">${item.value}</div>
            </div>
        `;
    });
    
    // Complete results HTML
    resultsDiv.innerHTML = `
        <h2 style="margin-bottom: 1.5rem; font-size: 1.5rem;">Analysis Results</h2>
        
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Total Bugs</h3>
                <div class="summary-value">${data.summary.total_bugs}</div>
                <div class="bug-counts">
                    <span class="critical"> ${counts.critical}</span>
                    <span class="high">${counts.high}</span>
                    <span class="medium"> ${counts.medium}</span>
                    <span class="low">${counts.low}</span>
                </div>
            </div>
            
            <div class="summary-card">
                <h3>Bug Probability</h3>
                <div class="summary-value">${data.summary.bug_probability}%</div>
                <div class="summary-label">ML Prediction</div>
            </div>
            
            <div class="summary-card">
                <h3>Quality Score</h3>
                <div class="summary-value">${data.summary.quality_score}</div>
                <div class="grade-badge grade-${data.summary.quality_grade}">${data.summary.quality_grade}</div>
            </div>
            
            <div class="summary-card">
                <h3>Code Size</h3>
                <div class="summary-value">${data.metrics.lines_of_code}</div>
                <div class="summary-label">Lines of Code</div>
            </div>
        </div>
        
        <div class="risk-section ${riskClass}">
            <div class="risk-info">
                <h3>Risk Assessment</h3>
                <div class="risk-value">${data.summary.risk_level}</div>
            </div>
            <div class="risk-probability">
                ML model predicts ${data.summary.bug_probability}% probability of bugs
            </div>
        </div>
        
        <div class="metrics-section">
            <h3>Code Metrics</h3>
            <div class="metrics-grid">
                ${metricsHtml}
            </div>
        </div>
        
        <div class="bugs-section">
            <h3>Detected Bugs (${data.bugs.length})</h3>
            <div class="bug-list">
                ${bugsHtml}
            </div>
        </div>
        
        <div class="suggestions-section">
            <h3>Improvement Suggestions</h3>
            <ul class="suggestions-list">
                ${suggestionsHtml}
            </ul>
        </div>
    `;
    
    resultsDiv.classList.remove('hidden');
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}