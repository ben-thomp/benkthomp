const PHASE_COLORS = {
    genai:  { bg: '#B5D4F4', text: '#0C447C' },
    review: { bg: '#C0DD97', text: '#27500A' },
    ilc:    { bg: '#FAC775', text: '#633806' },
    study:  { bg: '#CECBF6', text: '#3C3489' },
    exam:   { bg: '#F7C1C1', text: '#791F1F' },
    cpcu:   { bg: '#F4C0D1', text: '#72243E' },
    buffer: { bg: '#D3D1C7', text: '#444441' },
};

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

function renderGantt(phases, startDate, endDate) {
    const totalDays = dayDiff(startDate, endDate) + 1;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayOffset = dayDiff(startDate, today);
    const BAR_AREA = 560;

    let monthHeaders = '<tr><td class="gantt-label"></td>';
    let cur = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
    while (cur <= endDate) {
        const monthStart = cur < startDate ? startDate : cur;
        const nextMonth = new Date(cur.getFullYear(), cur.getMonth() + 1, 1);
        const monthEnd = nextMonth > endDate ? endDate : ad(nextMonth, -1);
        const span = dayDiff(monthStart, monthEnd) + 1;
        const pct = (span / totalDays * BAR_AREA).toFixed(1);
        monthHeaders += `<th style="width:${pct}px;text-align:left;font-size:11px;`
            + `color:#8b949e;font-weight:400;padding:0 0 5px 2px;`
            + `border-bottom:1px solid #30363d;">`
            + `${MONTHS_SHORT[cur.getMonth()]} ${cur.getFullYear()}</th>`;
        cur = nextMonth;
    }
    monthHeaders += '</tr>';

    let rows = '';
    phases.forEach(ph => {
        const c = PHASE_COLORS[ph.type] || PHASE_COLORS.buffer;
        const phStart = pd(ph.start);
        const phEnd = pd(ph.end);
        const leftDays = dayDiff(startDate, phStart);
        const spanDays = dayDiff(phStart, phEnd) + 1;
        const leftPx = (leftDays / totalDays * BAR_AREA).toFixed(1);
        const widthPx = Math.max(spanDays / totalDays * BAR_AREA, 8).toFixed(1);
        const todayLine = (todayOffset >= 0 && todayOffset <= totalDays)
            ? `<div class="gantt-today-line" style="left:${(todayOffset / totalDays * BAR_AREA).toFixed(1)}px;"></div>`
            : '';
        rows += `<tr>
            <td class="gantt-label">${ph.label}</td>
            <td class="gantt-bar-cell" style="width:${BAR_AREA}px;position:relative;">
                ${todayLine}
                <div class="gantt-bar" style="left:${leftPx}px;width:${widthPx}px;background:${c.bg};color:${c.text};">${ph.label}</div>
            </td>
        </tr>`;
    });

    return `<table class="gantt-table"><thead>${monthHeaders}</thead><tbody>${rows}</tbody></table>`;
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
                            const doneClass = ev.complete ? ' pill-complete' : '';
                            const check = ev.complete ? '<span class="pill-check">&#10003;</span>' : '';
                            html += `<span class="pill pill-${ev.type}${doneClass}" `
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
    const counts = {
        genai: { total: 0, done: 0 },
        cpcu:  { total: 0, done: 0 },
    };
    Object.values(schedule).forEach(events => {
        events.forEach(ev => {
            if (ev.type === 'genai' || ev.type === 'cpcu') {
                counts[ev.type].total++;
                if (ev.complete) counts[ev.type].done++;
            }
        });
    });
    return counts;
}

function updateProgressBars(schedule) {
    const c = computeProgress(schedule);
    ['genai', 'cpcu'].forEach(t => {
        const pct = c[t].total ? Math.round(c[t].done / c[t].total * 100) : 0;
        const bar = document.getElementById(`${t}-bar`);
        const label = document.getElementById(`${t}-pct`);
        if (bar) bar.style.width = pct + '%';
        if (label) label.textContent = pct + '%';
    });
}

async function togglePill(type, label) {
    const key = sessionStorage.getItem('roadmap_admin_key');
    if (!key) return;

    const resp = await fetch('/api/roadmap/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Key': key },
        body: JSON.stringify({ type, label }),
    });
    if (!resp.ok) return;

    const { complete } = await resp.json();

    // Update all matching pills and the in-memory schedule
    const data = window.SCHEDULE_DATA;
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

    document.getElementById('gantt-out').innerHTML = renderGantt(data.phases, startDate, endDate);
    document.getElementById('calendar-out').innerHTML = renderCalendar(data.schedule, startDate, endDate);

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
