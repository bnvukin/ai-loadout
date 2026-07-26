/* Loadout dashboard SPA. Vanilla JS, no build step.
 * Reads /api/* for data and streams /ws for live events. Everything renders off the
 * same digital twin the CLI uses, so the two never disagree. */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const api = (p, opt) => fetch(p, opt).then((r) => r.json());
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const TASK_ORDER = ["scan", "deps", "runtimes", "config", "health"];
  const VIEW_META = {
    overview: ["Overview", "Live view of your machine's digital twin."],
    components: ["Components", "Every managed tool, its state and health."],
    models: ["Models", "Hardware-aware recommendations for this machine."],
    config: ["Config Center", "Config files, environment variables and PATH (secrets redacted)."],
    activity: ["Activity", "Live event stream from the orchestrator."],
  };

  const store = { view: "overview", events: [], seen: new Set(), tasks: {} };

  function badge(health) {
    const h = health || "gray";
    return `<span class="badge b-${h}"><span class="dot"></span>${esc(h)}</span>`;
  }
  function stars(n) {
    n = Number(n) || 0;
    return `<span class="stars">${"*".repeat(n)}${"·".repeat(Math.max(0, 5 - n))}</span>`;
  }
  function fmtTime(ts) {
    const d = new Date((ts || 0) * 1000);
    return d.toLocaleTimeString();
  }

  // -- views --------------------------------------------------------------------
  async function renderOverview() {
    const host = $("#view-overview");
    const [snap, health] = await Promise.all([api("/api/state"), api("/api/health")]);
    const hw = snap.hardware || {};
    const c = health.counts || {};
    const ringColor =
      health.percent >= 80 ? "var(--green)" : health.percent >= 50 ? "var(--yellow)" : "var(--red)";
    const issues = (health.issues || [])
      .map(
        (i) => `<div class="issue">
          <h4>${esc(i.title)}</h4>
          <div class="muted">${esc(i.explanation || "")}</div>
          <div class="fix">Fix: ${esc(i.fix || "")}</div>
          ${i.why ? `<div class="why">${esc(i.why)}</div>` : ""}
        </div>`
      )
      .join("");

    host.innerHTML = `
      <div class="grid cols-2">
        <div class="card">
          <h3>System health</h3>
          <div class="health">
            <div class="ring" style="--p:${health.percent || 0}; --c:${ringColor}">
              <div class="val">${health.percent || 0}%</div>
            </div>
            <div class="meta">
              <div class="status">${esc(health.status || "")}</div>
              <div class="counts">
                <span>${badge("green")} ${c.green || 0}</span>
                <span>${badge("yellow")} ${c.yellow || 0}</span>
                <span>${badge("red")} ${c.red || 0}</span>
                <span>${badge("gray")} ${c.gray || 0}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="card">
          <h3>Machine</h3>
          <div class="kv">
            <div class="k">OS</div><div class="v">${esc(hw.os_name || "?")}</div>
            <div class="k">CPU</div><div class="v">${esc(hw.cpu_name || "?")}</div>
            <div class="k">RAM</div><div class="v">${esc(hw.ram_total_gb ?? "?")} GB</div>
            <div class="k">VRAM</div><div class="v">${esc(hw.total_vram_gb ?? 0)} GB</div>
            <div class="k">Disk free</div><div class="v">${esc(hw.primary_disk_free_gb ?? "?")} GB</div>
            <div class="k">Internet</div><div class="v">${hw.internet ? "online" : "offline"}</div>
          </div>
        </div>
      </div>
      <div class="card" style="margin-top:16px">
        <h3>Issues (${(health.issues || []).length})</h3>
        ${issues || '<div class="empty">No issues detected. Your workstation looks healthy.</div>'}
      </div>`;
  }

  async function renderComponents() {
    const host = $("#view-components");
    const { components } = await api("/api/components");
    const groups = {};
    for (const c of components) (groups[c.category] = groups[c.category] || []).push(c);
    const order = ["hardware", "os", "dependency", "runtime", "editor", "connection", "config", "model", "service"];
    const cats = Object.keys(groups).sort((a, b) => order.indexOf(a) - order.indexOf(b));
    if (!components.length) {
      host.innerHTML = '<div class="card"><div class="empty">Nothing scanned yet. Hit Rescan.</div></div>';
      return;
    }
    host.innerHTML = cats
      .map(
        (cat) => `<div class="card" style="margin-bottom:16px">
        <h3>${esc(cat)}</h3>
        <table><thead><tr><th>Component</th><th>State</th><th>Health</th><th>Version</th><th>Detail</th></tr></thead>
        <tbody>${groups[cat]
          .map(
            (c) => `<tr>
            <td><strong>${esc(c.name)}</strong></td>
            <td class="muted">${esc(c.state)}</td>
            <td>${badge(c.health)}</td>
            <td class="mono">${esc(c.version || "")}</td>
            <td class="muted">${esc(c.detail || "")}</td>
          </tr>`
          )
          .join("")}</tbody></table></div>`
      )
      .join("");
  }

  async function renderModels() {
    const host = $("#view-models");
    const data = await api("/api/models");
    const recs = data.recommendations || [];
    const installed = data.installed || [];
    const rows = recs
      .map(
        (r) => `<tr>
        <td><strong>${esc(r.name)}</strong> ${
          (r.labels || [])[0] ? `<span class="trust safe">${esc(r.labels[0])}</span>` : ""
        }</td>
        <td class="muted">${esc(r.best_for || "")}</td>
        <td>${stars(r.coding)}</td>
        <td>${stars(r.effective_speed)}</td>
        <td class="right">${esc(r.min_ram_gb ?? "")}G</td>
        <td class="right mono">${esc(r.tokens_per_sec ?? "")}</td>
        <td>${
          r.fit === "fits"
            ? badge("green")
            : r.fit === "tight"
            ? badge("yellow")
            : badge("red")
        } ${esc(r.fit || "")}</td>
      </tr>`
      )
      .join("");
    host.innerHTML = `
      <div class="card">
        <h3>Recommended for this machine</h3>
        <table><thead><tr><th>Model</th><th>Best for</th><th>Coding</th><th>Speed</th><th class="right">RAM</th><th class="right">tok/s</th><th>Fit</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="7" class="empty">Run a scan to size models.</td></tr>'}</tbody></table>
      </div>
      <div class="card" style="margin-top:16px">
        <h3>Installed locally (${installed.length})</h3>
        ${
          installed.length
            ? `<table><thead><tr><th>Name</th><th>Provider</th><th class="right">Size</th></tr></thead><tbody>${installed
                .map(
                  (m) =>
                    `<tr><td class="mono">${esc(m.name)}</td><td class="muted">${esc(
                      m.provider
                    )}</td><td class="right">${m.size_gb ? esc(m.size_gb) + " GB" : ""}</td></tr>`
                )
                .join("")}</tbody></table>`
            : '<div class="empty">No local models found (Ollama not running or empty).</div>'
        }
      </div>`;
  }

  async function renderConfig() {
    const host = $("#view-config");
    const data = await api("/api/config");
    const cfgRows = (data.configs || [])
      .map(
        (cf) => `<tr>
        <td><strong>${esc(cf.name)}</strong></td>
        <td><span class="trust ${esc(cf.trust)}">${esc(cf.trust)}</span></td>
        <td>${cf.exists ? badge("green") : badge("gray")}</td>
        <td class="mono muted">${esc(cf.path || "")}</td>
        <td>${cf.exists ? `<button class="btn ghost" data-cfg="${esc(cf.key)}">view</button>` : ""}</td>
      </tr>`
      )
      .join("");
    const env = (data.env || [])
      .filter((e) => e.present)
      .map(
        (e) => `<tr><td class="mono">${esc(e.name)}</td><td class="mono">${esc(e.value)}</td></tr>`
      )
      .join("");
    const p = data.path || {};
    host.innerHTML = `
      <div class="card">
        <h3>Config files</h3>
        <table><thead><tr><th>File</th><th>Trust</th><th>Status</th><th>Path</th><th></th></tr></thead>
        <tbody>${cfgRows}</tbody></table>
      </div>
      <pre class="file hidden" id="file-view"></pre>
      <div class="grid cols-2" style="margin-top:16px">
        <div class="card">
          <h3>Environment (${(data.env || []).filter((e) => e.present).length} set)</h3>
          <table><tbody>${
            env || '<tr><td class="empty">No AI-relevant env vars set.</td></tr>'
          }</tbody></table>
        </div>
        <div class="card">
          <h3>PATH (${p.count || 0} entries)</h3>
          <div class="muted" style="margin-bottom:8px">
            ${(p.missing || []).length} missing · ${(p.duplicates || []).length} duplicate
          </div>
          <div class="mono" style="max-height:40vh; overflow:auto">${(p.entries || [])
            .map(
              (e) =>
                `<div>${esc(e.path)} ${
                  e.exists ? "" : '<span style="color:var(--red)">MISSING</span>'
                } ${e.duplicate ? '<span style="color:var(--yellow)">DUP</span>' : ""}</div>`
            )
            .join("")}</div>
        </div>
      </div>`;
    $$("[data-cfg]", host).forEach((btn) =>
      btn.addEventListener("click", async () => {
        const view = $("#file-view");
        view.classList.remove("hidden");
        view.textContent = "Loading...";
        const res = await api("/api/config/" + encodeURIComponent(btn.dataset.cfg));
        const note = res.redacted ? "  (secrets redacted)" : "";
        view.textContent = `# ${res.path || ""}${note}\n\n${res.content || res.error || "(empty)"}`;
        view.scrollIntoView({ behavior: "smooth", block: "nearest" });
      })
    );
  }

  function renderActivity() {
    const host = $("#view-activity");
    host.innerHTML = `<div class="card"><h3>Event stream</h3><div class="log" id="log"></div></div>`;
    const log = $("#log");
    log.innerHTML = store.events
      .slice(-500)
      .map(
        (e) =>
          `<div class="row"><span class="ts">${fmtTime(e.ts)}</span><span class="lvl ${esc(
            e.level
          )}">${esc(e.level)}</span><span>${esc(e.message)}</span></div>`
      )
      .join("");
    log.scrollTop = log.scrollHeight;
  }

  const RENDERERS = {
    overview: renderOverview,
    components: renderComponents,
    models: renderModels,
    config: renderConfig,
    activity: renderActivity,
  };

  function refresh() {
    const fn = RENDERERS[store.view];
    if (fn) fn().catch((e) => console.error(e));
  }

  function setView(v) {
    store.view = v;
    $$(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === v));
    $$("section[id^='view-']").forEach((s) => s.classList.add("hidden"));
    $("#view-" + v).classList.remove("hidden");
    const [title, sub] = VIEW_META[v];
    $("#view-title").textContent = title;
    $("#view-sub").textContent = sub;
    refresh();
  }

  // -- progress chips -----------------------------------------------------------
  function renderProgress() {
    const host = $("#progress");
    const keys = Object.keys(store.tasks);
    if (!keys.length) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = TASK_ORDER.filter((t) => store.tasks[t])
      .map((t) => `<span class="chip ${esc(store.tasks[t])}">${esc(t)}</span>`)
      .join("");
  }

  // -- live events --------------------------------------------------------------
  let refreshTimer = null;
  function scheduleRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(refresh, 300);
  }

  function handleEvent(ev) {
    if (store.seen.has(ev.id)) return;
    store.seen.add(ev.id);
    store.events.push(ev);
    if (ev.message && /Scan started/i.test(ev.message)) store.tasks = {};
    if (ev.kind === "progress" && ev.data && ev.data.status) {
      store.tasks[ev.data.target] = ev.data.status;
      renderProgress();
      if (ev.data.status === "done") scheduleRefresh();
    }
    if (ev.kind === "step" && /complete/i.test(ev.message || "")) scheduleRefresh();
    if (store.view === "activity") {
      const log = $("#log");
      if (log) {
        const row = document.createElement("div");
        row.className = "row";
        row.innerHTML = `<span class="ts">${fmtTime(ev.ts)}</span><span class="lvl ${esc(
          ev.level
        )}">${esc(ev.level)}</span><span>${esc(ev.message)}</span>`;
        log.appendChild(row);
        log.scrollTop = log.scrollHeight;
      }
    }
  }

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    const conn = $("#conn");
    ws.onopen = () => {
      conn.classList.add("live");
      $("#conn-label").textContent = "live";
    };
    ws.onmessage = (m) => {
      try {
        handleEvent(JSON.parse(m.data));
      } catch (_) {}
    };
    ws.onclose = () => {
      conn.classList.remove("live");
      $("#conn-label").textContent = "reconnecting...";
      setTimeout(connect, 2000);
    };
    ws.onerror = () => ws.close();
  }

  // -- boot ---------------------------------------------------------------------
  function init() {
    $$(".nav-item").forEach((n) => n.addEventListener("click", () => setView(n.dataset.view)));
    $("#rescan").addEventListener("click", async () => {
      $("#rescan").disabled = true;
      store.tasks = { scan: "running" };
      renderProgress();
      try {
        await api("/api/scan", { method: "POST" });
      } finally {
        setTimeout(() => ($("#rescan").disabled = false), 1500);
      }
    });
    api("/api/version")
      .then((v) => ($("#foot").textContent = `Loadout ${v.version}`))
      .catch(() => {});
    setView("overview");
    connect();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
