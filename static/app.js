const $ = (sel) => document.querySelector(sel);

const THEME = {
  accent: "#58a6ff",
  good: "#3fb950",
  warn: "#d29922",
  bad: "#f85149",
  muted: "#8b949e",
  purple: "#a371f7",
  emerald: "#39d353",
  border: "#262c38",
};

const LEVEL_COLORS = {
  A1: "#8b949e",
  A2: "#58a6ff",
  B1: "#3fb950",
  B2: "#d29922",
  C1: "#f85149",
  C2: "#a371f7",
};

const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];
const LEVEL_RANK = { A1: 1, A2: 2, B1: 3, B2: 4, C1: 5, C2: 6 };

Chart.defaults.color = "#8b949e";
Chart.defaults.borderColor = "#262c38";
Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

const DL = {
  color: "#e6edf3",
  anchor: "end",
  align: "end",
  offset: 4,
  font: { size: 11, weight: "600" },
  formatter: (v) => (v > 0 ? v : ""),
};

const charts = {};
let currentTab = "overview";
let wordsSortKey = "score";
let wordsSortDir = "desc";
let wordsStatusFilter = "";
let wordsPageSize = 100;
let wordsPage = 1;
let scatterXAxis = "attempts";
let editingIdx = null;

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function toast(msg, kind = "ok") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = `toast show ${kind}`;
  setTimeout(() => { el.className = "toast"; }, 2500);
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return r.json();
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function hint(key) {
  return `<p class="hint">${I18N.t(key)}</p>`;
}

// Shared level+phrase badge for tables.
function levelBadge(level, isPhrase) {
  const phr = isPhrase ? `<span class="phrase-badge">${I18N.t("words.phrase")}</span>` : "";
  if (level) return `<span class="level-badge level-${level}">${level}</span>${phr}`;
  return isPhrase ? `<span class="muted">—</span>${phr}` : `<span class="muted">—</span>`;
}

// ---------- Markdown export helpers ----------
function mdCell(s) {
  return String(s ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, " ").trim();
}

function mdTable(headers, rows) {
  const out = [`| ${headers.join(" | ")} |`, `|${headers.map(() => "---").join("|")}|`];
  rows.forEach(r => out.push(`| ${r.join(" | ")} |`));
  return out;
}

function mdStamp() {
  return new Date().toISOString().slice(0, 16).replace("T", " ");
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast(I18N.t("copy.copied"));
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      toast(I18N.t("copy.copied"));
    } catch {
      toast(I18N.t("copy.error"), "error");
    }
  }
}

function buildOverviewMd(d) {
  const L = (k) => I18N.t(k);
  const out = [];
  out.push(`# ${L("app.title")} — ${L("tabs.overview")}`);
  out.push(`${L("copy.date")}: ${mdStamp()}`);
  out.push("");

  out.push(`## ${L("group.status")}`);
  out.push(`- ${L("kpi.total")}: ${d.s.total}`);
  out.push(`- ${L("kpi.mature")}: ${d.s.by_status.mature || 0} (${d.s.mature_share}%)`);
  out.push(`- ${L("kpi.young")}: ${d.s.by_status.young || 0}`);
  out.push(`- ${L("kpi.learning")}: ${d.s.by_status.learning || 0}`);
  out.push(`- ${L("kpi.new")}: ${d.s.by_status.new || 0}`);
  out.push("");

  out.push(`## ${L("group.quality")}`);
  out.push(`- ${L("kpi.avg_easiness")}: ${d.s.avg_easiness}`);
  out.push(`- ${L("kpi.attempts")}: ${d.s.total_attempts}`);
  out.push(d.cefrAvg.matched
    ? `- ${L("kpi.cefr_avg")}: ${d.cefrAvg.avg.toFixed(2)} (${d.cefrAvg.matched}/${d.s.total})`
    : `- ${L("kpi.cefr_avg")}: —`);
  out.push(`- ${L("kpi.avg_cost")}: ${d.cost.avg} (${d.cost.count})`);
  out.push("");

  out.push(`## ${L("group.activity")}`);
  out.push(`- ${L("kpi.streak_current")}: ${d.streak.current}`);
  out.push(`- ${L("kpi.streak_longest")}: ${d.streak.longest}`);
  out.push(`- ${L("kpi.overdue")}: ${d.over.length}`);
  out.push(`- ${L("kpi.avg_load")}: ${d.load.avg} (${L("kpi.peak")}: ${d.load.peak})`);
  out.push(`- ${L("copy.active_days")}: ${d.heat.days.filter(x => x.count > 0).length}/${d.heat.days.length}`);
  out.push("");

  out.push(`## ${L("chart.cefr_profile.title")}`);
  out.push(...mdTable(
    [...d.cefrP.labels, L("words.unknown_level")],
    [[...d.cefrP.counts, d.cefrP.unknown]],
  ));
  out.push("");

  out.push(`## ${L("chart.cefr_ease.title")}`);
  out.push(...mdTable(
    d.cefrEase.map(r => r.level),
    [d.cefrEase.map(r => r.avg_easiness || "—")],
  ));
  out.push("");

  out.push(`## ${L("chart.easiness.title")}`);
  out.push(...mdTable(d.hist.labels, [d.hist.counts]));
  out.push("");

  out.push(`## ${L("chart.intervals.title")}`);
  out.push(...mdTable(d.intervals.labels, [d.intervals.counts]));
  out.push("");

  out.push(`## ${L("chart.recall_ease.title")}`);
  out.push(...mdTable(d.recallEase.labels, [d.recallEase.counts]));
  out.push("");

  out.push(`## ${L("chart.weekly.title")}`);
  out.push(...mdTable(d.week.weeks, [d.week.counts]));
  out.push("");

  out.push(`## ${L("chart.time_of_day.title")}`);
  out.push(...mdTable(d.tod.labels, [d.tod.counts]));
  out.push("");

  return out.join("\n");
}

function buildCalendarMd(d) {
  const L = (k) => I18N.t(k);
  const out = [];
  out.push(`# ${L("app.title")} — ${L("tabs.calendar")}`);
  out.push(`${L("copy.date")}: ${mdStamp()}`);
  out.push("");

  out.push(`## ${L("chart.calendar.title")}`);
  out.push(`- ${L("kpi.total")}: ${d.d.counts.reduce((a, b) => a + b, 0)}`);
  out.push(`- ${L("kpi.peak")}: ${d.d.counts.length ? Math.max(...d.d.counts) : 0}`);
  out.push("");
  if (d.d.days.length) {
    out.push(...mdTable(
      [L("table.due"), L("table.days")],
      d.d.days.map((day, i) => [day, d.d.counts[i]]),
    ));
    out.push("");
  }

  out.push(`## ${L("chart.next_year.title")}`);
  const busy = d.yearHeat.days.filter(x => x.count > 0);
  out.push(`- ${L("copy.active_days")}: ${busy.length}/${d.yearHeat.days.length}`);
  if (busy.length) {
    out.push("");
    out.push(...mdTable([L("table.due"), L("kpi.total")], busy.slice(0, 60).map(x => [x.date, x.count])));
    if (busy.length > 60) out.push(`_+${busy.length - 60}_`);
    out.push("");
  }

  const lvlText = (r) => r.level
    ? r.level + (r.is_phrase ? ` ${L("words.phrase")}` : "")
    : (r.is_phrase ? `— ${L("words.phrase")}` : "—");

  out.push(`## ${L("chart.due_soon.title")}`);
  if (d.due.length) {
    out.push(...mdTable(
      [L("table.word"), L("table.translation"), L("table.level"), L("table.due"), L("table.days")],
      d.due.map(r => [mdCell(r.word), mdCell(r.translation), lvlText(r), r.due, r.days]),
    ));
  } else {
    out.push("—");
  }
  out.push("");

  out.push(`## ${L("chart.overdue.title")} (${d.over.length})`);
  if (d.over.length) {
    out.push(...mdTable(
      [L("table.word"), L("table.translation"), L("table.level"), L("table.due"), L("table.overdue_days")],
      d.over.slice(0, 30).map(r => [mdCell(r.word), mdCell(r.translation), lvlText(r), r.due, r.overdue_days]),
    ));
    if (d.over.length > 30) out.push(`_+${d.over.length - 30}_`);
  } else {
    out.push("—");
  }

  return out.join("\n");
}

function buildWordsMd(rows) {
  const L = (k) => I18N.t(k);
  const out = [];
  out.push(`# ${L("app.title")} — ${L("tabs.words")}`);
  out.push(`${L("copy.date")}: ${mdStamp()}`);

  const q = ($("#wordsSearch").value || "").trim();
  const lvl = $("#wordsLevel").value;
  const st = $("#wordsStatus").value;
  const filters = [];
  if (q) filters.push(`${L("words.search")}: ${q}`);
  if (lvl === "__unknown") filters.push(`${L("table.level")}: ${L("words.unknown_level")}`);
  else if (lvl) filters.push(`${L("table.level")}: ${lvl}`);
  if (st) filters.push(`${L("words.status_filter")}: ${L("kpi." + st)}`);
  if (filters.length) out.push(`${L("copy.filters")}: ${filters.join("; ")}`);
  out.push(`${L("kpi.total")}: ${rows.length}`);
  out.push("");

  out.push(...mdTable(
    [L("table.word"), L("table.translation"), L("table.level"), L("table.attempts"), L("table.easiness"), L("table.score"), L("table.context")],
    rows.map(r => {
      const lvlText = r.level ? r.level + (r.is_phrase ? ` ${L("words.phrase")}` : "") : (r.is_phrase ? `— ${L("words.phrase")}` : "—");
      const score = (r.attempts / Math.max(r.easiness, 0.1)).toFixed(1);
      let ctx = (r.contexts || "").split("|")[0].trim();
      if (ctx.length > 150) ctx = ctx.slice(0, 150) + "…";
      return [mdCell(r.word), mdCell(r.translation), lvlText, r.attempts, r.easiness.toFixed(2), score, mdCell(ctx)];
    }),
  ));

  return out.join("\n");
}

// ---------- Tabs ----------
$("#tabs").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (!btn) return;
  document.querySelectorAll("#tabs button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  document.querySelectorAll(".tab").forEach(s => s.hidden = true);
  $(`#tab-${btn.dataset.tab}`).hidden = false;
  render(btn.dataset.tab);
});

// ---------- Hotkeys ----------
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    const em = $("#editModal");
    if (em && !em.hidden) { e.preventDefault(); closeEditModal(); return; }
    const bm = $("#bulkModal");
    if (bm && !bm.hidden) { e.preventDefault(); closeBulkModal(); return; }
  }
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  const tabs = ["overview", "calendar", "words", "editor", "settings"];
  const idx = parseInt(e.key, 10) - 1;
  if (idx >= 0 && idx < tabs.length) {
    const btn = document.querySelector(`#tabs button[data-tab="${tabs[idx]}"]`);
    if (btn) btn.click();
  }
  if (e.key === "/") {
    e.preventDefault();
    const search = $("#wordsSearch") || $("#filter");
    if (search) search.focus();
  }
});

// ---------- Overview ----------
async function renderOverview() {
  const el = $("#tab-overview");
  el.innerHTML = `
    <div class="tab-actions">
      <button class="btn btn-secondary" id="copyOverview">${I18N.t("copy.button")}</button>
    </div>

    <div class="section-label">${I18N.t("group.status")}</div>
    <div class="grid" id="kpiGrid"></div>

    <div class="section-label">${I18N.t("group.quality")}</div>
    <div class="grid" id="qualityGrid"></div>

    <div class="section-label">${I18N.t("group.activity")}</div>
    <div class="grid" id="activityGrid"></div>

    <div class="charts-grid" style="margin-top:24px">
      <div class="chart-wrap"><h2>${I18N.t("chart.status.title")}</h2>
        <canvas id="statusChart"></canvas>${hint("chart.status.hint")}</div>
      <div class="chart-wrap"><h2>${I18N.t("chart.cefr_profile.title")}</h2>
        <canvas id="cefrChart"></canvas>${hint("chart.cefr_profile.hint")}</div>
      <div class="chart-wrap"><h2>${I18N.t("chart.cefr_ease.title")}</h2>
        <canvas id="cefrEaseChart"></canvas>${hint("chart.cefr_ease.hint")}</div>
      <div class="chart-wrap"><h2>${I18N.t("chart.intervals.title")}</h2>
        <canvas id="intervalsChart"></canvas>${hint("chart.intervals.hint")}</div>
      <div class="chart-wrap"><h2>${I18N.t("chart.easiness.title")}</h2>
        <canvas id="easChart"></canvas>${hint("chart.easiness.hint")}</div>
      <div class="chart-wrap"><h2>${I18N.t("chart.recall_ease.title")}</h2>
        <canvas id="recallEaseChart"></canvas>${hint("chart.recall_ease.hint")}</div>
      <div class="chart-wrap"><h2>${I18N.t("chart.weekly.title")}</h2>
        <canvas id="weekChart"></canvas>${hint("chart.weekly.hint")}</div>
      <div class="chart-wrap"><h2>${I18N.t("chart.time_of_day.title")}</h2>
        <canvas id="todChart"></canvas>${hint("chart.time_of_day.hint")}</div>
    </div>

    <div class="chart-wrap"><h2>${I18N.t("chart.velocity.title")}</h2>
      <canvas id="velChart"></canvas>${hint("chart.velocity.hint")}</div>

    <div class="chart-wrap"><h2>${I18N.t("chart.heatmap.title")}</h2>
      <div class="heatmap-wrap"><div class="heatmap" id="heatmap"></div></div>
      ${hint("chart.heatmap.hint")}</div>`;

  const [s, hist, vel, streak, heat, week, over, load, cefrP, cefrAvg, cefrEase, intervals, recallEase, tod, cost, conf] = await Promise.all([
    api("/api/stats/overview"),
    api("/api/stats/easiness-histogram"),
    api("/api/stats/velocity"),
    api("/api/stats/streak"),
    api("/api/stats/heatmap?days=365"),
    api("/api/stats/weekly?weeks=12"),
    api("/api/stats/overdue"),
    api("/api/stats/avg-load?days=30"),
    api("/api/stats/cefr-profile"),
    api("/api/stats/cefr-avg"),
    api("/api/stats/cefr-by-easiness"),
    api("/api/stats/interval-distribution"),
    api("/api/stats/recall-ease"),
    api("/api/stats/time-of-day"),
    api("/api/stats/avg-cost"),
    api("/api/settings"),
  ]);

  const cefrAvgText = cefrAvg.matched ? cefrAvg.avg.toFixed(2) : "—";
  const cefrAvgSub = cefrAvg.matched ? `${cefrAvg.matched} matched` : "";

  const matureHint = I18N.t("kpi.mature_hint").replace("{days}", conf.mature_days);
  const youngHint = I18N.t("kpi.young_hint")
    .replace("{young}", conf.young_days)
    .replace("{mature}", conf.mature_days);

  $("#kpiGrid").innerHTML = `
    <div class="card accent-blue" title="${I18N.t("kpi.total_hint")}"><h3>${I18N.t("kpi.total")}</h3><div class="value">${s.total}</div></div>
    <div class="card accent-green" title="${matureHint}"><h3>${I18N.t("kpi.mature")}</h3><div class="value">${s.by_status.mature || 0}</div><div class="sub">${s.mature_share}% ${I18N.t("kpi.of_all")}</div></div>
    <div class="card accent-blue" title="${youngHint}"><h3>${I18N.t("kpi.young")}</h3><div class="value">${s.by_status.young || 0}</div></div>
    <div class="card accent-yellow" title="${I18N.t("kpi.learning_hint")}"><h3>${I18N.t("kpi.learning")}</h3><div class="value">${s.by_status.learning || 0}</div></div>
    <div class="card accent-gray" title="${I18N.t("kpi.new_hint")}"><h3>${I18N.t("kpi.new")}</h3><div class="value">${s.by_status.new || 0}</div></div>`;

  $("#qualityGrid").innerHTML = `
    <div class="card accent-purple" title="${I18N.t("kpi.avg_easiness_hint")}"><h3>${I18N.t("kpi.avg_easiness")}</h3><div class="value">${s.avg_easiness}</div></div>
    <div class="card accent-red" title="${I18N.t("kpi.attempts_hint")}"><h3>${I18N.t("kpi.attempts")}</h3><div class="value">${s.total_attempts}</div></div>
    <div class="card accent-purple" title="${I18N.t("kpi.cefr_avg_hint")}"><h3>${I18N.t("kpi.cefr_avg")}</h3><div class="value">${cefrAvgText}</div><div class="sub">${cefrAvgSub}</div></div>
    <div class="card accent-purple" title="${I18N.t("kpi.avg_cost_hint")}"><h3>${I18N.t("kpi.avg_cost")}</h3><div class="value">${cost.avg}</div><div class="sub">${cost.count} ${I18N.t("kpi.avg_cost_sub")}</div></div>`;

  $("#activityGrid").innerHTML = `
    <div class="card accent-emerald" title="${I18N.t("kpi.streak_current_hint")}"><h3>${I18N.t("kpi.streak_current")}</h3><div class="value">${streak.current}</div></div>
    <div class="card accent-emerald" title="${I18N.t("kpi.streak_longest_hint")}"><h3>${I18N.t("kpi.streak_longest")}</h3><div class="value">${streak.longest}</div></div>
    <div class="card accent-red" title="${I18N.t("kpi.overdue_hint")}"><h3>${I18N.t("kpi.overdue")}</h3><div class="value">${over.length}</div></div>
    <div class="card accent-blue" title="${I18N.t("kpi.avg_load_hint")}"><h3>${I18N.t("kpi.avg_load")}</h3><div class="value">${load.avg}</div><div class="sub">${I18N.t("kpi.peak")} ${load.peak}</div></div>`;

  destroyChart("status");
  charts.status = new Chart($("#statusChart"), {
    type: "doughnut",
    plugins: [ChartDataLabels],
    data: {
      labels: [I18N.t("kpi.mature"), I18N.t("kpi.young"), I18N.t("kpi.learning"), I18N.t("kpi.new")],
      datasets: [{
        data: [s.by_status.mature || 0, s.by_status.young || 0, s.by_status.learning || 0, s.by_status.new || 0],
        backgroundColor: [THEME.good, THEME.accent, THEME.warn, THEME.muted],
        borderWidth: 0,
      }],
    },
    options: {
      plugins: {
        legend: { position: "right" },
        datalabels: {
          color: "#e6edf3",
          textStrokeColor: "rgba(0, 0, 0, 0.55)",
          textStrokeWidth: 3,
          font: { size: 13, weight: "700" },
          formatter: (v, ctx) => {
            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
            if (!v || !total) return "";
            return v / total >= 0.05 ? v : "";
          },
        },
      },
      cutout: "60%",
    },
  });

  destroyChart("cefr");
  charts.cefr = new Chart($("#cefrChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: cefrP.labels,
      datasets: [{
        label: I18N.t("chart.cefr_profile.title"),
        data: cefrP.counts,
        backgroundColor: cefrP.labels.map(l => LEVEL_COLORS[l]),
        borderRadius: 6,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: { ...DL },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => ctx.dataIndex === cefrP.labels.length - 1 ? `${I18N.t("words.unknown_level")}: ${cefrP.unknown}` : "",
          },
        },
      },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  destroyChart("cefrEase");
  charts.cefrEase = new Chart($("#cefrEaseChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: cefrEase.map(r => r.level),
      datasets: [{
        label: I18N.t("chart.cefr_ease.title"),
        data: cefrEase.map(r => r.avg_easiness),
        backgroundColor: cefrEase.map(r => LEVEL_COLORS[r.level]),
        borderRadius: 6,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: { ...DL, formatter: (v) => (v > 0 ? v.toFixed(2) : "") },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => `${cefrEase[ctx.dataIndex].count} words`,
          },
        },
      },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  destroyChart("intervals");
  charts.intervals = new Chart($("#intervalsChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: intervals.labels,
      datasets: [{
        label: I18N.t("chart.intervals.title"),
        data: intervals.counts,
        backgroundColor: THEME.purple,
        borderRadius: 6,
      }],
    },
    options: {
      plugins: { legend: { display: false }, datalabels: { ...DL } },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  destroyChart("eas");
  charts.eas = new Chart($("#easChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: hist.labels,
      datasets: [{
        label: I18N.t("chart.easiness.title"),
        data: hist.counts,
        backgroundColor: hist.labels.map((_, i) => i < 2 ? THEME.bad : i < 3 ? THEME.warn : THEME.good),
        borderRadius: 6,
      }],
    },
    options: {
      plugins: { legend: { display: false }, datalabels: { ...DL } },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  destroyChart("recallEase");
  charts.recallEase = new Chart($("#recallEaseChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: recallEase.labels,
      datasets: [{
        label: I18N.t("chart.recall_ease.title"),
        data: recallEase.counts,
        backgroundColor: recallEase.labels.map((_, i) => i < 2 ? THEME.bad : i < 4 ? THEME.warn : THEME.good),
        borderRadius: 6,
      }],
    },
    options: {
      plugins: { legend: { display: false }, datalabels: { ...DL } },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  destroyChart("vel");
  charts.vel = new Chart($("#velChart"), {
    type: "line",
    data: {
      labels: vel.days,
      datasets: [{
        label: I18N.t("chart.velocity.title"),
        data: vel.cumulative,
        borderColor: THEME.emerald,
        backgroundColor: "rgba(57, 211, 83, 0.08)",
        tension: .3, fill: true,
        pointRadius: 0, pointHoverRadius: 5,
      }],
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });

  drawHeatmap($("#heatmap"), heat.days);

  destroyChart("week");
  charts.week = new Chart($("#weekChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: week.weeks,
      datasets: [{
        label: I18N.t("chart.weekly.title"),
        data: week.counts,
        backgroundColor: THEME.accent,
        borderRadius: 6,
      }],
    },
    options: {
      plugins: { legend: { display: false }, datalabels: { ...DL } },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  destroyChart("tod");
  charts.tod = new Chart($("#todChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: tod.labels,
      datasets: [{
        label: I18N.t("chart.time_of_day.title"),
        data: tod.counts,
        backgroundColor: THEME.emerald,
        borderRadius: 4,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: { ...DL, font: { size: 9, weight: "600" }, offset: 2 },
      },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  $("#copyOverview").addEventListener("click", () => {
    const md = buildOverviewMd({ s, hist, vel, streak, heat, week, over, load, cefrP, cefrAvg, cefrEase, intervals, recallEase, tod, cost });
    copyToClipboard(md);
  });
}

// ---------- Heatmap (GitHub-style) ----------
function drawHeatmap(container, days) {
  if (!container || !days.length) return;

  const first = new Date(days[0].date + "T00:00:00Z");
  const dow = (first.getUTCDay() + 6) % 7; // 0 = Monday
  const padded = Array(dow).fill(null).concat(days);
  const weeks = Math.ceil(padded.length / 7);

  // Size cells so the grid fills the container width.
  // 6px min (readability), 22px max (otherwise it looks silly on ultrawide).
  const wrap = container.parentElement;
  const availW = (wrap ? wrap.clientWidth : 900) - 4;
  const gap = 3;
  const rawCell = Math.floor((availW - (weeks - 1) * gap) / weeks);
  const cell = Math.max(6, Math.min(22, rawCell));
  container.style.gridTemplateRows = `repeat(7, ${cell}px)`;
  container.style.gridAutoColumns = `${cell}px`;
  container.style.gap = `${gap}px`;

  const maxCount = Math.max(...days.map(d => d.count), 1);
  const levelOf = (c) => {
    if (!c) return "hm-l0";
    const r = c / maxCount;
    if (r < 0.25) return "hm-l1";
    if (r < 0.5) return "hm-l2";
    if (r < 0.75) return "hm-l3";
    return "hm-l4";
  };

  container.innerHTML = "";
  const frag = document.createDocumentFragment();
  padded.forEach((d) => {
    const el = document.createElement("div");
    if (!d) {
      el.className = "hm-cell hm-empty";
    } else {
      el.className = `hm-cell ${levelOf(d.count)}`;
      el.title = `${d.date}: ${d.count}`;
    }
    frag.appendChild(el);
  });
  container.appendChild(frag);
}

// ---------- Calendar ----------
async function renderCalendar() {
  const el = $("#tab-calendar");
  el.innerHTML = `
    <div class="tab-actions">
      <button class="btn btn-secondary" id="copyCalendar">${I18N.t("copy.button")}</button>
    </div>

    <div class="chart-wrap"><h2>${I18N.t("chart.calendar.title")}</h2>
      <canvas id="calChart"></canvas>${hint("chart.calendar.hint")}</div>
    <div class="chart-wrap"><h2>${I18N.t("chart.next_year.title")}</h2>
      <div class="heatmap-wrap"><div class="heatmap" id="yearHeatmap"></div></div>
      ${hint("chart.next_year.hint")}</div>
    <div class="chart-wrap"><h2>${I18N.t("chart.due_soon.title")}</h2>
      <table id="dueTable"></table>${hint("chart.due_soon.hint")}</div>
    <div class="chart-wrap"><h2>${I18N.t("chart.overdue.title")}</h2>
      <table id="overdueTable"></table>${hint("chart.overdue.hint")}</div>`;

  const [d, due, over, yearHeat] = await Promise.all([
    api("/api/stats/srs?days=60"),
    api("/api/stats/due-soon?days=1"),
    api("/api/stats/overdue"),
    api("/api/stats/next-year-heatmap?days=365"),
  ]);

  drawHeatmap($("#yearHeatmap"), yearHeat.days);

  destroyChart("cal");
  charts.cal = new Chart($("#calChart"), {
    type: "bar",
    plugins: [ChartDataLabels],
    data: {
      labels: d.days,
      datasets: [{
        label: I18N.t("chart.calendar.title"),
        data: d.counts,
        backgroundColor: THEME.accent,
        borderRadius: 4,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: { ...DL, font: { size: 9, weight: "600" }, offset: 2 },
      },
      scales: { y: { beginAtZero: true, grace: "15%" } },
    },
  });

  const header = `<tr><th>${I18N.t("table.word")}</th><th>${I18N.t("table.translation")}</th><th>${I18N.t("table.level")}</th><th>${I18N.t("table.due")}</th><th>${I18N.t("table.days")}</th></tr>`;
  if (!due.length) {
    $("#dueTable").innerHTML = header + `<tr><td colspan="5" class="muted">—</td></tr>`;
  } else {
    $("#dueTable").innerHTML = header + due.map(r => {
      const badge = r.days === 0 ? `<span class="due-badge today">${r.due}</span>` : `<span class="due-badge tomorrow">${r.due}</span>`;
      return `<tr><td>${escapeHtml(r.word)}</td><td>${escapeHtml(r.translation)}</td><td>${levelBadge(r.level, r.is_phrase)}</td><td>${badge}</td><td>${r.days}</td></tr>`;
    }).join("");
  }

  const overHeader = `<tr><th>${I18N.t("table.word")}</th><th>${I18N.t("table.translation")}</th><th>${I18N.t("table.level")}</th><th>${I18N.t("table.due")}</th><th>${I18N.t("table.overdue_days")}</th></tr>`;
  if (!over.length) {
    $("#overdueTable").innerHTML = overHeader + `<tr><td colspan="5" class="muted">—</td></tr>`;
  } else {
    $("#overdueTable").innerHTML = overHeader + over.map(r =>
      `<tr><td>${escapeHtml(r.word)}</td><td>${escapeHtml(r.translation)}</td><td>${levelBadge(r.level, r.is_phrase)}</td><td>${r.due}</td><td>${r.overdue_days}</td></tr>`
    ).join("");
  }

  $("#copyCalendar").addEventListener("click", () => {
    const md = buildCalendarMd({ d, due, over, yearHeat });
    copyToClipboard(md);
  });
}

// ---------- Words ----------
let scatterCache = [];

async function renderWords() {
  const el = $("#tab-words");
  const levelOptions = [`<option value="">${I18N.t("words.level_filter")}</option>`]
    .concat(LEVELS.map(l => `<option value="${l}">${l}</option>`))
    .concat([`<option value="__unknown">${I18N.t("words.unknown_level")}</option>`])
    .join("");

  const statusOptions = [`<option value="">${I18N.t("words.status_filter")}</option>`]
    .concat(["mature", "young", "learning", "new"].map(s =>
      `<option value="${s}">${I18N.t("kpi." + s)}</option>`
    ))
    .join("");

  const xAxisOptions = [
    ["attempts", I18N.t("words.x_attempts")],
    ["word_length", I18N.t("words.x_word_length")],
    ["context_length", I18N.t("words.x_context_length")],
  ].map(([v, label]) => {
    const selected = v === scatterXAxis ? " selected" : "";
    return `<option value="${v}"${selected}>${label}</option>`;
  }).join("");

  el.innerHTML = `
    <div class="tab-actions">
      <button class="btn btn-secondary" id="copyWords">${I18N.t("copy.button")}</button>
    </div>

    <div class="chart-wrap">
      <div class="filters-row">
        <input id="wordsSearch" data-i18n-placeholder="words.search" placeholder="${I18N.t("words.search")}" />
        <select id="wordsLevel">${levelOptions}</select>
        <select id="wordsStatus">${statusOptions}</select>
      </div>
    </div>
    <div class="chart-wrap"><h2>${I18N.t("chart.scatter.title")}</h2>
      <div class="row" style="margin-bottom:12px">
        <div></div>
        <div style="display:flex;align-items:center;gap:8px">
          <label class="muted" style="font-size:12px;text-transform:uppercase;letter-spacing:.5px">${I18N.t("words.x_axis")}</label>
          <select id="scatterXAxis">${xAxisOptions}</select>
        </div>
      </div>
      <canvas id="scatterChart"></canvas>${hint("chart.scatter.hint")}</div>
    <div class="chart-wrap"><h2>${I18N.t("chart.difficult.title")}</h2>
      <table id="wordsTable"></table>
      <div class="pagination" id="wordsPagination"></div>
      ${hint("chart.difficult.hint")}</div>`;

  scatterCache = await api("/api/stats/scatter");
  wordsSortKey = "score";
  wordsSortDir = "desc";
  wordsStatusFilter = "";
  wordsPage = 1;

  const resetAndDraw = () => { wordsPage = 1; drawWordsPage(); };

  $("#wordsSearch").addEventListener("input", resetAndDraw);
  $("#wordsLevel").addEventListener("change", resetAndDraw);
  $("#wordsStatus").addEventListener("change", resetAndDraw);
  $("#scatterXAxis").addEventListener("change", (e) => {
    scatterXAxis = e.target.value;
    drawWordsPage();
  });

  $("#copyWords").addEventListener("click", () => {
    const filtered = getFilteredWords();
    const sorted = sortWords(filtered, wordsSortKey, wordsSortDir);
    copyToClipboard(buildWordsMd(sorted));
  });

  drawWordsPage();
}

function getFilteredWords() {
  const q = ($("#wordsSearch").value || "").toLowerCase();
  const lvl = $("#wordsLevel").value;
  const st = $("#wordsStatus").value;

  let filtered = scatterCache.filter(w =>
    !q ||
    w.word.toLowerCase().includes(q) ||
    w.translation.toLowerCase().includes(q) ||
    (w.contexts || "").toLowerCase().includes(q)
  );
  if (lvl === "__unknown") filtered = filtered.filter(w => !w.level);
  else if (lvl) filtered = filtered.filter(w => w.level === lvl);
  if (st) filtered = filtered.filter(w => w.status === st);
  return filtered;
}

function drawWordsPage() {
  const filtered = getFilteredWords();
  const sorted = sortWords(filtered, wordsSortKey, wordsSortDir);
  const total = sorted.length;

  // Scatter — по всем отфильтрованным, независимо от страницы
  drawScatter(sorted);

  const pageSize = wordsPageSize || total || 1;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (wordsPage > totalPages) wordsPage = totalPages;
  if (wordsPage < 1) wordsPage = 1;

  const from = (wordsPage - 1) * pageSize;
  const to = Math.min(from + pageSize, total);
  const slice = sorted.slice(from, to);

  drawWordsTable(slice);
  renderPagination(from, to, total, totalPages);
}

function renderPagination(from, to, total, totalPages) {
  const el = $("#wordsPagination");
  if (!el) return;

  const sizeOptions = [50, 100, 250, 500, 0].map(s => {
    const label = s === 0 ? I18N.t("words.page_all") : s;
    const selected = s === wordsPageSize ? " selected" : "";
    return `<option value="${s}"${selected}>${label}</option>`;
  }).join("");

  const info = total === 0 ? "0 / 0" : `${from + 1}–${to} / ${total}`;

  el.innerHTML = `
    <div class="page-size">
      <label>${I18N.t("words.per_page")}</label>
      <select id="wordsPageSize">${sizeOptions}</select>
    </div>
    <button id="wordsPrev" ${wordsPage <= 1 ? "disabled" : ""}>←</button>
    <span class="page-info">${info}</span>
    <button id="wordsNext" ${wordsPage >= totalPages ? "disabled" : ""}>→</button>`;

  $("#wordsPageSize").addEventListener("change", (e) => {
    wordsPageSize = parseInt(e.target.value, 10) || 0;
    wordsPage = 1;
    drawWordsPage();
  });
  $("#wordsPrev").addEventListener("click", () => {
    if (wordsPage > 1) { wordsPage--; drawWordsPage(); }
  });
  $("#wordsNext").addEventListener("click", () => {
    if (wordsPage < totalPages) { wordsPage++; drawWordsPage(); }
  });
}

function drawScatter(rows) {
  destroyChart("scatter");
  const xKey = scatterXAxis; // "attempts" | "word_length" | "context_length"
  const xLabel = xKey === "word_length" ? I18N.t("words.x_word_length")
    : xKey === "context_length" ? I18N.t("words.x_context_length")
    : I18N.t("words.x_attempts");
  const points = rows.map(r => ({
    x: r[xKey] ?? 0,
    y: r.easiness,
    word: r.word,
    translation: r.translation,
    level: r.level,
    is_phrase: r.is_phrase,
  }));
  charts.scatter = new Chart($("#scatterChart"), {
    type: "scatter",
    data: {
      datasets: [{
        label: I18N.t("chart.scatter.title"),
        data: points,
        backgroundColor: points.map(p => p.level ? LEVEL_COLORS[p.level] : (p.y < 1.8 ? THEME.bad : p.y < 2.2 ? THEME.warn : THEME.good)),
        pointRadius: 5, pointHoverRadius: 8,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const lvl = ctx.raw.level || "—";
              const phr = ctx.raw.is_phrase ? ` (${I18N.t("words.phrase")})` : "";
              return `${ctx.raw.word} — ${ctx.raw.translation} · ${lvl}${phr} · ${xLabel}: ${ctx.raw.x}, ${ctx.raw.y.toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        x: { title: { display: true, text: xLabel }, beginAtZero: true },
        y: { title: { display: true, text: I18N.t("table.easiness") }, beginAtZero: true },
      },
    },
  });
}

function renderContextCell(contexts, word) {
  if (!contexts) return `<span class="muted">—</span>`;
  const first = contexts.split("|")[0].trim();
  if (!first) return `<span class="muted">—</span>`;
  const truncated = first.length > 220 ? first.slice(0, 220) + "…" : first;
  const idx = truncated.toLowerCase().indexOf((word || "").toLowerCase());
  if (idx === -1) return `<span class="ctx-cell">${escapeHtml(truncated)}</span>`;
  const before = escapeHtml(truncated.slice(0, idx));
  const hit = escapeHtml(truncated.slice(idx, idx + word.length));
  const after = escapeHtml(truncated.slice(idx + word.length));
  return `<span class="ctx-cell">${before}<mark class="context-hit">${hit}</mark>${after}</span>`;
}

function sortWords(rows, key, dir) {
  const cmp = (a, b) => {
    let av, bv;
    if (key === "level") {
      av = a.level ? LEVEL_RANK[a.level] : 99;
      bv = b.level ? LEVEL_RANK[b.level] : 99;
    } else if (key === "score") {
      av = a.attempts / Math.max(a.easiness, 0.1);
      bv = b.attempts / Math.max(b.easiness, 0.1);
    } else if (key === "word" || key === "translation") {
      av = (a[key] || "").toLowerCase();
      bv = (b[key] || "").toLowerCase();
    } else {
      av = a[key] ?? 0;
      bv = b[key] ?? 0;
    }
    if (av < bv) return dir === "asc" ? -1 : 1;
    if (av > bv) return dir === "asc" ? 1 : -1;
    return 0;
  };
  return [...rows].sort(cmp);
}

function drawWordsTable(rows) {
  const sorted = sortWords(rows, wordsSortKey, wordsSortDir);
  const arrow = (k) => wordsSortKey === k ? `data-dir="${wordsSortDir}"` : "";
  const header = `<tr>
    <th class="sortable" data-sort="word" ${arrow("word")}>${I18N.t("table.word")}</th>
    <th class="sortable" data-sort="translation" ${arrow("translation")}>${I18N.t("table.translation")}</th>
    <th class="sortable" data-sort="level" ${arrow("level")}>${I18N.t("table.level")}</th>
    <th class="sortable" data-sort="attempts" ${arrow("attempts")}>${I18N.t("table.attempts")}</th>
    <th class="sortable" data-sort="easiness" ${arrow("easiness")}>${I18N.t("table.easiness")}</th>
    <th class="sortable" data-sort="score" ${arrow("score")} title="${I18N.t("table.score_hint")}">${I18N.t("table.score")}</th>
    <th>${I18N.t("table.context")}</th>
  </tr>`;

  const body = sorted.length
    ? sorted.map(r => {
        const phr = r.is_phrase ? `<span class="phrase-badge">${I18N.t("words.phrase")}</span>` : "";
        const lvl = r.level
          ? `<span class="level-badge level-${r.level}">${r.level}</span>${phr}`
          : (r.is_phrase ? `<span class="muted">—</span>${phr}` : `<span class="muted">—</span>`);
        const score = (r.attempts / Math.max(r.easiness, 0.1)).toFixed(1);
        return `<tr>
          <td>${escapeHtml(r.word)}</td>
          <td>${escapeHtml(r.translation)}</td>
          <td>${lvl}</td>
          <td>${r.attempts}</td>
          <td>${r.easiness.toFixed(2)}</td>
          <td>${score}</td>
          <td>${renderContextCell(r.contexts, r.word)}</td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="7" class="muted">—</td></tr>`;

  $("#wordsTable").innerHTML = header + body;

  document.querySelectorAll("#wordsTable th.sortable").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (wordsSortKey === key) {
        wordsSortDir = wordsSortDir === "asc" ? "desc" : "asc";
      } else {
        wordsSortKey = key;
        wordsSortDir = (key === "word" || key === "translation") ? "asc" : "desc";
      }
      wordsPage = 1;
      drawWordsPage();
    });
  });
}

// ---------- Editor (table + modal) ----------
let wordsCache = [];

async function renderEditor() {
  const el = $("#tab-editor");
  wordsCache = await api("/api/words");
  el.innerHTML = `<div class="chart-wrap">
    <div class="editor-header">
      <h2>${I18N.t("editor.title")}</h2>
      <div class="editor-actions">
        <button class="btn btn-secondary" id="exportJsonBtn">${I18N.t("editor.export_json")}</button>
        <button class="btn" id="importJsonBtn">${I18N.t("editor.import_json")}</button>
      </div>
    </div>
    <input id="filter" data-i18n-placeholder="editor.filter" placeholder="${I18N.t("editor.filter")}" />
    <div id="wordList" style="margin-top:14px"></div>
  </div>`;
  $("#filter").addEventListener("input", drawEditorList);
  $("#exportJsonBtn").addEventListener("click", exportEditorJson);
  $("#importJsonBtn").addEventListener("click", openBulkModal);
  drawEditorList();
}

async function exportEditorJson() {
  // Export the currently filtered set, sorted by difficulty (desc),
  // ready to be handed to an LLM. No `new_word` field in the export —
  // the LLM adds it only if it wants to rename.
  const src = editorFilteredWords();
  const scoreOf = (w) => {
    const attempts = parseInt(w.spaced_repetition_recall_attempts, 10) || 0;
    const ease = parseFloat(w.spaced_repetition_easiness_factor) || 2.5;
    return attempts / Math.max(ease, 0.1);
  };
  const sorted = [...src].sort((a, b) => scoreOf(b) - scoreOf(a));
  const payload = sorted.map(w => ({
    word: w.word,
    translation: w.translation,
    contexts: w.contexts,
  }));
  await copyToClipboard(JSON.stringify(payload, null, 2));
}

function drawEditorList() {
  const q = ($("#filter").value || "").toLowerCase();
  const list = $("#wordList");
  const header = `<tr>
    <th>${I18N.t("table.word")}</th>
    <th>${I18N.t("table.translation")}</th>
    <th>${I18N.t("table.level")}</th>
    <th>${I18N.t("table.context")}</th>
    <th style="width:60px;text-align:right"></th>
  </tr>`;

  const rows = wordsCache
    .map((w, i) => ({ w, i }))
    .filter(({ w }) => !q || w.word.toLowerCase().includes(q) || w.translation.toLowerCase().includes(q))
    .map(({ w, i }) => {
      const phr = w.is_phrase ? `<span class="phrase-badge">${I18N.t("words.phrase")}</span>` : "";
      const lvl = w.level
        ? `<span class="level-badge level-${w.level}">${w.level}</span>${phr}`
        : (w.is_phrase ? `<span class="muted">—</span>${phr}` : `<span class="muted">—</span>`);
      return `<tr>
        <td>${escapeHtml(w.word)}</td>
        <td>${escapeHtml(w.translation)}</td>
        <td>${lvl}</td>
        <td>${renderContextCell(w.contexts, w.word)}</td>
        <td style="text-align:right"><button class="icon-btn" data-edit="${i}" title="${I18N.t("editor.edit")}">⚙</button></td>
      </tr>`;
    }).join("");

  list.innerHTML = `<table>${header}${rows || `<tr><td colspan="5" class="muted">—</td></tr>`}</table>`;

  list.querySelectorAll("button[data-edit]").forEach(btn => {
    btn.addEventListener("click", () => openEditModal(parseInt(btn.dataset.edit, 10)));
  });
}

function openEditModal(idx) {
  editingIdx = idx;
  const w = wordsCache[idx];
  if (!w) return;
  $("#modalTitle").textContent = w.word || I18N.t("editor.edit");
  $("#modalWord").value = w.word || "";
  $("#modalTranslation").value = w.translation || "";
  $("#modalContexts").value = w.contexts || "";
  updateModalPreview();
  $("#editModal").hidden = false;
  $("#modalWord").focus();
}

function closeEditModal() {
  editingIdx = null;
  $("#editModal").hidden = true;
}

function updateModalPreview() {
  const block = $("#modalPreview");
  const needle = ($("#modalWord").value || "").trim();
  const hay = $("#modalContexts").value || "";
  if (!needle || !hay) { block.innerHTML = ""; return; }
  const idx = hay.toLowerCase().indexOf(needle.toLowerCase());
  if (idx === -1) {
    block.innerHTML = `<span class="preview-bad">${I18N.t("editor.not_in_context")}</span>`;
    return;
  }
  const before = escapeHtml(hay.slice(0, idx));
  const hit = escapeHtml(hay.slice(idx, idx + needle.length));
  const after = escapeHtml(hay.slice(idx + needle.length));
  block.innerHTML = `${before}<mark class="context-hit">${hit}</mark>${after}`;
}

async function saveEditModal() {
  if (editingIdx === null) return;
  const payload = {
    word: $("#modalWord").value,
    translation: $("#modalTranslation").value,
    contexts: $("#modalContexts").value,
  };
  try {
    const r = await api(`/api/words/${editingIdx}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    wordsCache[editingIdx] = r.word;
    toast(I18N.t("toast.saved"));
    closeEditModal();
    drawEditorList();
  } catch (e) {
    toast(e.message, "error");
  }
}

// Wire modal buttons once.
$("#modalCancel").addEventListener("click", closeEditModal);
$("#modalSave").addEventListener("click", saveEditModal);
$("#modalWord").addEventListener("input", updateModalPreview);
$("#modalContexts").addEventListener("input", updateModalPreview);
$("#editModal").addEventListener("click", (e) => {
  if (e.target === $("#editModal")) closeEditModal();
});

// ---------- Bulk edit (paste JSON → diff → apply) ----------
let bulkState = {
  rows: [],         // {word, field, before, after, checked, status}
  unanchored: [],   // original word values from LLM that aren't in the dictionary
  filter: "all",    // "all" | "conflicts" | "word" | "translation" | "contexts"
  page: 1,
  pageSize: 100,
};

function openBulkModal() {
  bulkState = { rows: [], unanchored: [], filter: "all", page: 1, pageSize: 100 };
  $("#bulkInput").value = "";
  $("#bulkPreviewStep").hidden = true;
  $("#bulkPreview").innerHTML = "";
  $("#bulkSummary").innerHTML = "";
  $("#bulkConflicts").innerHTML = "";
  $("#bulkUnanchored").innerHTML = "";
  $("#bulkPagination").innerHTML = "";
  updateBulkApplyButton();
  $("#bulkModal").hidden = false;
  $("#bulkInput").focus();
}

function closeBulkModal() {
  $("#bulkModal").hidden = true;
}

function editorFilteredWords() {
  const q = ($("#filter").value || "").toLowerCase();
  return wordsCache.filter(w =>
    !q || w.word.toLowerCase().includes(q) || w.translation.toLowerCase().includes(q)
  );
}

function bulkParse() {
  const raw = $("#bulkInput").value.trim();
  if (!raw) return;
  const cleaned = raw.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();
  let parsed;
  try {
    parsed = JSON.parse(cleaned);
  } catch (e) {
    toast(I18N.t("bulk.parse_error").replace("{msg}", e.message), "error");
    return;
  }
  if (!Array.isArray(parsed)) {
    toast(I18N.t("bulk.parse_error").replace("{msg}", "expected top-level array"), "error");
    return;
  }

  const byWord = new Map(wordsCache.map(w => [w.word, w]));
  const rows = [];
  const unanchored = [];
  const seenNewWords = new Set();

  parsed.forEach(item => {
    if (!item || typeof item !== "object") return;
    const anchor = typeof item.word === "string" ? item.word : null;
    if (!anchor) return;

    const old = byWord.get(anchor);
    if (!old) {
      unanchored.push(anchor);
      return;
    }

    const finalWord = (item.new_word && String(item.new_word).trim()) || old.word;
    const finalCtx = item.contexts !== undefined && item.contexts !== null
      ? String(item.contexts)
      : old.contexts;

    // Rename — only if new_word actually differs from the anchor.
    if (
      item.new_word !== undefined &&
      item.new_word !== null &&
      String(item.new_word).trim() !== "" &&
      String(item.new_word).trim() !== old.word
    ) {
      const nw = String(item.new_word).trim();
      let status = "ok";
      if (seenNewWords.has(nw.toLowerCase())) status = "duplicate";
      else if (wordsCache.some(w => w.word !== old.word && w.word.toLowerCase() === nw.toLowerCase())) status = "duplicate";
      else if (finalCtx && !finalCtx.toLowerCase().includes(nw.toLowerCase())) status = "not_in_context";

      rows.push({ word: old.word, field: "word", before: old.word, after: nw, checked: status === "ok", status });
      if (status === "ok") seenNewWords.add(nw.toLowerCase());
    }

    // Translation
    if (item.translation !== undefined && item.translation !== null && item.translation !== old.translation) {
      rows.push({ word: old.word, field: "translation", before: old.translation, after: String(item.translation), checked: true, status: "ok" });
    }

    // Contexts
    if (item.contexts !== undefined && item.contexts !== null && item.contexts !== old.contexts) {
      const ctx = String(item.contexts);
      let status = "ok";
      if (!ctx.trim()) status = "empty";
      else if (!ctx.toLowerCase().includes(finalWord.toLowerCase())) status = "not_in_context";
      rows.push({ word: old.word, field: "contexts", before: old.contexts, after: ctx, checked: status === "ok", status });
    }
  });

  bulkState = { rows, unanchored, filter: "all", page: 1, pageSize: 100 };
  renderBulkPreview();
}

// --- char-level diff (LCS) ---
function escapeChar(c) {
  return c.replace(/[&<>"']/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
}

function charDiff(a, b) {
  if (a === b) return [{ t: "same", s: a }];
  if (a.length > 2000 || b.length > 2000) {
    const out = [];
    if (a) out.push({ t: "del", s: a });
    if (b) out.push({ t: "add", s: b });
    return out;
  }
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (a[i] === b[j]) dp[i][j] = dp[i + 1][j + 1] + 1;
      else dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const ops = [];
  let i = 0, j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) { ops.push({ t: "same", s: a[i] }); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { ops.push({ t: "del", s: a[i] }); i++; }
    else { ops.push({ t: "add", s: b[j] }); j++; }
  }
  while (i < m) { ops.push({ t: "del", s: a[i] }); i++; }
  while (j < n) { ops.push({ t: "add", s: b[j] }); j++; }
  return ops;
}

function renderInlineDiff(before, after) {
  const ops = charDiff(before, after);
  return ops.map(op => {
    const s = escapeChar(op.s);
    if (op.t === "same") return `<span class="diff-same">${s}</span>`;
    if (op.t === "del") return `<span class="diff-del">${s}</span>`;
    return `<span class="diff-add">${s}</span>`;
  }).join("");
}

function bulkFilteredRows() {
  return bulkState.rows
    .map((r, i) => ({ ...r, _i: i }))
    .filter(r => {
      const f = bulkState.filter;
      if (f === "all") return true;
      if (f === "conflicts") return r.status !== "ok";
      return r.field === f;
    });
}

function renderBulkPreview() {
  $("#bulkPreviewStep").hidden = false;
  renderBulkSummary();
  renderBulkConflicts();
  renderBulkUnanchored();
  renderBulkPage();
  updateBulkApplyButton();
}

function renderBulkSummary() {
  const total = bulkState.rows.length;
  const conflicts = bulkState.rows.filter(r => r.status !== "ok").length;
  const byField = { word: 0, translation: 0, contexts: 0 };
  bulkState.rows.forEach(r => { byField[r.field] = (byField[r.field] || 0) + 1; });

  const chip = (filter, label, count, warn) => {
    const active = bulkState.filter === filter ? " active" : "";
    const warnCls = warn && count > 0 ? " warn" : "";
    return `<span class="bulk-chip${active}${warnCls}" data-filter="${filter}">${label}: ${count}</span>`;
  };

  const html = [
    chip("all", I18N.t("bulk.filter_all"), total, false),
    conflicts > 0 ? chip("conflicts", "⚠ " + I18N.t("bulk.filter_conflicts"), conflicts, true) : "",
    byField.word ? chip("word", I18N.t("table.word"), byField.word, false) : "",
    byField.translation ? chip("translation", I18N.t("table.translation"), byField.translation, false) : "",
    byField.contexts ? chip("contexts", I18N.t("table.context"), byField.contexts, false) : "",
  ].filter(Boolean).join("");

  $("#bulkSummary").innerHTML = html;

  $("#bulkSummary").querySelectorAll(".bulk-chip").forEach(el => {
    el.addEventListener("click", () => {
      bulkState.filter = el.dataset.filter;
      bulkState.page = 1;
      renderBulkPreview();
    });
  });
}

function renderBulkConflicts() {
  const conflicts = bulkState.rows.filter(r => r.status !== "ok").length;
  if (!conflicts) { $("#bulkConflicts").innerHTML = ""; return; }
  $("#bulkConflicts").innerHTML = `<div class="bulk-conflict-warn">${I18N.t("bulk.conflicts").replace("{n}", conflicts)}</div>`;
}

function renderBulkUnanchored() {
  const list = bulkState.unanchored;
  if (!list.length) { $("#bulkUnanchored").innerHTML = ""; return; }
  const sample = list.slice(0, 10).map(escapeHtml).join(", ");
  const more = list.length > 10 ? ` +${list.length - 10}` : "";
  $("#bulkUnanchored").innerHTML = `<div class="bulk-unanchored-warn">
    ${I18N.t("bulk.unanchored").replace("{n}", list.length)}<br>
    <span class="muted">${I18N.t("bulk.unanchored_list")} ${sample}${more}</span>
  </div>`;
}

function renderBulkPage() {
  const filtered = bulkFilteredRows();
  const pageSize = bulkState.pageSize;
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  if (bulkState.page > totalPages) bulkState.page = totalPages;
  if (bulkState.page < 1) bulkState.page = 1;

  const from = (bulkState.page - 1) * pageSize;
  const to = Math.min(from + pageSize, filtered.length);
  const slice = filtered.slice(from, to);

  if (!bulkState.rows.length) {
    $("#bulkPreview").innerHTML = `<p class="muted">${I18N.t("bulk.no_changes")}</p>`;
    $("#bulkPagination").innerHTML = "";
    return;
  }
  if (!slice.length) {
    $("#bulkPreview").innerHTML = `<p class="muted">—</p>`;
    renderBulkPagination(0, 0, 0, 1);
    return;
  }

  const header = `<tr>
    <th style="width:32px"></th>
    <th>${I18N.t("table.word")}</th>
    <th>${I18N.t("bulk.field")}</th>
    <th>${I18N.t("bulk.diff")}</th>
    <th>${I18N.t("bulk.new_value")}</th>
  </tr>`;

  const fieldLabel = (f) => f === "word" ? I18N.t("table.word")
    : f === "translation" ? I18N.t("table.translation")
    : I18N.t("table.context");

  const statusTag = (r) => {
    if (r.status === "ok") return "";
    if (r.status === "empty") return `<span class="bulk-status bad">${I18N.t("bulk.status_empty")}</span>`;
    if (r.status === "duplicate") return `<span class="bulk-status bad">${I18N.t("bulk.status_duplicate")}</span>`;
    if (r.status === "not_in_context") return `<span class="bulk-status warn">${I18N.t("bulk.status_not_in_context")}</span>`;
    return "";
  };

  const rowCls = (r) => r.status === "ok" ? "" : (r.status === "not_in_context" ? "row-warn" : "row-bad");

  const body = slice.map(r => {
    const i = r._i;
    const diff = renderInlineDiff(r.before, r.after);
    return `<tr class="${rowCls(r)}">
      <td><input type="checkbox" data-bidx="${i}" ${r.checked ? "checked" : ""}></td>
      <td>${escapeHtml(r.word)}</td>
      <td>${fieldLabel(r.field)}${statusTag(r)}</td>
      <td class="diff-cell"><div class="diff-text">${diff}</div></td>
      <td><textarea class="diff-textarea" data-bidx="${i}">${escapeHtml(r.after)}</textarea></td>
    </tr>`;
  }).join("");

  $("#bulkPreview").innerHTML = `<table class="diff-table">${header}${body}</table>`;

  $("#bulkPreview").querySelectorAll("input[type=checkbox][data-bidx]").forEach(cb => {
    cb.addEventListener("change", () => {
      bulkState.rows[parseInt(cb.dataset.bidx, 10)].checked = cb.checked;
      updateBulkApplyButton();
    });
  });
  $("#bulkPreview").querySelectorAll("textarea.diff-textarea").forEach(ta => {
    ta.addEventListener("input", () => {
      const i = parseInt(ta.dataset.bidx, 10);
      bulkState.rows[i].after = ta.value;
      // live-update diff cell
      const diffCell = ta.closest("tr").querySelector(".diff-text");
      if (diffCell) diffCell.innerHTML = renderInlineDiff(bulkState.rows[i].before, ta.value);
    });
  });

  renderBulkPagination(from, to, filtered.length, totalPages);
}

function renderBulkPagination(from, to, total, totalPages) {
  const el = $("#bulkPagination");
  if (total === 0) { el.innerHTML = ""; return; }
  const info = `${from + 1}–${to} / ${total}`;
  el.innerHTML = `
    <button id="bulkPrev" ${bulkState.page <= 1 ? "disabled" : ""}>←</button>
    <span class="page-info">${info}</span>
    <button id="bulkNext" ${bulkState.page >= totalPages ? "disabled" : ""}>→</button>`;
  $("#bulkPrev").addEventListener("click", () => { if (bulkState.page > 1) { bulkState.page--; renderBulkPage(); } });
  $("#bulkNext").addEventListener("click", () => { if (bulkState.page < totalPages) { bulkState.page++; renderBulkPage(); } });
}

function updateBulkApplyButton() {
  const n = bulkState.rows.filter(r => r.status === "ok" && r.checked).length;
  const btn = $("#bulkApply");
  btn.disabled = n === 0;
  btn.textContent = `${I18N.t("bulk.apply_hint")} (${n})`;
}

function bulkSelectBy(predicate) {
  bulkState.rows.forEach(r => {
    if (r.status === "ok") r.checked = predicate(r);
  });
  renderBulkPage();
  updateBulkApplyButton();
}

async function bulkApply() {
  const checked = bulkState.rows.filter(r => r.status === "ok" && r.checked);
  if (!checked.length) return;

  // Collapse per original word: one patch per anchor.
  const byWord = new Map();
  checked.forEach(r => {
    if (!byWord.has(r.word)) byWord.set(r.word, { word: r.word });
    const p = byWord.get(r.word);
    if (r.field === "translation") p.translation = r.after;
    else if (r.field === "contexts") p.contexts = r.after;
    else if (r.field === "word" && r.after !== r.word) p.new_word = r.after;
  });

  try {
    const res = await api("/api/words/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify([...byWord.values()]),
    });
    const failed = res.results.filter(r => !r.ok);
    if (failed.length) {
      toast(I18N.t("bulk.applied_fail")
        .replace("{ok}", res.applied)
        .replace("{total}", res.total)
        .replace("{fail}", failed.length), "error");
    } else if (res.backup) {
      toast(I18N.t("bulk.applied_backup").replace("{n}", res.applied));
    } else {
      toast(I18N.t("bulk.applied").replace("{n}", res.applied));
    }
    closeBulkModal();
    wordsCache = await api("/api/words");
    drawEditorList();
  } catch (e) {
    toast(e.message, "error");
  }
}

// Wire bulk modal buttons once.
$("#bulkCancel").addEventListener("click", closeBulkModal);
$("#bulkApply").addEventListener("click", bulkApply);
$("#bulkCopyAgain").addEventListener("click", exportEditorJson);
$("#bulkParse").addEventListener("click", bulkParse);
$("#bulkSelectAll").addEventListener("click", () => bulkSelectBy(() => true));
$("#bulkSelectNone").addEventListener("click", () => bulkSelectBy(() => false));
$("#bulkInvert").addEventListener("click", () => bulkSelectBy(r => !r.checked));
$("#bulkApplyTranslations").addEventListener("click", () => bulkSelectBy(r => r.field === "translation"));
$("#bulkApplyContexts").addEventListener("click", () => bulkSelectBy(r => r.field === "contexts"));
$("#bulkApplyRenames").addEventListener("click", () => bulkSelectBy(r => r.field === "word"));
$("#bulkModal").addEventListener("click", (e) => {
  if (e.target === $("#bulkModal")) closeBulkModal();
});

// ---------- Settings ----------
async function renderSettings() {
  const el = $("#tab-settings");
  const [info, conf, cefr] = await Promise.all([
    api("/api/file-info"),
    api("/api/settings"),
    api("/api/stats/cefr-avg"),
  ]);
  const langs = I18N.supported();

  const langButtons = langs
    .map(l => `<button class="lang-btn${l === I18N.current ? " active" : ""}" data-lang="${l}">${l.toUpperCase()}</button>`)
    .join("");

  const cefrRow = cefr.matched
    ? `<div class="info-row"><span>${I18N.t("settings.cefr_info")}</span><code>${I18N.t("settings.cefr_found")}: ${cefr.matched}</code></div>`
    : `<div class="info-row"><span>${I18N.t("settings.cefr_info")}</span><code class="muted">${I18N.t("settings.cefr_missing")}</code></div>`;

  const infoRows = (info.exists
    ? `
      <div class="info-row"><span>${I18N.t("settings.path")}</span><code>${escapeHtml(info.path)}</code></div>
      <div class="info-row"><span>${I18N.t("settings.size")}</span><code>${info.size_human}</code></div>
      <div class="info-row"><span>${I18N.t("settings.modified")}</span><code>${info.modified}</code></div>
      <div class="info-row"><span>${I18N.t("settings.words")}</span><code>${info.words}</code></div>`
    : `<div class="info-row"><span>${I18N.t("settings.path")}</span><code>${escapeHtml(info.path)}</code></div>
       <div class="info-row muted">File not found</div>`) + cefrRow;

  el.innerHTML = `
    <div class="chart-wrap">
      <div class="settings-header">
        <h2 class="settings-title">${I18N.t("settings.title")}</h2>
        <div class="settings-actions">
          <button class="btn btn-secondary" id="reloadCefr">${I18N.t("settings.cefr_reload")}</button>
          <button class="btn btn-secondary" id="reloadBtn">${I18N.t("settings.reload")}</button>
        </div>
      </div>
      <div class="settings-block" style="margin-top:20px">
        <div class="settings-label">${I18N.t("settings.language")}</div>
        <div class="lang-switch" id="langSwitch">${langButtons}</div>
      </div>
      <div class="settings-block">
        <div class="settings-label">${I18N.t("settings.thresholds")}</div>
        <div class="row">
          <div><label class="muted">${I18N.t("settings.mature_days")}</label>
            <input type="number" id="matureDays" value="${conf.mature_days}" min="1" max="365"></div>
          <div><label class="muted">${I18N.t("settings.young_days")}</label>
            <input type="number" id="youngDays" value="${conf.young_days}" min="1" max="365"></div>
        </div>
        <button class="btn" id="saveThresholds" style="margin-top:12px">${I18N.t("settings.save")}</button>
      </div>
      <div class="settings-block">
        <div class="settings-label">${I18N.t("settings.file_info")}</div>
        <div class="info-list">${infoRows}</div>
      </div>
    </div>`;

  $("#langSwitch").addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-lang]");
    if (!btn) return;
    await setLanguage(btn.dataset.lang);
  });
  $("#reloadBtn").addEventListener("click", () => window.location.reload());
  $("#saveThresholds").addEventListener("click", async () => {
    const mature = parseInt($("#matureDays").value, 10);
    const young = parseInt($("#youngDays").value, 10);
    if (!mature || !young) return;
    try {
      await api("/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mature_days: mature, young_days: young }),
      });
      toast(I18N.t("toast.saved"));
      renderOverview();
    } catch (e) {
      toast(e.message, "error");
    }
  });
  $("#reloadCefr").addEventListener("click", async () => {
    try {
      const r = await api("/api/cefr/reload", { method: "POST" });
      toast(`${I18N.t("settings.cefr_reload")}: ${r.words}`);
      renderSettings();
    } catch (e) {
      toast(e.message, "error");
    }
  });
}

async function setLanguage(lang) {
  await I18N.load(lang);
  localStorage.setItem("lang", lang);
  I18N.apply();
  document.documentElement.lang = lang;
  document.title = I18N.t("app.title");
  render(currentTab);
}

// ---------- Router ----------
const renderers = {
  overview: renderOverview,
  calendar: renderCalendar,
  words: renderWords,
  editor: renderEditor,
  settings: renderSettings,
};

function render(tab) {
  currentTab = tab;
  renderers[tab]();
}

// Re-layout heatmaps on window resize (only tabs that have them).
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (currentTab === "overview" || currentTab === "calendar") render(currentTab);
  }, 200);
});

// ---------- Init ----------
(async function init() {
  const savedLang = localStorage.getItem("lang") || "en";
  await I18N.load(savedLang);
  I18N.apply();
  document.documentElement.lang = savedLang;
  document.title = I18N.t("app.title");
  render("overview");
})();