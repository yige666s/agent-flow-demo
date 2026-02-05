// Configuration
const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8080/api/v1'
    : '/api/v1';

const HEALTH_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8080/health'
    : '/health';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkSystemStatus();
    setupEventListeners();
    setInterval(checkSystemStatus, 15000); // Check every 15s
});

function setupEventListeners() {
    const form = document.getElementById('recommendForm');
    if (form) {
        form.addEventListener('submit', handleRecommend);
    }
}

// System Status
async function checkSystemStatus() {
    const statusBadge = document.getElementById('serviceStatus');
    const statusText = statusBadge.querySelector('.status-text');

    try {
        const response = await fetch(HEALTH_URL);
        if (response.ok) {
            statusBadge.classList.add('online');
            statusText.textContent = '系统运行中';
        } else {
            throw new Error();
        }
    } catch (error) {
        statusBadge.classList.remove('online');
        statusText.textContent = '系统连接失败';
    }
}

// Quick Tag Helper
window.setQuery = (text) => {
    const input = document.getElementById('queryInput');
    input.value = text;
    input.focus();
};

// Handle Recommendation Request
async function handleRecommend(e) {
    e.preventDefault();

    const query = document.getElementById('queryInput').value.trim();
    if (!query) return;

    const submitBtn = document.getElementById('submitBtn');
    const resultsSection = document.getElementById('resultsSection');
    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');

    // UI State Reset
    submitBtn.disabled = true;
    resultsSection.classList.add('hidden');
    emptyState.classList.add('hidden');
    loadingState.classList.remove('hidden');

    try {
        const startTime = Date.now();
        const response = await fetch(`${API_BASE_URL}/recommend`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                user_id: "anonymous_user",
                top_k: 6
            })
        });

        if (!response.ok) throw new Error('Recommendation failed');

        const data = await response.json();
        const duration = Date.now() - startTime;

        if (data.status === 'success' && data.recommendations && data.recommendations.length > 0) {
            renderResults(data, duration);
            resultsSection.classList.remove('hidden');
        } else {
            emptyState.classList.remove('hidden');
        }

    } catch (error) {
        console.error('Error:', error);
        showNotification('推荐失败，请稍后再试', 'error');
    } finally {
        submitBtn.disabled = false;
        loadingState.classList.add('hidden');
    }
}

// Render Results
function renderResults(data, duration) {
    const list = document.getElementById('recommendationsList');
    const explanation = document.getElementById('aiExplanation');
    const timeEl = document.getElementById('responseTime');

    // Set time and explanation
    timeEl.textContent = `耗时: ${(duration / 1000).toFixed(2)}s`;
    explanation.textContent = data.explanation || "为您推荐以下最佳模版：";

    // RRF scores are very small, we normalize them for the UI so the top result feels like a high-confidence match
    const maxScore = data.recommendations[0].score || 0.01;

    // Render cards
    list.innerHTML = data.recommendations.map((item, index) => {
        // Normalize: top result gets ~96-99%, others follow relatively
        const normalizedScore = (item.score / maxScore) * (98 - (index * 0.5));
        const displayScore = Math.max(70, normalizedScore).toFixed(1);

        return `
        <div class="recommendation-item card">
            <div class="item-header">
                <span class="item-category">${item.category || '通用'}</span>
                <span class="item-score">匹配度: ${displayScore}%</span>
            </div>
            <h3 class="item-title">${item.name}</h3>
            <p class="item-desc">${item.description}</p>
            <div class="item-meta">
                ${(item.tags || []).map(tag => `<span class="item-chip">${tag}</span>`).join('')}
                <span class="item-chip">${item.style || '默认风格'}</span>
            </div>
            <div class="item-footer">
                <button class="btn-use" onclick="showNotification('模版已准备就绪', 'success')">立即使用</button>
            </div>
        </div>
    `;}).join('');
}

// Notifications
function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    const el = document.createElement('div');
    el.className = `notification ${type}`;
    el.textContent = message;
    container.appendChild(el);

    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(20px)';
        setTimeout(() => el.remove(), 300);
    }, 3000);
}
