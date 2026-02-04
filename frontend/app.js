// Configuration
// 支持本地开发和 Kubernetes 部署
// 本地: http://localhost:8000/api/v1
// Kubernetes: /api/v1 (通过 Nginx 代理)
const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api/v1'
    : '/api/v1';
const POLL_INTERVAL = 2000; // 2 seconds

// State
let tasks = [];
let polling = {};

// Example tasks
const examples = [
	"帮我获取 https://example.com 的网页标题和链接数量，并保存到 result.json 文件",
	"创建一个文本文件 hello.txt，内容是 'Hello from AgentFlow!'",
	"访问 https://httpbin.org/json 并提取返回的 JSON 数据中的 slideshow.title 字段"
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
	checkSystemStatus();
	loadTasks();
	setupEventListeners();
	setInterval(checkSystemStatus, 30000); // Check every 30s
});

// Event Listeners
function setupEventListeners() {
	document.getElementById('taskForm').addEventListener('submit', handleSubmit);
}

// System Status
async function checkSystemStatus() {
	const statusEl = document.getElementById('systemStatus');
	const dotEl = statusEl.querySelector('.status-dot');
	const textEl = statusEl.querySelector('.status-text');

	try {
		const response = await fetch(`http://localhost:8000/health`);
		if (response.ok) {
			const data = await response.json();
			dotEl.classList.add('online');
			textEl.textContent = `系统运行中`;
		} else {
			throw new Error('Backend not healthy');
		}
	} catch (error) {
		dotEl.classList.remove('online');
		textEl.textContent = '系统离线';
	}
}

// Fill Example
function fillExample(index) {
	document.getElementById('taskInput').value = examples[index];
}

// Handle Form Submit
async function handleSubmit(e) {
	e.preventDefault();

	const userInput = document.getElementById('taskInput').value.trim();
	if (!userInput) return;

	const submitBtn = document.getElementById('submitBtn');
	submitBtn.disabled = true;
	submitBtn.innerHTML = '<span class="spinner"></span> 提交中...';

	try {
		const response = await fetch(`${API_BASE_URL}/tasks`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ user_input: userInput })
		});

		if (!response.ok) {
			throw new Error('Failed to create task');
		}

		const data = await response.json();

		// Clear input
		document.getElementById('taskInput').value = '';

		// Show success message
		showNotification('任务已创建！', 'success');

		// Reload tasks
		await loadTasks();

		// Start polling for this task
		startPolling(data.task_id);

	} catch (error) {
		console.error('Error creating task:', error);
		showNotification('任务创建失败，请检查后端服务是否运行', 'error');
	} finally {
		submitBtn.disabled = false;
		submitBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M0 0L16 8L0 16V10L12 8L0 6V0Z"/>
            </svg>
            提交任务
        `;
	}
}

// Load Tasks
async function loadTasks() {
	try {
		const response = await fetch(`${API_BASE_URL}/tasks`);

		// Note: The current backend doesn't have a list endpoint
		// So we'll maintain a local list of created tasks
		// In production, you'd want to add a GET /tasks endpoint to the backend

		renderTasks();
	} catch (error) {
		console.error('Error loading tasks:', error);
	}
}

// Refresh Tasks
async function refreshTasks() {
	const refreshBtn = document.getElementById('refreshBtn');
	refreshBtn.disabled = true;
	refreshBtn.innerHTML = '刷新中...';

	// Reload all task statuses
	for (const task of tasks) {
		await getTaskDetails(task.id);
	}

	renderTasks();

	setTimeout(() => {
		refreshBtn.disabled = false;
		refreshBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 2V0L5 3L8 6V4C11.31 4 14 6.69 14 10C14 11.01 13.75 11.97 13.3 12.8L14.46 13.96C15.13 12.81 15.5 11.45 15.5 10C15.5 5.86 12.14 2.5 8 2.5V2ZM8 16C4.69 16 2 13.31 2 10C2 8.99 2.25 8.03 2.7 7.2L1.54 6.04C0.87 7.19 0.5 8.55 0.5 10C0.5 14.14 3.86 17.5 8 17.5V20L11 17L8 14V16Z"/>
            </svg>
            刷新
        `;
	}, 500);
}

// Render Tasks
function renderTasks() {
	const tasksList = document.getElementById('tasksList');

	if (tasks.length === 0) {
		tasksList.innerHTML = `
            <div class="empty-state">
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                    <circle cx="32" cy="32" r="30" stroke="currentColor" stroke-width="2" opacity="0.3"/>
                    <path d="M32 20V44M20 32H44" stroke="currentColor" stroke-width="2" opacity="0.5"/>
                </svg>
                <p>暂无任务</p>
                <p class="hint">创建您的第一个任务开始使用</p>
            </div>
        `;
		return;
	}

	// Sort by created_at descending
	const sortedTasks = [...tasks].sort((a, b) =>
		new Date(b.created_at) - new Date(a.created_at)
	);

	tasksList.innerHTML = sortedTasks.map(task => createTaskCard(task)).join('');
}

// Create Task Card
function createTaskCard(task) {
	const statusClass = `status-${task.status}`;
	const statusText = getStatusText(task.status);
	const timeAgo = getTimeAgo(task.created_at);

	return `
        <div class="task-card" onclick="showTaskDetails('${task.id}')">
            <div class="task-card-header">
                <div class="task-id">${task.id}</div>
                <div class="task-status ${statusClass}">${statusText}</div>
            </div>
            <div class="task-input">${escapeHtml(task.user_input)}</div>
            <div class="task-meta">
                <span>📅 ${timeAgo}</span>
                ${task.plan ? `<span>📋 ${task.plan.steps.length} 个步骤</span>` : ''}
                ${task.status === 'completed' ? '<span>✅ 已完成</span>' : ''}
            </div>
        </div>
    `;
}

// Get Status Text
function getStatusText(status) {
	const statusMap = {
		'pending': '等待中',
		'planning': '规划中',
		'running': '执行中',
		'completed': '已完成',
		'failed': '失败',
		'cancelled': '已取消'
	};
	return statusMap[status] || status;
}

// Get Time Ago
function getTimeAgo(timestamp) {
	const now = new Date();
	const past = new Date(timestamp);
	const diffMs = now - past;
	const diffMins = Math.floor(diffMs / 60000);

	if (diffMins < 1) return '刚刚';
	if (diffMins < 60) return `${diffMins} 分钟前`;

	const diffHours = Math.floor(diffMins / 60);
	if (diffHours < 24) return `${diffHours} 小时前`;

	const diffDays = Math.floor(diffHours / 24);
	return `${diffDays} 天前`;
}

// Show Task Details
async function showTaskDetails(taskId) {
	const task = await getTaskDetails(taskId);
	if (!task) return;

	const modal = document.getElementById('taskModal');
	const modalBody = document.getElementById('modalBody');

	modalBody.innerHTML = `
        <div class="task-detail">
            <div class="detail-section">
                <h4>任务 ID</h4>
                <p class="task-id">${task.id}</p>
            </div>
            
            <div class="detail-section">
                <h4>状态</h4>
                <div class="task-status ${`status-${task.status}`}">${getStatusText(task.status)}</div>
            </div>
            
            <div class="detail-section">
                <h4>用户输入</h4>
                <p>${escapeHtml(task.user_input)}</p>
            </div>
            
            ${task.plan ? `
                <div class="detail-section">
                    <h4>执行计划</h4>
                    <div class="plan-steps">
                        ${task.plan.steps.map((step, i) => `
                            <div class="step-item">
                                <div class="step-number">${step.step_id}</div>
                                <div class="step-content">
                                    <div class="step-desc">${escapeHtml(step.description)}</div>
                                    <div class="step-tool">工具: ${step.tool}</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${task.result ? `
                <div class="detail-section">
                    <h4>执行结果</h4>
                    <pre class="result-json">${JSON.stringify(task.result, null, 2)}</pre>
                </div>
            ` : ''}
            
            ${task.error ? `
                <div class="detail-section error-section">
                    <h4>错误信息</h4>
                    <p class="error-text">${escapeHtml(task.error)}</p>
                </div>
            ` : ''}
            
            <div class="detail-section">
                <h4>时间信息</h4>
                <p>创建时间: ${new Date(task.created_at).toLocaleString('zh-CN')}</p>
                <p>更新时间: ${new Date(task.updated_at).toLocaleString('zh-CN')}</p>
                ${task.completed_at ? `<p>完成时间: ${new Date(task.completed_at).toLocaleString('zh-CN')}</p>` : ''}
            </div>
        </div>
    `;

	// Add styles for modal content
	const style = document.createElement('style');
	style.textContent = `
        .detail-section { margin-bottom: 24px; }
        .detail-section h4 { margin-bottom: 8px; font-size: 14px; color: var(--text-secondary); }
        .plan-steps { display: flex; flex-direction: column; gap: 12px; }
        .step-item { display: flex; gap: 12px; padding: 12px; background: var(--secondary); border-radius: var(--radius-sm); }
        .step-number { 
            width: 32px; 
            height: 32px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            background: var(--primary); 
            color: white; 
            border-radius: 50%; 
            font-weight: 600;
            flex-shrink: 0;
        }
        .step-content { flex: 1; }
        .step-desc { font-weight: 500; margin-bottom: 4px; }
        .step-tool { font-size: 13px; color: var(--text-secondary); }
        .result-json { 
            background: #1e293b; 
            color: #e2e8f0; 
            padding: 16px; 
            border-radius: var(--radius-sm); 
            overflow-x: auto;
            font-size: 13px;
        }
        .error-section { background: #fed7d7; padding: 16px; border-radius: var(--radius-sm); }
        .error-text { color: #c53030; }
    `;
	modalBody.appendChild(style);

	modal.classList.add('show');
}

// Close Modal
function closeModal() {
	document.getElementById('taskModal').classList.remove('show');
}

// Get Task Details
async function getTaskDetails(taskId) {
	try {
		const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
		if (!response.ok) throw new Error('Task not found');

		const task = await response.json();

		// Update in local tasks array
		const index = tasks.findIndex(t => t.id === taskId);
		if (index >= 0) {
			tasks[index] = task;
		} else {
			tasks.push(task);
		}

		renderTasks();
		return task;
	} catch (error) {
		console.error('Error getting task details:', error);
		return null;
	}
}

// Start Polling
function startPolling(taskId) {
	if (polling[taskId]) return;

	polling[taskId] = setInterval(async () => {
		const task = await getTaskDetails(taskId);

		if (task && (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled')) {
			clearInterval(polling[taskId]);
			delete polling[taskId];

			if (task.status === 'completed') {
				showNotification(`任务 ${taskId.slice(0, 8)}... 已完成！`, 'success');
			} else if (task.status === 'failed') {
				showNotification(`任务 ${taskId.slice(0, 8)}... 执行失败`, 'error');
			}
		}
	}, POLL_INTERVAL);
}

// Show Notification
function showNotification(message, type = 'info') {
	// Create notification element
	const notification = document.createElement('div');
	notification.className = `notification notification-${type}`;
	notification.textContent = message;

	// Add styles
	const style = document.createElement('style');
	style.textContent = `
        .notification {
            position: fixed;
            top: 24px;
            right: 24px;
            padding: 16px 24px;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            z-index: 2000;
            animation: slideIn 0.3s;
            font-weight: 500;
        }
        .notification-success { background: #c6f6d5; color: #22543d; }
        .notification-error { background: #fed7d7; color: #c53030; }
        .notification-info { background: #bee3f8; color: #2c5282; }
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `;
	document.head.appendChild(style);
	document.body.appendChild(notification);

	// Remove after 3 seconds
	setTimeout(() => {
		notification.style.animation = 'slideIn 0.3s reverse';
		setTimeout(() => notification.remove(), 300);
	}, 3000);
}

// Utility: Escape HTML
function escapeHtml(text) {
	const div = document.createElement('div');
	div.textContent = text;
	return div.innerHTML;
}
