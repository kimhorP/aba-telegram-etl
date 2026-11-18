const state = {
  shop: "",
  start: "",
  end: "",
  bucket: "day",
  sort: { key: "date", dir: "desc" },
};
const charts = {};
const SORT_DEFAULT_DIR = {
  date: "desc",
  amount: "desc",
  khr: "desc",
  shop: "asc",
  customer: "asc",
  bank: "asc",
  currency: "asc",
  remark: "asc",
};

const numFmt = new Intl.NumberFormat("en-US");
const fmtInt = (n) => numFmt.format(Math.round(n));

const PALETTES = {
  light: {
    muted: "#6e6e73",
    grid: "#ecece7",
    blue: "#2f5d8c",
    gold: "#c08a2e",
    ink: "#1b1b1f",
    donutBorder: "#ffffff",
    fill: "rgba(47, 93, 140, 0.08)",
  },
  dark: {
    muted: "#9a9aa0",
    grid: "#2a2a30",
    blue: "#6fa3e0",
    gold: "#d9a441",
    ink: "#e8e8e4",
    donutBorder: "#1c1c20",
    fill: "rgba(111, 163, 224, 0.14)",
  },
};

let COLORS = PALETTES.light;
let axisTicks = { color: COLORS.muted, font: { size: 11 } };

function applyChartTheme() {
  const name =
    document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  COLORS = PALETTES[name];
  axisTicks = { color: COLORS.muted, font: { size: 11 } };
  Chart.defaults.font.family = "'IBM Plex Sans', system-ui, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.color = COLORS.muted;
}

function filters() {
  return {
    shop: state.shop && state.shop !== "All shops" ? state.shop : "",
    start: state.start,
    end: state.end,
  };
}

async function api(path, params) {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) qs.set(key, value);
  }
  const res = await fetch(path + (qs.size ? `?${qs}` : ""));
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || res.statusText);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

function showError(message) {
  const banner = document.getElementById("error-banner");
  banner.textContent =
    message ||
    "Can't reach the database. Is the db container running? (docker compose up -d db)";
  banner.hidden = false;
}

function hideError() {
  document.getElementById("error-banner").hidden = true;
}

function renderShops(shops) {
  const select = document.getElementById("filter-shop");
  const current = select.value || "All shops";
  const next = shops.join("\u0000");
  if (select.dataset.rendered === next) return;
  select.innerHTML = "";
  for (const name of shops) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  }
  select.value = shops.includes(current) ? current : "All shops";
  select.dataset.rendered = next;
}

function renderSummary(s) {
  document.getElementById("kpi-total").textContent = fmtInt(s.total_khr);
  document.getElementById("kpi-count").textContent = fmtInt(s.count);
  document.getElementById("kpi-avg").textContent =
    s.avg_khr == null ? "—" : fmtInt(s.avg_khr);
  document.getElementById("kpi-currency").textContent =
    `${fmtInt(s.usd_count)} / ${fmtInt(s.khr_count)}`;
}

const MOVE_LABELS = { dod: "DoD", mom: "MoM", yoy: "YoY" };

function renderMovement(key, m) {
  const deltaEl = document.getElementById(`mov-${key}-delta`);
  const label = MOVE_LABELS[key];
  if (m.previous == null || m.delta == null) {
    deltaEl.textContent = `— ${label}`;
    deltaEl.className = "kpi-move mono flat";
    return;
  }
  const arrow = m.delta > 0 ? "▲" : m.delta < 0 ? "▼" : "";
  const pct = m.pct == null ? "" : ` (${m.pct > 0 ? "+" : ""}${m.pct.toFixed(1)}%)`;
  deltaEl.textContent = `${arrow} ${fmtInt(m.delta)}${pct} ${label}`;
  deltaEl.className =
    "kpi-move mono " + (m.delta > 0 ? "pos" : m.delta < 0 ? "neg" : "flat");
}

function makeChart(id, config) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), config);
}

function fmtPeriod(iso, bucket) {
  if (bucket === "month" || bucket === "6month") {
    const d = new Date(`${iso}T00:00:00`);
    return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  }
  if (bucket === "year") return iso.slice(0, 4);
  return iso;
}

const trendCrosshair = {
  id: "trendCrosshair",
  afterDraw(chart) {
    const active = chart.tooltip?.getActiveElements?.() || [];
    if (!active.length) return;
    const x = active[0].element.x;
    const { top, bottom } = chart.chartArea;
    const ctx = chart.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.lineWidth = 1;
    ctx.strokeStyle = COLORS.muted;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.restore();
  },
};

let lastTrend = [];

function renderTrend(points) {
  lastTrend = points;
  const showMarkers = state.bucket !== "day";
  makeChart("chart-trend", {
    type: "line",
    plugins: [trendCrosshair],
    data: {
      labels: points.map((p) => fmtPeriod(p.period, state.bucket)),
      datasets: [
        {
          label: "KHR",
          data: points.map((p) => p.total_khr),
          borderColor: COLORS.blue,
          backgroundColor: COLORS.fill,
          fill: true,
          tension: 0.25,
          pointRadius: showMarkers ? 3 : 0,
          pointHoverRadius: showMarkers ? 5 : 4,
          pointHitRadius: 24,
          borderWidth: 2,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            label: (ctx) => `${fmtInt(ctx.parsed.y)} KHR`,
            title: (items) => (items.length ? items[0].label : ""),
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { ...axisTicks, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
        },
        y: {
          beginAtZero: true,
          grid: { color: COLORS.grid },
          ticks: { ...axisTicks, callback: (v) => fmtInt(v) },
        },
      },
    },
  });
}

const shortLabel = (s) => (s.length > 20 ? `${s.slice(0, 18)}…` : s);

const fmtBar = (v) => {
  const a = Math.abs(v);
  if (a >= 1e6) return `${+(v / 1e6).toFixed(1)}M`;
  if (a >= 1e4) return `${+(v / 1e3).toFixed(1)}K`;
  return fmtInt(v);
};

const barValueLabels = {
  id: "barValueLabels",
  afterDatasetsDraw(chart) {
    const dataset = chart.data.datasets[0];
    if (!dataset) return;
    const meta = chart.getDatasetMeta(0);
    const horizontal = chart.options.indexAxis === "y";
    const rotate = !horizontal && meta.data.length > 12;
    const ctx = chart.ctx;
    ctx.save();
    ctx.font = "600 10px 'IBM Plex Sans', system-ui, sans-serif";
    for (let i = 0; i < meta.data.length; i++) {
      const v = dataset.data[i];
      if (v == null || v === 0) continue;
      const el = meta.data[i];
      const text = fmtBar(v);
      if (horizontal) {
        const endX = Math.max(el.x, el.base);
        const w = ctx.measureText(text).width;
        ctx.save();
        if (endX + 5 + w <= chart.chartArea.right) {
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          ctx.fillStyle = COLORS.ink;
          ctx.fillText(text, endX + 5, el.y);
        } else {
          ctx.textAlign = "right";
          ctx.textBaseline = "middle";
          ctx.fillStyle = "#ffffff";
          ctx.fillText(text, endX - 5, el.y);
        }
        ctx.restore();
      } else if (rotate) {
        if (el.base - el.y < 10) continue;
        const w = ctx.measureText(text).width;
        const inside = el.y - 5 - w < chart.chartArea.top;
        ctx.save();
        ctx.translate(el.x, inside ? el.y + w + 2 : el.y - 5);
        ctx.rotate(-Math.PI / 2);
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillStyle = inside ? "#ffffff" : COLORS.ink;
        ctx.fillText(text, 0, 0);
        ctx.restore();
      } else {
        if (el.base - el.y < 12) continue;
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillStyle = COLORS.ink;
        ctx.fillText(text, el.x, el.y - 4);
        ctx.restore();
      }
    }
    ctx.restore();
  },
};

function renderBars(id, rows, valueKey = "total_khr") {
  makeChart(id, {
    type: "bar",
    plugins: [barValueLabels],
    data: {
      labels: rows.map((r) => shortLabel(r.label)),
      datasets: [
        {
          data: rows.map((r) => r[valueKey]),
          backgroundColor: COLORS.blue,
          borderRadius: 2,
          barThickness: 14,
        },
      ],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => (items.length ? rows[items[0].dataIndex].label : ""),
            label: (ctx) =>
              valueKey === "count"
                ? `${fmtInt(ctx.parsed.x)} transactions`
                : `${fmtInt(ctx.parsed.x)} KHR`,
          },
        },
      },
      layout: { padding: { left: 4, right: 8 } },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: COLORS.grid },
          ticks: {
            ...axisTicks,
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 6,
            callback: (v) =>
              Math.abs(v) >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : fmtInt(v),
          },
        },
        y: {
          grid: { display: false },
          ticks: { ...axisTicks, font: { size: 11.5 } },
        },
      },
    },
  });
}

function renderColumns(id, rows, opts = {}) {
  makeChart(id, {
    type: "bar",
    plugins: [barValueLabels],
    data: {
      labels: rows.map((r) => r.label),
      datasets: [
        {
          data: rows.map((r) => r.total_khr),
          backgroundColor: COLORS.blue,
          borderRadius: 2,
          barPercentage: 0.8,
          categoryPercentage: 0.9,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${fmtInt(ctx.parsed.y)} KHR`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            ...axisTicks,
            maxRotation: 0,
            autoSkip: !!opts.autoSkip,
            maxTicksLimit: opts.maxTicksLimit,
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: COLORS.grid },
          ticks: { ...axisTicks, callback: (v) => fmtInt(v) },
        },
      },
    },
  });
}

function renderDonut(rows) {
  makeChart("chart-currency", {
    type: "doughnut",
    data: {
      labels: rows.map((r) => r.label),
      datasets: [
        {
          data: rows.map((r) => r.total_khr),
          backgroundColor: [COLORS.blue, COLORS.gold, COLORS.ink],
          borderColor: COLORS.donutBorder,
          borderWidth: 2,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { boxWidth: 10, boxHeight: 10, padding: 12 },
        },
      },
      cutout: "62%",
    },
  });
}

function renderRecent(rows) {
  const body = document.getElementById("recent-body");
  body.innerHTML = "";
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="8" class="remark">No transactions match these filters.</td>`;
    body.appendChild(tr);
    return;
  }
  for (const r of rows) {
    const tr = document.createElement("tr");
    const date = r.date ? r.date.replace("T", " ").slice(0, 16) : "—";
    const cells = [
      date,
      r.shop ?? "—",
      r.customer ?? "—",
      r.bank ?? "—",
      r.currency ?? "—",
      r.amount == null ? "—" : fmtInt(r.amount),
      r.khr == null ? "—" : fmtInt(r.khr),
      r.remark === "NaN" ? "" : r.remark ?? "",
    ];
    cells.forEach((value, i) => {
      const td = document.createElement("td");
      if (i === 5 || i === 6) td.className = "num";
      if (i === 7) td.className = "remark";
      td.textContent = value;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  }
}

async function load() {
  hideError();
  applyChartTheme();
  const f = filters();
  try {
    const [
      shops,
      summary,
      trend,
      byShop,
      byBank,
      byCurrency,
      custAmount,
      custCount,
      patterns,
      recent,
      movement,
    ] = await Promise.all([
      api("/api/shops", {}),
      api("/api/summary", f),
      api("/api/timeseries", { ...f, bucket: state.bucket }),
      api("/api/breakdown", { ...f, dim: "shop_name" }),
      api("/api/breakdown", { ...f, dim: "sender_bank", limit: 5 }),
      api("/api/breakdown", { ...f, dim: "currency" }),
      api("/api/breakdown", {
        ...f,
        dim: "customer_name",
        order: "amount",
        limit: 10,
      }),
      api("/api/breakdown", {
        ...f,
        dim: "customer_name",
        order: "count",
        limit: 10,
      }),
      api("/api/patterns", f),
      api("/api/recent", { ...f, limit: 15 }),
      api("/api/movement", f),
    ]);

    renderShops(shops);

    const empty = summary.count === 0;
    document.getElementById("empty-state").hidden = !empty;
    document.getElementById("dashboard").hidden = empty;
    if (empty) return;

    renderSummary(summary);
    renderMovement("dod", movement.dod);
    renderMovement("mom", movement.mom);
    renderMovement("yoy", movement.yoy);
    renderTrend(trend);
    renderBars("chart-shop", byShop);
    renderBars("chart-bank", byBank);
    renderDonut(byCurrency);
    renderBars("chart-cust-amount", custAmount, "total_khr");
    renderBars("chart-cust-count", custCount, "count");
    renderColumns("chart-dow", patterns.dow);
    renderColumns("chart-hour", patterns.hour, {
      autoSkip: true,
      maxTicksLimit: 12,
    });
    renderRecent(recent);
    lastRecent = recent;
    updateSortHeaders();
  } catch (err) {
    if (err.status === 503) showError();
    else showError(`Something went wrong: ${err.message}`);
  }
}

function themeLabel() {
  const btn = document.getElementById("theme-toggle");
  const dark = document.documentElement.dataset.theme === "dark";
  document.getElementById("theme-label").textContent = dark ? "Light" : "Dark";
  btn.setAttribute(
    "aria-label",
    dark ? "Switch to light theme" : "Switch to dark theme"
  );
}

function updateSortHeaders() {
  for (const th of document.querySelectorAll("th[data-sort]")) {
    const active = th.dataset.sort === state.sort.key;
    th.classList.toggle("sorted", active);
    const arrow = th.querySelector(".sort-arrow");
    if (arrow) arrow.textContent = active ? (state.sort.dir === "asc" ? "▲" : "▼") : "";
  }
}

let lastRecent = [];

const RECENT_GETTERS = {
  date: (r) => r.date || "",
  shop: (r) => r.shop ?? "",
  customer: (r) => r.customer ?? "",
  bank: (r) => r.bank ?? "",
  currency: (r) => r.currency ?? "",
  amount: (r) => r.amount ?? 0,
  khr: (r) => r.khr ?? 0,
  remark: (r) => r.remark ?? "",
};

function sortRecent(key) {
  if (state.sort.key === key) {
    state.sort.dir = state.sort.dir === "asc" ? "desc" : "asc";
  } else {
    state.sort.key = key;
    state.sort.dir = SORT_DEFAULT_DIR[key] || "asc";
  }
  const get = RECENT_GETTERS[key] || RECENT_GETTERS.date;
  const dir = state.sort.dir === "asc" ? 1 : -1;
  const rows = [...lastRecent].sort((a, b) => {
    const va = get(a);
    const vb = get(b);
    if (va < vb) return -1 * dir;
    if (va > vb) return 1 * dir;
    return 0;
  });
  updateSortHeaders();
  renderRecent(rows);
}

function bindEvents() {
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const next =
      document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch (e) {}
    themeLabel();
    load();
  });
  document.getElementById("filter-shop").addEventListener("change", (e) => {
    state.shop = e.target.value;
    load();
  });
  document.getElementById("filter-start").addEventListener("change", (e) => {
    state.start = e.target.value;
    load();
  });
  document.getElementById("filter-end").addEventListener("change", (e) => {
    state.end = e.target.value;
    load();
  });
  document.getElementById("filter-clear").addEventListener("click", () => {
    state.shop = "";
    state.start = "";
    state.end = "";
    document.getElementById("filter-shop").value = "All shops";
    document.getElementById("filter-start").value = "";
    document.getElementById("filter-end").value = "";
    load();
  });
  for (const th of document.querySelectorAll("th[data-sort]")) {
    th.addEventListener("click", () => {
      sortRecent(th.dataset.sort);
    });
  }
  for (const btn of document.querySelectorAll(".toggle-btn")) {
    btn.addEventListener("click", () => {
      state.bucket = btn.dataset.bucket;
      for (const b of document.querySelectorAll(".toggle-btn")) {
        b.classList.toggle("is-active", b === btn);
      }
      load();
    });
  }
}

const EXPORT_LIBS = {
  html2canvas:
    "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js",
  jspdf: "https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js",
};

function loadScript(src) {
  if ([...document.scripts].some((s) => s.src === src)) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error("Failed to load export library"));
    document.head.appendChild(s);
  });
}

async function renderExportCanvas() {
  await loadScript(EXPORT_LIBS.html2canvas);
  return window.html2canvas(document.body, {
    backgroundColor: getComputedStyle(document.body).backgroundColor,
    scale: 2,
    useCORS: true,
  });
}

function fileStamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function exportName(ext) {
  const slug = document.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `${slug}-${fileStamp()}.${ext}`;
}

async function exportPng() {
  const canvas = await renderExportCanvas();
  const a = document.createElement("a");
  a.download = exportName("png");
  a.href = canvas.toDataURL("image/png");
  a.click();
}

async function exportPdf() {
  let canvas = await renderExportCanvas();
  const max = 14000;
  if (Math.max(canvas.width, canvas.height) > max) {
    const k = max / Math.max(canvas.width, canvas.height);
    const scaled = document.createElement("canvas");
    scaled.width = Math.round(canvas.width * k);
    scaled.height = Math.round(canvas.height * k);
    scaled.getContext("2d").drawImage(canvas, 0, 0, scaled.width, scaled.height);
    canvas = scaled;
  }
  await loadScript(EXPORT_LIBS.jspdf);
  const { jsPDF } = window.jspdf;
  const w = canvas.width;
  const h = canvas.height;
  const pdf = new jsPDF({
    orientation: w >= h ? "landscape" : "portrait",
    unit: "px",
    format: [w, h],
    hotfixes: ["px_scaling"],
  });
  pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, 0, w, h);
  pdf.save(exportName("pdf"));
}

function bindExport() {
  const btn = document.getElementById("export-btn");
  const menu = document.getElementById("export-menu");
  const close = () => {
    menu.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  };
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.hidden = !menu.hidden;
    btn.setAttribute("aria-expanded", String(!menu.hidden));
  });
  document.addEventListener("click", (e) => {
    if (!menu.hidden && !menu.contains(e.target)) close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
  });

  async function run(fn) {
    close();
    hideError();
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.textContent = "Exporting…";
    try {
      await fn();
    } catch (err) {
      showError(`Export failed: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = original;
    }
  }

  document
    .getElementById("export-png")
    .addEventListener("click", () => run(exportPng));
  document
    .getElementById("export-pdf")
    .addEventListener("click", () => run(exportPdf));
}

function bindTrendCopy() {
  const btn = document.getElementById("trend-copy");
  btn.addEventListener("click", async () => {
    const text = lastTrend
      .map((p) => `${fmtPeriod(p.period, state.bucket)}\t${p.total_khr}`)
      .join("\n");
    let ok = true;
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      ok = document.execCommand("copy");
      ta.remove();
    }
    if (ok) {
      btn.textContent = "Copied!";
      setTimeout(() => {
        btn.textContent = "Copy";
      }, 1500);
    } else {
      showError("Couldn't copy to clipboard");
    }
  });
}

applyChartTheme();
themeLabel();
bindEvents();
bindExport();
bindTrendCopy();
load();
