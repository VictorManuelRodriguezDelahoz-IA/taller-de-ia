/* ============================================================
   ClickIT Dashboard - Frontend Logic
   ============================================================ */

const API = '';

// ============================================================
// NAVIGATION
// ============================================================

const navItems = document.querySelectorAll('.nav-item');
const sections = document.querySelectorAll('.section');

const sectionMeta = {
    overview: { title: 'Overview', subtitle: 'Bienvenido, Poncho. Aqui esta el resumen de ClickIT.' },
    proposals: { title: 'Propuestas', subtitle: 'Pipeline de propuestas comerciales y su estado actual.' },
    clients: { title: 'Clientes', subtitle: 'Base de clientes, satisfaccion y metricas de relacion.' },
    'ai-chat': { title: 'Chat IA', subtitle: 'Preguntale a la IA sobre el estado de la empresa.' },
};

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const section = item.dataset.section;

        navItems.forEach(n => n.classList.remove('active'));
        item.classList.add('active');

        sections.forEach(s => s.classList.remove('active'));
        document.getElementById(`section-${section}`).classList.add('active');

        document.getElementById('pageTitle').textContent = sectionMeta[section].title;
        document.getElementById('pageSubtitle').textContent = sectionMeta[section].subtitle;
    });
});

// ============================================================
// DATE
// ============================================================

const now = new Date();
const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
document.getElementById('currentDate').textContent =
    `${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;

// ============================================================
// FORMAT HELPERS
// ============================================================

function formatMoney(n) {
    if (n >= 1000000) return '$' + (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return '$' + (n / 1000).toFixed(0) + 'k';
    return '$' + n;
}

function formatMoneyFull(n) {
    return '$' + n.toLocaleString('en-US');
}

const statusLabels = {
    won: 'Ganada', pending: 'Pendiente', in_progress: 'En Progreso', lost: 'Perdida',
    active: 'Activo', at_risk: 'En Riesgo', churned: 'Perdido', prospect: 'Prospecto',
};

// ============================================================
// OVERVIEW
// ============================================================

let revenueChart, satisfactionChart, proposalsPieChart;

async function loadOverview() {
    try {
        const res = await fetch(`${API}/api/overview`);
        const data = await res.json();
        const k = data.kpis;

        document.getElementById('kpiRevenue').textContent = formatMoney(k.total_revenue);
        document.getElementById('kpiPipeline').textContent = formatMoney(k.pipeline_value);
        document.getElementById('kpiClients').textContent = k.active_clients;
        document.getElementById('kpiSatisfaction').textContent = k.avg_satisfaction + '/5';
        document.getElementById('kpiWinRate').textContent = k.win_rate + '%';
        document.getElementById('kpiTeam').textContent = k.team_size + ' personas';

        renderRevenueChart(data.monthly_revenue);
        renderSatisfactionChart(data.satisfaction_history);
        renderProposalsPieChart(k);
    } catch (err) {
        console.error('Error loading overview:', err);
    }
}

function renderRevenueChart(data) {
    const ctx = document.getElementById('revenueChart').getContext('2d');
    if (revenueChart) revenueChart.destroy();

    const labels = data.map(d => {
        const [y, m] = d.month.split('-');
        return months[parseInt(m) - 1] + ' ' + y.slice(2);
    });

    revenueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: data.map(d => d.revenue),
                    backgroundColor: 'rgba(79, 125, 249, 0.7)',
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Costos',
                    data: data.map(d => d.costs),
                    backgroundColor: 'rgba(248, 113, 113, 0.5)',
                    borderRadius: 6,
                    borderSkipped: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: { color: '#8b8fa3', font: { family: 'Inter', size: 12 }, usePointStyle: true, pointStyle: 'rectRounded' }
                },
            },
            scales: {
                x: { ticks: { color: '#5c6078', font: { size: 11 } }, grid: { display: false } },
                y: {
                    ticks: {
                        color: '#5c6078', font: { size: 11 },
                        callback: v => '$' + (v / 1000) + 'k'
                    },
                    grid: { color: 'rgba(42, 45, 62, 0.5)' }
                },
            },
        },
    });
}

function renderSatisfactionChart(data) {
    const ctx = document.getElementById('satisfactionChart').getContext('2d');
    if (satisfactionChart) satisfactionChart.destroy();

    const labels = data.map(d => {
        const [y, m] = d.month.split('-');
        return months[parseInt(m) - 1] + ' ' + y.slice(2);
    });

    satisfactionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Satisfaccion',
                data: data.map(d => d.score),
                borderColor: '#34d399',
                backgroundColor: 'rgba(52, 211, 153, 0.1)',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#34d399',
                pointRadius: 4,
                pointHoverRadius: 7,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: { ticks: { color: '#5c6078', font: { size: 11 } }, grid: { display: false } },
                y: {
                    min: 3.5, max: 5,
                    ticks: { color: '#5c6078', font: { size: 11 }, stepSize: 0.5 },
                    grid: { color: 'rgba(42, 45, 62, 0.5)' }
                },
            },
        },
    });
}

function renderProposalsPieChart(kpis) {
    const ctx = document.getElementById('proposalsPieChart').getContext('2d');
    if (proposalsPieChart) proposalsPieChart.destroy();

    proposalsPieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Ganadas', 'Pendientes', 'En Progreso', 'Perdidas'],
            datasets: [{
                data: [kpis.proposals_won, kpis.proposals_pending, kpis.proposals_in_progress, kpis.proposals_lost],
                backgroundColor: ['#34d399', '#fbbf24', '#4f7df9', '#f87171'],
                borderWidth: 0,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#8b8fa3', font: { family: 'Inter', size: 12 }, usePointStyle: true, pointStyle: 'circle', padding: 20 }
                },
            },
        },
    });
}

// ============================================================
// AI INSIGHTS
// ============================================================

async function loadInsights() {
    const el = document.getElementById('aiInsights');
    el.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';

    try {
        const res = await fetch(`${API}/api/ai/insights`);
        const data = await res.json();
        el.textContent = data.insights;
    } catch {
        el.textContent = 'No se pudieron cargar los insights. Verifica la conexion.';
    }
}

document.getElementById('refreshInsights').addEventListener('click', loadInsights);

// ============================================================
// PROPOSALS
// ============================================================

let allProposals = [];

async function loadProposals(filter = 'all') {
    try {
        const res = await fetch(`${API}/api/proposals?status=${filter}`);
        const data = await res.json();
        allProposals = data.proposals;
        renderProposals(data.proposals);
    } catch (err) {
        console.error('Error loading proposals:', err);
    }
}

function renderProposals(proposals) {
    const grid = document.getElementById('proposalsGrid');
    grid.innerHTML = proposals.map(p => `
        <div class="proposal-card status-${p.status}">
            <div class="proposal-header">
                <span class="proposal-client">${p.client}</span>
                <span class="proposal-amount">${formatMoneyFull(p.amount)}</span>
            </div>
            <div class="proposal-title">${p.title}</div>
            <div class="proposal-desc">${p.description}</div>
            <div class="proposal-footer">
                <div class="proposal-tech">
                    ${p.tech.slice(0, 3).map(t => `<span class="tech-tag">${t}</span>`).join('')}
                </div>
                <span class="status-badge status-${p.status}">${statusLabels[p.status] || p.status}</span>
            </div>
            ${p.lost_reason ? `<div class="lost-reason">${p.lost_reason}</div>` : ''}
        </div>
    `).join('');
}

// Proposal filters
document.querySelector('#section-proposals .filter-tabs').addEventListener('click', (e) => {
    if (!e.target.classList.contains('filter-btn')) return;
    document.querySelectorAll('#section-proposals .filter-btn').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    loadProposals(e.target.dataset.filter);
});

// ============================================================
// CLIENTS
// ============================================================

let allClients = [];

async function loadClients(filter = 'all') {
    try {
        const res = await fetch(`${API}/api/clients?status=${filter}`);
        const data = await res.json();
        allClients = data.clients;
        renderClients(data.clients);
    } catch (err) {
        console.error('Error loading clients:', err);
    }
}

function renderClients(clients) {
    const tbody = document.getElementById('clientsTableBody');
    tbody.innerHTML = clients.map(c => {
        const satPercent = c.satisfaction ? (c.satisfaction / 5 * 100) : 0;
        let satColor = '#34d399';
        if (c.satisfaction < 3.5) satColor = '#f87171';
        else if (c.satisfaction < 4) satColor = '#fbbf24';

        return `
            <tr>
                <td>
                    <div class="client-name-cell">
                        <span class="client-name">${c.name}</span>
                        <span class="client-since">Desde ${c.since}</span>
                    </div>
                </td>
                <td>${c.industry}</td>
                <td>${c.contact}</td>
                <td><span class="status-badge client-status-${c.status}">${statusLabels[c.status] || c.status}</span></td>
                <td>
                    ${c.satisfaction ? `
                        <div class="satisfaction-bar">
                            <div class="satisfaction-fill">
                                <div class="satisfaction-fill-inner" style="width: ${satPercent}%; background: ${satColor}"></div>
                            </div>
                            <span style="font-size:13px; font-weight:600; color:${satColor}">${c.satisfaction}</span>
                        </div>
                    ` : '<span style="color:var(--text-muted)">N/A</span>'}
                </td>
                <td style="font-weight:600">${c.total_revenue ? formatMoneyFull(c.total_revenue) : '-'}</td>
                <td style="text-align:center">${c.projects_count}</td>
            </tr>
        `;
    }).join('');
}

// Client filters
document.querySelector('#section-clients .filter-tabs').addEventListener('click', (e) => {
    if (!e.target.classList.contains('filter-btn')) return;
    document.querySelectorAll('#section-clients .filter-btn').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    loadClients(e.target.dataset.filter);
});

// ============================================================
// AI CHAT
// ============================================================

const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // User message
    appendMessage('user', message);
    chatInput.value = '';
    chatSend.disabled = true;

    // Loading
    const loadingId = 'loading-' + Date.now();
    chatMessages.innerHTML += `
        <div class="chat-message bot" id="${loadingId}">
            <div class="message-avatar">AI</div>
            <div class="message-content">
                <div class="loading-dots"><span></span><span></span><span></span></div>
            </div>
        </div>
    `;
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const res = await fetch(`${API}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        const data = await res.json();

        document.getElementById(loadingId).remove();
        appendMessage('bot', data.response, data.model);
    } catch {
        document.getElementById(loadingId).remove();
        appendMessage('bot', 'Error de conexion. Verifica que el servidor este corriendo.');
    }

    chatSend.disabled = false;
}

function appendMessage(role, text, model = '') {
    const avatar = role === 'user' ? 'P' : 'AI';
    const modelBadge = model ? `<span style="font-size:10px;color:var(--text-muted);display:block;margin-top:6px;">via ${model}</span>` : '';

    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <p>${text.replace(/\n/g, '<br>')}</p>
            ${modelBadge}
        </div>
    `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ============================================================
// INIT
// ============================================================

loadOverview();
loadInsights();
loadProposals();
loadClients();
