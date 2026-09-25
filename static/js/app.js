/**
 * FocusTracker Pro — Client Application Logic
 * High-performance, real-time WebSocket dashboard for productivity & distraction tracking.
 */

// Application State
const state = {
  socket: null,
  isConnected: false,
  isTracking: true,
  liveTimer: null,
  liveWindowDurationSec: 0,
  activeTab: 'dashboard',
  audioEnabled: true,
  desktopNotificationsEnabled: false,
  snoozedUntil: 0,
  settings: {
    idle_threshold: 60,
    alert_threshold: 30
  },
  charts: {
    category: null,
    hourly: null
  },
  activities: [],
  tasks: [],
  keywords: [],
  activityFilter: 'all',
  taskFilter: 'all'
};

// DOM Elements Cache
const DOM = {
  // Navigation & Shell
  navItems: document.querySelectorAll('.nav-item'),
  tabPanes: document.querySelectorAll('.tab-pane'),
  pageTitle: document.getElementById('pageTitle'),
  liveClock: document.getElementById('liveClock'),
  connIndicator: document.getElementById('connIndicator'),
  connText: document.getElementById('connText'),
  toggleTrackingBtn: document.getElementById('toggleTrackingBtn'),
  trackingStatusText: document.getElementById('trackingStatusText'),

  // Live Radar & Rail Guard
  liveAppName: document.getElementById('liveAppName'),
  liveWindowTitle: document.getElementById('liveWindowTitle'),
  liveAppAvatar: document.getElementById('liveAppAvatar'),
  liveCategoryBadge: document.getElementById('liveCategoryBadge'),
  liveConfidence: document.getElementById('liveConfidence'),
  liveWindowDuration: document.getElementById('liveWindowDuration'),
  railguardBadge: document.getElementById('railguardBadge'),
  webInspectorCard: document.getElementById('webInspectorCard'),
  inspectorUrlBadge: document.getElementById('inspectorUrlBadge'),
  inspectorSnippetText: document.getElementById('inspectorSnippetText'),
  inspectorKeywordsList: document.getElementById('inspectorKeywordsList'),
  inspectorStatusText: document.getElementById('inspectorStatusText'),


  // Metric Cards
  statProductive: document.getElementById('statProductive'),
  statDistraction: document.getElementById('statDistraction'),
  statTotalActive: document.getElementById('statTotalActive'),
  statFocusScore: document.getElementById('statFocusScore'),
  scoreRating: document.getElementById('scoreRating'),
  focusScoreBar: document.getElementById('focusScoreBar'),
  distractionPercentage: document.getElementById('distractionPercentage'),

  // Tables & Feeds
  dashboardActivityBody: document.getElementById('dashboardActivityBody'),
  fullActivityBody: document.getElementById('fullActivityBody'),
  activitySearchInput: document.getElementById('activitySearchInput'),
  activityFilters: document.querySelectorAll('.btn-filter'),
  viewAllActivitiesBtn: document.getElementById('viewAllActivitiesBtn'),
  activityCountBadge: document.getElementById('activityCountBadge'),

  // Tasks
  addTaskForm: document.getElementById('addTaskForm'),
  newTaskInput: document.getElementById('newTaskInput'),
  taskList: document.getElementById('taskList'),
  taskProgressPercent: document.getElementById('taskProgressPercent'),
  taskProgressBar: document.getElementById('taskProgressBar'),
  tasksCompletedCount: document.getElementById('tasksCompletedCount'),
  tasksTotalCount: document.getElementById('tasksTotalCount'),
  taskFilters: document.querySelectorAll('.btn-task-filter'),
  taskCountBadge: document.getElementById('taskCountBadge'),

  // Keywords
  addKeywordForm: document.getElementById('addKeywordForm'),
  newKwPhrase: document.getElementById('newKwPhrase'),
  newKwCategory: document.getElementById('newKwCategory'),
  keywordsContainer: document.getElementById('keywordsContainer'),
  kwSearchInput: document.getElementById('kwSearchInput'),
  forceRetrainBtn: document.getElementById('forceRetrainBtn'),

  // Modals & Alerts
  distractionModal: document.getElementById('distractionModal'),
  distractionModalMsg: document.getElementById('distractionModalMsg'),
  snoozeAlertBtn: document.getElementById('snoozeAlertBtn'),
  dismissAlertBtn: document.getElementById('dismissAlertBtn'),
  openSettingsBtn: document.getElementById('openSettingsBtn'),
  settingsModal: document.getElementById('settingsModal'),
  closeSettingsBtn: document.getElementById('closeSettingsBtn'),
  saveSettingsBtn: document.getElementById('saveSettingsBtn'),
  idleThresholdInput: document.getElementById('idleThresholdInput'),
  idleThresholdVal: document.getElementById('idleThresholdVal'),
  alertThresholdInput: document.getElementById('alertThresholdInput'),
  alertThresholdVal: document.getElementById('alertThresholdVal'),
  soundToggle: document.getElementById('soundToggle'),
  enableNotifyBtn: document.getElementById('enableNotifyBtn'),
  toastContainer: document.getElementById('toastContainer')
};

// Helper: Format seconds to readable format (e.g. 1h 24m 10s or 45s)
function formatSeconds(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;

  if (hrs > 0) {
    return `${hrs}h ${mins}m`;
  }
  if (mins > 0) {
    return `${mins}m ${secs}s`;
  }
  return `${secs}s`;
}

// Helper: Format duration to HH:MM:SS
function formatDurationHMS(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  const hrs = String(Math.floor(s / 3600)).padStart(2, '0');
  const mins = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const secs = String(s % 60).padStart(2, '0');
  return `${hrs}:${mins}:${secs}`;
}

// Helper: App Avatar Icon Selector
function getAppEmoji(appName) {
  const app = (appName || '').toLowerCase();
  if (app.includes('code') || app.includes('cursor') || app.includes('pycharm') || app.includes('sublime')) return '💻';
  if (app.includes('chrome') || app.includes('edge') || app.includes('firefox') || app.includes('brave') || app.includes('safari')) return '🌐';
  if (app.includes('terminal') || app.includes('cmd') || app.includes('powershell') || app.includes('bash')) return '📟';
  if (app.includes('youtube') || app.includes('netflix') || app.includes('vlc') || app.includes('spotify')) return '🎬';
  if (app.includes('slack') || app.includes('discord') || app.includes('telegram') || app.includes('teams')) return '💬';
  if (app.includes('figma') || app.includes('photoshop') || app.includes('blender')) return '🎨';
  if (app.includes('notion') || app.includes('obsidian') || app.includes('word') || app.includes('excel')) return '📝';
  return '⚡';
}

// Web Audio API Synthesizer Chime
function playChime(type = 'warning') {
  if (!state.audioEnabled) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === 'warning') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
      osc.frequency.exponentialRampToValueAtTime(330, ctx.currentTime + 0.35);
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
      osc.start();
      osc.stop(ctx.currentTime + 0.45);
    } else if (type === 'success') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
      osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.1); // E5
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    }
  } catch (e) {
    console.warn('Audio chime unsupported or blocked:', e);
  }
}

// Toast Notifications
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type === 'prod' ? 'prod' : type === 'dist' ? 'dist' : 'info'}`;
  
  const icon = type === 'prod' ? '🎯' : type === 'dist' ? '⚠️' : 'ℹ️';
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  
  DOM.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Desktop Notification Dispatcher
function sendDesktopNotification(title, body) {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'granted') {
    new Notification(title, {
      body: body,
      icon: '/static/favicon.ico'
    });
  }
}

// ==========================================================================
// WebSocket Real-time Communication
// ==========================================================================
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  state.socket = new WebSocket(wsUrl);

  state.socket.onopen = () => {
    state.isConnected = true;
    DOM.connIndicator.className = 'conn-dot online';
    DOM.connText.textContent = 'Live Connected';
    console.log('⚡ Connected to FocusTracker live stream.');
  };

  state.socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleServerMessage(msg);
    } catch (err) {
      console.error('Error parsing WebSocket message:', err);
    }
  };

  state.socket.onclose = () => {
    state.isConnected = false;
    DOM.connIndicator.className = 'conn-dot offline';
    DOM.connText.textContent = 'Reconnecting...';
    setTimeout(initWebSocket, 2000);
  };

  state.socket.onerror = (err) => {
    console.warn('WebSocket error, retrying...', err);
  };
}

function handleServerMessage(msg) {
  switch (msg.type) {
    case 'initial_state':
      if (msg.data.live) updateLiveRadar(msg.data.live);
      if (msg.data.summary) updateDashboardMetrics(msg.data.summary);
      setTrackingButtonState(msg.data.is_running);
      break;

    case 'live_status':
      updateLiveRadar(msg.data);
      break;

    case 'dashboard_stats':
      updateDashboardMetrics(msg.data);
      break;

    case 'distraction_alert':
      handleDistractionAlert(msg.data);
      break;

    case 'milestone_alert':
      showToast(msg.data.message, 'prod');
      playChime('success');
      sendDesktopNotification('Focus Milestone!', msg.data.message);
      break;
  }
}

// ==========================================================================
// UI Updates: Live Radar & Metrics
// ==========================================================================
function updateLiveRadar(data) {
  DOM.liveAppName.textContent = data.app_name || 'System';
  DOM.liveWindowTitle.textContent = data.window_title || 'No Active Window';
  DOM.liveAppAvatar.textContent = getAppEmoji(data.app_name);

  // Category Badge
  DOM.liveCategoryBadge.className = 'cat-badge';
  if (data.category === 'Intended Task') {
    DOM.liveCategoryBadge.classList.add('cat-prod');
    DOM.liveCategoryBadge.textContent = '🎯 INTENDED TASK';
  } else if (data.category === 'Distraction') {
    DOM.liveCategoryBadge.classList.add('cat-dist');
    DOM.liveCategoryBadge.textContent = '⚠️ DISTRACTION';
  } else {
    DOM.liveCategoryBadge.classList.add('cat-idle');
    DOM.liveCategoryBadge.textContent = '💤 SYSTEM IDLE';
  }

  // Confidence
  if (data.confidence && data.confidence > 0) {
    DOM.liveConfidence.textContent = `${(data.confidence * 100).toFixed(0)}% Conf`;
  } else {
    DOM.liveConfidence.textContent = '';
  }

  // Window Duration local timer reset
  state.liveWindowDurationSec = data.duration_seconds || 0;
  DOM.liveWindowDuration.textContent = formatDurationHMS(state.liveWindowDurationSec);

  // Web Rail Guard 70-Word Inspector Panel
  if (data.snippet && data.snippet.trim().length > 0 && !data.is_idle) {
    DOM.webInspectorCard.classList.remove('hidden');
    DOM.inspectorUrlBadge.textContent = data.url ? data.url : (data.app_name || 'Active Web Page');
    DOM.inspectorSnippetText.textContent = `"${data.snippet}"`;

    if (data.railguard_triggered) {
      DOM.railguardBadge.classList.remove('hidden');
      DOM.inspectorStatusText.innerHTML = `<span class="text-dist font-bold">⚠️ Rail-Guard Active: Overruled misleading title based on 70-word page text</span>`;
    } else {
      DOM.railguardBadge.classList.add('hidden');
      DOM.inspectorStatusText.textContent = `Analyzed ${data.word_count || 70} words against misleading content`;
    }

    // Render matched keywords tags
    if (data.matched_keywords && data.matched_keywords.length > 0) {
      DOM.inspectorKeywordsList.innerHTML = data.matched_keywords.map(kw => 
        `<span class="inspector-kw-tag">#${kw}</span>`
      ).join('');
    } else {
      DOM.inspectorKeywordsList.innerHTML = '';
    }
  } else {
    DOM.webInspectorCard.classList.add('hidden');
    DOM.railguardBadge.classList.add('hidden');
  }
}

function startLocalTicker() {
  if (state.liveTimer) clearInterval(state.liveTimer);
  state.liveTimer = setInterval(() => {
    state.liveWindowDurationSec += 1;
    DOM.liveWindowDuration.textContent = formatDurationHMS(state.liveWindowDurationSec);

    // Live clock in topbar
    const now = new Date();
    DOM.liveClock.textContent = now.toLocaleTimeString();
  }, 1000);
}

function updateDashboardMetrics(summary) {
  const active = summary.total_active_time || 0;
  const dist = summary.total_distraction_time || 0;
  const prod = summary.productive_time || Math.max(0, active - dist);
  const score = summary.focus_score !== undefined ? summary.focus_score : (active > 0 ? (prod / active) * 100 : 100);

  DOM.statProductive.textContent = formatSeconds(prod);
  DOM.statDistraction.textContent = formatSeconds(dist);
  DOM.statTotalActive.textContent = formatSeconds(active);
  DOM.statFocusScore.textContent = `${score.toFixed(1)}%`;
  DOM.focusScoreBar.style.width = `${Math.min(100, Math.max(0, score))}%`;

  // Focus rating label
  if (score >= 80) {
    DOM.scoreRating.textContent = '🔥 Peak Focus';
    DOM.scoreRating.style.color = '#10b981';
  } else if (score >= 60) {
    DOM.scoreRating.textContent = '👍 Good Pace';
    DOM.scoreRating.style.color = '#f59e0b';
  } else {
    DOM.scoreRating.textContent = '⚠️ Distracted';
    DOM.scoreRating.style.color = '#f43f5e';
  }

  // Distraction % of session
  const distPct = active > 0 ? ((dist / active) * 100).toFixed(0) : 0;
  DOM.distractionPercentage.textContent = `${distPct}% of session`;

  // Update Doughnut Chart
  updateCategoryChart(prod, dist);
}

// ==========================================================================
// Chart.js Visualizations
// ==========================================================================
function initCharts() {
  // 1. Doughnut Category Breakdown
  const catCanvas = document.getElementById('categoryChart');
  if (catCanvas) {
    const ctx = catCanvas.getContext('2d');
    state.charts.category = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Productive', 'Distraction'],
        datasets: [{
          data: [1, 0],
          backgroundColor: ['#10b981', '#f43f5e'],
          borderColor: '#111827',
          borderWidth: 3,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 } }
          },
          tooltip: {
            callbacks: {
              label: (context) => ` ${context.label}: ${formatSeconds(context.raw)}`
            }
          }
        }
      }
    });
  }

  // 2. Hourly Activity Bar Chart
  const hourlyCanvas = document.getElementById('hourlyChart');
  if (hourlyCanvas) {
    const ctx = hourlyCanvas.getContext('2d');
    const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);

    state.charts.hourly = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: hours,
        datasets: [
          {
            label: 'Productive (min)',
            data: new Array(24).fill(0),
            backgroundColor: 'rgba(16, 185, 129, 0.8)',
            borderRadius: 4
          },
          {
            label: 'Distraction (min)',
            data: new Array(24).fill(0),
            backgroundColor: 'rgba(244, 63, 94, 0.8)',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            stacked: true,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#64748b', font: { size: 10 } }
          },
          y: {
            stacked: true,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#64748b', font: { size: 10 } }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
          }
        }
      }
    });
  }
}

function updateCategoryChart(prod, dist) {
  if (!state.charts.category) return;
  const total = prod + dist;
  if (total === 0) {
    state.charts.category.data.datasets[0].data = [1, 0];
  } else {
    state.charts.category.data.datasets[0].data = [prod, dist];
  }
  state.charts.category.update();
}

async function loadHourlyChartData() {
  try {
    const res = await fetch('/api/stats/hourly');
    if (!res.ok) return;
    const data = await res.json();

    const prodMinutes = [];
    const distMinutes = [];

    for (let i = 0; i < 24; i++) {
      const key = String(i).padStart(2, '0');
      const hourData = data[key] || { productive: 0, distraction: 0 };
      prodMinutes.push(Math.round((hourData.productive || 0) / 60));
      distMinutes.push(Math.round((hourData.distraction || 0) / 60));
    }

    if (state.charts.hourly) {
      state.charts.hourly.data.datasets[0].data = prodMinutes;
      state.charts.hourly.data.datasets[1].data = distMinutes;
      state.charts.hourly.update();
    }
  } catch (err) {
    console.error('Error fetching hourly chart data:', err);
  }
}

// ==========================================================================
// Activities Feed & Re-classification Action
// ==========================================================================
async function loadActivities() {
  try {
    const search = DOM.activitySearchInput.value.trim();
    const cat = state.activityFilter;
    const url = `/api/activities?limit=60&search=${encodeURIComponent(search)}&category=${encodeURIComponent(cat)}`;
    
    const res = await fetch(url);
    if (!res.ok) return;
    state.activities = await res.json();

    renderActivities();
  } catch (err) {
    console.error('Error loading activities:', err);
  }
}

function renderActivities() {
  const count = state.activities.length;
  DOM.activityCountBadge.textContent = count;

  // Mini table on Dashboard (top 8)
  const miniList = state.activities.slice(0, 8);
  if (miniList.length === 0) {
    DOM.dashboardActivityBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No recent activity logged yet today.</td></tr>`;
  } else {
    DOM.dashboardActivityBody.innerHTML = miniList.map(a => renderActivityRow(a, false)).join('');
  }

  // Full table in Activity Log tab
  if (state.activities.length === 0) {
    DOM.fullActivityBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No activities match the filter.</td></tr>`;
  } else {
    DOM.fullActivityBody.innerHTML = state.activities.map((a, idx) => renderActivityRow(a, true, idx + 1)).join('');
  }

  // Attach reclassify event listeners
  attachReclassifyListeners();
}

function renderActivityRow(act, isFull = false, index = 1) {
  const isProd = act.category === 'Intended Task';
  const badgeClass = isProd ? 'cat-prod' : 'cat-dist';
  const badgeText = isProd ? 'TASK' : 'DISTRACT';
  const timeStr = act.start_time ? act.start_time.split('T')[1]?.substring(0, 8) || act.start_time : '';
  const durStr = formatSeconds(act.duration);

  const displayTitle = act.window_title.length > 50 ? act.window_title.substring(0, 47) + '...' : act.window_title;

  const targetNewCategory = isProd ? 'Distraction' : 'Intended Task';
  const actionBtnText = isProd ? 'Mark Distraction' : 'Mark Task';
  const actionBtnClass = isProd ? 'btn-outline text-dist' : 'btn-outline text-prod';

  if (!isFull) {
    return `
      <tr>
        <td><span class="cat-badge ${badgeClass}">${badgeText}</span></td>
        <td><strong>${act.app_name}</strong></td>
        <td title="${act.window_title}">${displayTitle}</td>
        <td><code>${durStr}</code></td>
        <td class="text-muted">${timeStr}</td>
        <td>
          <button class="btn btn-sm ${actionBtnClass} reclassify-btn" data-id="${act.id}" data-category="${targetNewCategory}">
            ${actionBtnText}
          </button>
        </td>
      </tr>
    `;
  }

  return `
    <tr>
      <td>${index}</td>
      <td><span class="cat-badge ${badgeClass}">${badgeText}</span></td>
      <td><strong>${act.app_name}</strong></td>
      <td title="${act.window_title}">${displayTitle}</td>
      <td><code>${durStr}</code></td>
      <td class="text-muted">${timeStr}</td>
      <td>
        <button class="btn btn-sm ${actionBtnClass} reclassify-btn" data-id="${act.id}" data-category="${targetNewCategory}">
          🔄 ${actionBtnText}
        </button>
      </td>
    </tr>
  `;
}

function attachReclassifyListeners() {
  document.querySelectorAll('.reclassify-btn').forEach(btn => {
    btn.onclick = async () => {
      const actId = btn.getAttribute('data-id');
      const newCategory = btn.getAttribute('data-category');

      try {
        const res = await fetch(`/api/activities/${actId}/reclassify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category: newCategory })
        });

        if (res.ok) {
          showToast(`Activity reclassified as "${newCategory}" & AI model retrained!`, newCategory === 'Intended Task' ? 'prod' : 'dist');
          loadActivities();
          loadHourlyChartData();
          loadKeywords();
        }
      } catch (err) {
        console.error('Error reclassifying activity:', err);
      }
    };
  });
}

// ==========================================================================
// Tasks Management
// ==========================================================================
async function loadTasks() {
  try {
    const res = await fetch('/api/tasks');
    if (!res.ok) return;
    state.tasks = await res.json();
    renderTasks();
  } catch (err) {
    console.error('Error loading tasks:', err);
  }
}

function renderTasks() {
  const filter = state.taskFilter;
  let filtered = state.tasks;
  if (filter === 'pending') filtered = filtered.filter(t => t.status !== 'complete');
  if (filter === 'complete') filtered = filtered.filter(t => t.status === 'complete');

  const total = state.tasks.length;
  const completed = state.tasks.filter(t => t.status === 'complete').length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  DOM.taskCountBadge.textContent = total - completed;
  DOM.taskProgressPercent.textContent = `${percent}%`;
  DOM.taskProgressBar.style.width = `${percent}%`;
  DOM.tasksCompletedCount.textContent = `${completed} completed`;
  DOM.tasksTotalCount.textContent = `${total} total`;

  if (filtered.length === 0) {
    DOM.taskList.innerHTML = `<li class="empty-state">No tasks in this view.</li>`;
    return;
  }

  DOM.taskList.innerHTML = filtered.map(t => `
    <li class="task-item ${t.status === 'complete' ? 'completed' : ''}">
      <div class="task-left">
        <input type="checkbox" class="task-checkbox" data-id="${t.id}" ${t.status === 'complete' ? 'checked' : ''} />
        <span class="task-text">${t.task_name}</span>
      </div>
      <button class="btn-delete" data-id="${t.id}" title="Delete task">🗑️</button>
    </li>
  `).join('');

  // Checkbox toggle handlers
  DOM.taskList.querySelectorAll('.task-checkbox').forEach(chk => {
    chk.onchange = async () => {
      const id = chk.getAttribute('data-id');
      const isComplete = chk.checked;
      await fetch(`/api/tasks/${id}/toggle`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: isComplete ? 'complete' : 'pending' })
      });
      if (isComplete) playChime('success');
      loadTasks();
    };
  });

  // Delete button handlers
  DOM.taskList.querySelectorAll('.btn-delete').forEach(btn => {
    btn.onclick = async () => {
      const id = btn.getAttribute('data-id');
      await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
      showToast('Task deleted', 'info');
      loadTasks();
    };
  });
}

// Add task form submission
DOM.addTaskForm.onsubmit = async (e) => {
  e.preventDefault();
  const name = DOM.newTaskInput.value.trim();
  if (!name) return;

  try {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_name: name })
    });
    if (res.ok) {
      DOM.newTaskInput.value = '';
      showToast('New focus task added!', 'prod');
      loadTasks();
    }
  } catch (err) {
    console.error('Error adding task:', err);
  }
};

// ==========================================================================
// ML Keywords Management
// ==========================================================================
async function loadKeywords() {
  try {
    const res = await fetch('/api/keywords');
    if (!res.ok) return;
    state.keywords = await res.json();
    renderKeywords();
  } catch (err) {
    console.error('Error loading keywords:', err);
  }
}

function renderKeywords() {
  const query = (DOM.kwSearchInput.value || '').toLowerCase().trim();
  let list = state.keywords;
  if (query) {
    list = list.filter(k => k.phrase.toLowerCase().includes(query) || k.category.toLowerCase().includes(query));
  }

  if (list.length === 0) {
    DOM.keywordsContainer.innerHTML = `<div class="empty-state">No keywords found.</div>`;
    return;
  }

  DOM.keywordsContainer.innerHTML = list.map(k => {
    const isProd = k.category === 'Intended Task';
    const chipClass = isProd ? 'kw-prod' : 'kw-dist';
    return `
      <div class="kw-chip ${chipClass}">
        <span>${isProd ? '🎯' : '⚠️'} ${k.phrase}</span>
        <button class="kw-del-btn" data-id="${k.id}" title="Remove keyword">&times;</button>
      </div>
    `;
  }).join('');

  // Delete keyword handlers
  DOM.keywordsContainer.querySelectorAll('.kw-del-btn').forEach(btn => {
    btn.onclick = async () => {
      const id = btn.getAttribute('data-id');
      await fetch(`/api/keywords/${id}`, { method: 'DELETE' });
      showToast('Keyword removed & AI model retrained', 'info');
      loadKeywords();
    };
  });
}

// Add keyword form submission
DOM.addKeywordForm.onsubmit = async (e) => {
  e.preventDefault();
  const phrase = DOM.newKwPhrase.value.trim();
  const category = DOM.newKwCategory.value;
  if (!phrase) return;

  try {
    const res = await fetch('/api/keywords', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword_phrase: phrase, category: category })
    });
    if (res.ok) {
      DOM.newKwPhrase.value = '';
      showToast(`Keyword "${phrase}" added to model dictionary!`, 'prod');
      loadKeywords();
    }
  } catch (err) {
    console.error('Error adding keyword:', err);
  }
};

// Force retrain button
DOM.forceRetrainBtn.onclick = async () => {
  try {
    DOM.forceRetrainBtn.disabled = true;
    DOM.forceRetrainBtn.textContent = '⏳ Retraining AI Model...';

    const res = await fetch('/api/model/retrain', { method: 'POST' });
    if (res.ok) {
      showToast('AI Classifier retrained successfully!', 'prod');
      playChime('success');
    }
  } catch (err) {
    console.error('Error retraining model:', err);
  } finally {
    DOM.forceRetrainBtn.disabled = false;
    DOM.forceRetrainBtn.textContent = '🔄 Force Retrain Model';
  }
};

DOM.kwSearchInput.oninput = () => renderKeywords();

// ==========================================================================
// Distraction Warning Modal & Audio Engine
// ==========================================================================
function handleDistractionAlert(data) {
  const now = Date.now();
  if (now < state.snoozedUntil) return;

  DOM.distractionModalMsg.textContent = data.message;
  DOM.distractionModal.classList.remove('hidden');

  playChime('warning');
  sendDesktopNotification('Focus Alert: Distraction Detected!', data.message);
}

DOM.dismissAlertBtn.onclick = () => {
  DOM.distractionModal.classList.add('hidden');
};

DOM.snoozeAlertBtn.onclick = () => {
  state.snoozedUntil = Date.now() + 5 * 60 * 1000; // 5 min snooze
  DOM.distractionModal.classList.add('hidden');
  showToast('Distraction alerts snoozed for 5 minutes', 'info');
};

// ==========================================================================
// Settings Modal & Engine Control
// ==========================================================================
DOM.openSettingsBtn.onclick = () => {
  DOM.settingsModal.classList.remove('hidden');
};

DOM.closeSettingsBtn.onclick = () => {
  DOM.settingsModal.classList.add('hidden');
};

DOM.idleThresholdInput.oninput = (e) => {
  DOM.idleThresholdVal.textContent = e.target.value;
};

DOM.alertThresholdInput.oninput = (e) => {
  DOM.alertThresholdVal.textContent = e.target.value;
};

DOM.soundToggle.onchange = (e) => {
  state.audioEnabled = e.target.checked;
};

DOM.enableNotifyBtn.onclick = async () => {
  if ('Notification' in window) {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      DOM.enableNotifyBtn.textContent = '✅ Notifications Enabled';
      DOM.enableNotifyBtn.classList.remove('btn-outline');
      DOM.enableNotifyBtn.classList.add('btn-primary');
      showToast('Browser notifications enabled!', 'prod');
    }
  }
};

DOM.saveSettingsBtn.onclick = async () => {
  const idle = parseInt(DOM.idleThresholdInput.value, 10);
  const alert = parseInt(DOM.alertThresholdInput.value, 10);

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idle_threshold: idle, alert_threshold: alert })
    });
    if (res.ok) {
      showToast('Settings saved successfully!', 'prod');
      DOM.settingsModal.classList.add('hidden');
    }
  } catch (err) {
    console.error('Error saving settings:', err);
  }
};

function setTrackingButtonState(isRunning) {
  state.isTracking = isRunning;
  if (isRunning) {
    DOM.trackingStatusText.textContent = 'Pause';
    DOM.toggleTrackingBtn.querySelector('.btn-icon').textContent = '⏸️';
  } else {
    DOM.trackingStatusText.textContent = 'Resume';
    DOM.toggleTrackingBtn.querySelector('.btn-icon').textContent = '▶️';
  }
}

DOM.toggleTrackingBtn.onclick = async () => {
  try {
    const res = await fetch('/api/tracker/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'toggle' })
    });
    if (res.ok) {
      const data = await res.json();
      setTrackingButtonState(data.is_running);
      showToast(data.is_running ? 'Monitoring active' : 'Monitoring paused', 'info');
    }
  } catch (err) {
    console.error('Error toggling tracker:', err);
  }
};

// ==========================================================================
// Tab Navigation & Filter Events
// ==========================================================================
DOM.navItems.forEach(item => {
  item.onclick = () => {
    const tabName = item.getAttribute('data-tab');
    switchTab(tabName);
  };
});

DOM.viewAllActivitiesBtn.onclick = () => switchTab('activities');

function switchTab(tabName) {
  state.activeTab = tabName;

  DOM.navItems.forEach(i => i.classList.toggle('active', i.getAttribute('data-tab') === tabName));
  DOM.tabPanes.forEach(p => p.classList.toggle('active', p.id === `tab-${tabName}`));

  if (tabName === 'dashboard') {
    DOM.pageTitle.textContent = 'Dashboard Overview';
    loadHourlyChartData();
    loadActivities();
  } else if (tabName === 'activities') {
    DOM.pageTitle.textContent = 'Activity History & Feedback';
    loadActivities();
  } else if (tabName === 'tasks') {
    DOM.pageTitle.textContent = 'Daily Focus Tasks';
    loadTasks();
  } else if (tabName === 'keywords') {
    DOM.pageTitle.textContent = 'Machine Learning Keywords';
    loadKeywords();
  }
}

// Activity Search & Category Filter
DOM.activitySearchInput.oninput = () => loadActivities();
DOM.activityFilters.forEach(btn => {
  btn.onclick = () => {
    DOM.activityFilters.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.activityFilter = btn.getAttribute('data-filter');
    loadActivities();
  };
});

// Task Filters
DOM.taskFilters.forEach(btn => {
  btn.onclick = () => {
    DOM.taskFilters.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.taskFilter = btn.getAttribute('data-task-filter');
    renderTasks();
  };
});

// Date display in topbar
function initDate() {
  const options = { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' };
  const dateStr = new Date().toLocaleDateString(undefined, options);
  const dateSub = document.getElementById('currentDateStr');
  if (dateSub) dateSub.textContent = dateStr;
}

// ==========================================================================
// Initialization
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  initDate();
  startLocalTicker();
  initCharts();
  initWebSocket();
  loadActivities();
  loadHourlyChartData();
  loadTasks();
  loadKeywords();
});
