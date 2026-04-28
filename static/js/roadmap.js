const MONTHS = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
];
const MONTHS_SHORT = [
    'Jan','Feb','Mar','Apr','May','Jun',
    'Jul','Aug','Sep','Oct','Nov','Dec'
];
const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

let adminMode = false;

function pd(s) {
    const [y, m, d] = s.split('-').map(Number);
    return new Date(y, m - 1, d);
}

function fk(d) {
    return d.getFullYear() + '-'
        + String(d.getMonth() + 1).padStart(2, '0') + '-'
        + String(d.getDate()).padStart(2, '0');
}

function ad(d, n) {
    const r = new Date(d);
    r.setDate(r.getDate() + n);
    return r;
}

function dayDiff(a, b) {
    return Math.round((b - a) / (1000 * 60 * 60 * 24));
}

function typeColors(type) {
    const td = (window.SCHEDULE_DATA.types || {})[type] || {};
    return {
        bg:   td.color_fill ? `#${td.color_fill}` : '#d3d1c7',
        text: td.color_text ? `#${td.color_text}` : '#444441',
    };
}

function renderLegend(types) {
    return Object.values(types).map(td =>
        `<div class="leg-item"><span class="leg-dot" style="background:#${td.color_fill}"></span>${td.label}</div>`
    ).join('');
}

const LABEL_W = 160;
const RIGHT_PAD = 16;
const MIN_BAR = 340;

function measureBarArea(container) {
    // Measure the scroll wrapper's clientWidth — excludes scrollbar, always accurate
    return Math.max(Math.floor(container.parentElement.clientWidth) - LABEL_W, MIN_BAR);
}

function renderGantt(phases, startDate, endDate, barArea) {
    const totalDays = dayDiff(startDate, endDate) + 1;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayOffset = dayDiff(startDate, today);

    const usable = barArea - RIGHT_PAD;
    const pxOf = days => (days / totalDays * usable).toFixed(1);

    const todayLine = (todayOffset >= 0 && todayOffset < totalDays)
        ? `<div class="gantt-today-line" style="left:${pxOf(todayOffset)}px;"></div>`
        : '';

    // Month labels
    let monthSpans = '';
    let mc = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
    while (mc <= endDate) {
        const mStart = mc < startDate ? startDate : mc;
        monthSpans += `<span style="position:absolute;left:${pxOf(dayDiff(startDate, mStart))}px;`
            + `bottom:5px;font-size:11px;color:#888888;white-space:nowrap;font-weight:400;">`
            + `${MONTHS_SHORT[mc.getMonth()]} ${mc.getFullYear()}</span>`;
        mc = new Date(mc.getFullYear(), mc.getMonth() + 1, 1);
    }

    // Labels column (outside scroll container — never scrolls)
    let labelsHtml = '<div class="gantt-header-spacer"></div>';
    phases.forEach(ph => {
        labelsHtml += `<div class="gantt-row-label">${ph.label}</div>`;
    });

    // Bars column (scrollable content, fixed pixel width)
    let barsHtml = `<div class="gantt-months">${todayLine}${monthSpans}</div>`;
    phases.forEach(ph => {
        const c = typeColors(ph.type);
        const phStart = pd(ph.start);
        const phEnd = pd(ph.end);
        const leftPx = pxOf(dayDiff(startDate, phStart));
        const widthPx = Math.max((dayDiff(phStart, phEnd) + 1) / totalDays * usable, 8).toFixed(1);
        barsHtml += `<div class="gantt-bar-row">
            ${todayLine}
            <div class="gantt-bar" style="left:${leftPx}px;width:${widthPx}px;background:${c.bg};color:${c.text};">${ph.label}</div>
        </div>`;
    });

    return `<div class="gantt-layout">
        <div class="gantt-labels-col">${labelsHtml}</div>
        <div class="gantt-bars-col">
            <div style="width:${barArea}px;">${barsHtml}</div>
        </div>
    </div>`;
}

function renderCalendar(schedule, startDate, endDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const firstMonth = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
    const lastMonth = new Date(endDate.getFullYear(), endDate.getMonth(), 1);
    let html = '';
    let cur = new Date(firstMonth);

    while (cur <= lastMonth) {
        const year = cur.getFullYear();
        const month = cur.getMonth();
        html += '<div class="month-block">';
        html += `<div class="month-label">${MONTHS[month]} ${year}</div>`;
        html += '<table class="cal-grid"><thead><tr>';
        DAYS.forEach(d => { html += `<th>${d}</th>`; });
        html += '</tr></thead><tbody>';

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        for (let row = 0; row < 6; row++) {
            if (row * 7 >= firstDay + daysInMonth) break;
            html += '<tr>';
            for (let col = 0; col < 7; col++) {
                const cellNum = row * 7 + col - firstDay + 1;
                if (cellNum < 1 || cellNum > daysInMonth) {
                    html += '<td class="out-of-range"></td>';
                } else {
                    const cellDate = new Date(year, month, cellNum);
                    const k = fk(cellDate);
                    const isW = col === 0 || col === 6;
                    const isTdy = cellDate.getTime() === today.getTime();
                    html += `<td class="${isW ? 'weekend' : ''}">`;
                    html += `<div class="day-num${isTdy ? ' today' : ''}">${cellNum}</div>`;
                    if (schedule[k]) {
                        schedule[k].forEach(ev => {
                            const c = typeColors(ev.type);
                            const doneClass = ev.complete ? ' pill-complete' : '';
                            const check = ev.complete ? '<span class="pill-check">&#10003;</span>' : '';
                            html += `<span class="pill${doneClass}" `
                                + `style="background:${c.bg};color:${c.text};" `
                                + `data-type="${ev.type}" data-label="${ev.label}">`
                                + `${check}${ev.label}</span>`;
                        });
                    }
                    html += '</td>';
                }
            }
            html += '</tr>';
        }
        html += '</tbody></table></div>';
        cur = new Date(year, month + 1, 1);
    }
    return html;
}

function computeProgress(schedule) {
    const certTypes = new Set(
        Object.values(window.SCHEDULE_DATA.certs).map(c => c.primary_type)
    );
    const counts = {};
    certTypes.forEach(t => { counts[t] = { total: 0, done: 0 }; });
    Object.values(schedule).forEach(events => {
        events.forEach(ev => {
            if (counts[ev.type] !== undefined) {
                counts[ev.type].total++;
                if (ev.complete) counts[ev.type].done++;
            }
        });
    });
    return counts;
}

function updateProgressBars(schedule) {
    const c = computeProgress(schedule);
    Object.entries(window.SCHEDULE_DATA.certs).forEach(([certKey, certMeta]) => {
        const t = certMeta.primary_type;
        const pct = c[t] && c[t].total ? Math.round(c[t].done / c[t].total * 100) : 0;
        const bar = document.getElementById(`${certKey}-bar`);
        const label = document.getElementById(`${certKey}-pct`);
        if (bar) bar.style.width = pct + '%';
        if (label) label.textContent = pct + '%';
    });
}

async function togglePill(type, label) {
    const key = sessionStorage.getItem('roadmap_admin_key');
    if (!key) return;

    const data = window.SCHEDULE_DATA;

    // Read current complete state from in-memory schedule
    let currentComplete = false;
    Object.values(data.schedule).forEach(events => {
        events.forEach(ev => {
            if (ev.type === type && ev.label === label) currentComplete = ev.complete;
        });
    });

    function applyState(complete) {
        Object.values(data.schedule).forEach(events => {
            events.forEach(ev => {
                if (ev.type === type && ev.label === label) ev.complete = complete;
            });
        });
        document.querySelectorAll(
            `.pill[data-type="${CSS.escape(type)}"][data-label="${CSS.escape(label)}"]`
        ).forEach(pill => {
            if (complete) {
                pill.classList.add('pill-complete');
                if (!pill.querySelector('.pill-check')) {
                    const check = document.createElement('span');
                    check.className = 'pill-check';
                    check.innerHTML = '&#10003;';
                    pill.prepend(check);
                }
            } else {
                pill.classList.remove('pill-complete');
                pill.querySelector('.pill-check')?.remove();
            }
        });
        updateProgressBars(data.schedule);
    }

    // Optimistic update — apply immediately before the request completes
    applyState(!currentComplete);

    try {
        const resp = await fetch('/api/roadmap/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Admin-Key': key },
            body: JSON.stringify({ type, label }),
        });
        if (!resp.ok) throw new Error(`${resp.status}`);
        const { complete } = await resp.json();
        // Sync with server's authoritative state in case it diverged
        if (complete !== !currentComplete) applyState(complete);
    } catch {
        applyState(currentComplete);
        alert('Failed to save — change reverted.');
    }
}

function setAdminMode(enabled) {
    adminMode = enabled;
    const lock = document.getElementById('admin-lock');
    if (lock) lock.innerHTML = enabled ? '&#128275;' : '&#128274;';
    document.getElementById('calendar-out').classList.toggle('admin-active', enabled);
}

function showModal() {
    document.getElementById('auth-modal').classList.add('visible');
    document.getElementById('admin-key-input').value = '';
    document.getElementById('auth-error').style.display = 'none';
    document.getElementById('admin-key-input').focus();
}

function hideModal() {
    document.getElementById('auth-modal').classList.remove('visible');
}

async function submitAuth() {
    const key = document.getElementById('admin-key-input').value;
    const resp = await fetch('/api/roadmap/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key }),
    });
    const { ok } = await resp.json();
    if (ok) {
        sessionStorage.setItem('roadmap_admin_key', key);
        setAdminMode(true);
        hideModal();
    } else {
        document.getElementById('auth-error').style.display = 'block';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const data = window.SCHEDULE_DATA;
    if (!data) return;

    const startDate = pd(data.start_date);
    const endDate = pd(data.end_date);
    const ganttOut = document.getElementById('gantt-out');

    function drawGantt() {
        ganttOut.innerHTML = renderGantt(data.phases, startDate, endDate, measureBarArea(ganttOut));
    }

    drawGantt();
    document.getElementById('legend-out').innerHTML = renderLegend(data.types || {});
    document.getElementById('calendar-out').innerHTML = renderCalendar(data.schedule, startDate, endDate);

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(drawGantt, 150);
    });


    // Restore admin session if key is still in sessionStorage
    if (sessionStorage.getItem('roadmap_admin_key')) {
        setAdminMode(true);
    }

    // Lock icon
    document.getElementById('admin-lock').addEventListener('click', () => {
        if (adminMode) {
            sessionStorage.removeItem('roadmap_admin_key');
            setAdminMode(false);
        } else {
            showModal();
        }
    });

    // Modal actions
    document.getElementById('auth-submit').addEventListener('click', submitAuth);
    document.getElementById('auth-cancel').addEventListener('click', hideModal);
    document.getElementById('admin-key-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') submitAuth();
        if (e.key === 'Escape') hideModal();
    });
    document.getElementById('auth-modal').addEventListener('click', e => {
        if (e.target === document.getElementById('auth-modal')) hideModal();
    });

    // Pill click delegation (only fires in admin mode)
    document.getElementById('calendar-out').addEventListener('click', e => {
        if (!adminMode) return;
        const pill = e.target.closest('.pill');
        if (!pill) return;
        togglePill(pill.dataset.type, pill.dataset.label);
    });
});
