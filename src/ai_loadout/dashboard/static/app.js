/* Loadout dashboard SPA. Vanilla JS, no build step.
 * Reads /api/* for data and streams /ws for live events. Everything renders off the
 * same digital twin the CLI uses, so the two never disagree.
 * Phase 2: every non-green item is actionable (install/upgrade/repair/rescan), models
 * pull with one click, and the Config Center edits + saves files. */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const api = (p, opt) => fetch(p, opt).then((r) => r.json());
  async function post(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    let json = {};
    try {
      json = await r.json();
    } catch (_) {}
    return { ok: r.ok, status: r.status, json };
  }
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const TASK_ORDER = ["scan", "deps", "runtimes", "config", "health"];
  const VIEW_META = {
    overview: ["Overview", "Live view of your machine's digital twin."],
    components: ["Components", "Every managed tool - fix anything that isn't green, right here."],
    models: ["Models", "Hardware-aware recommendations. Install with one click."],
    config: ["Config Center", "Open, edit and save config files. Browse every environment variable."],
    updates: ["Updates", "Loadout self-update status and component upgrades."],
    benchmark: ["Benchmark", "CPU, disk, and inference measurements for this machine."],
    vscode: ["VS Code", "Recommended settings and extensions for AI development."],
    continue: ["Continue", "Auto-generate Continue config from detected models."],
    agents: ["Agents / MCP", "Starter MCP config and agent workspace folders."],
    templates: ["Templates", "Scaffold new AI project starters."],
    profiles: ["Profiles", "Install an entire curated loadout in one go."],
    connections: ["Connections", "Which provider credentials are detected (presence only)."],
    settings: ["Settings & Privacy", "Telemetry opt-in, auto-rescan monitor, and privacy links."],
    activity: ["Activity", "Live event stream from the orchestrator."],
  };

  const store = {
    view: "overview",
    online: true,
    events: [],
    seen: new Set(),
    lastEventId: 0,
    tasks: {},
    installed: new Set(), // local model tags
    envMode: "known", // known | all
    envFilter: "",
    action: null, // { target, logEl, doneEl }
  };

  function netTip() {
    return store.online
      ? "Network available"
      : "Offline — downloads, model pulls, and installs are disabled";
  }

  function updateNetBadge() {
    const el = $("#net-badge");
    if (!el) return;
    el.textContent = store.online ? "online" : "offline";
    el.className = store.online ? "chip done" : "chip error";
    el.title = netTip();
  }

  async function pollConnectivity() {
    try {
      const c = await api("/api/connectivity");
      store.online = !!c.online;
    } catch (_) {
      store.online = false;
    }
    updateNetBadge();
  }

  function badge(health) {
    const h = health || "gray";
    return `<span class="badge b-${h}"><span class="dot"></span>${esc(h)}</span>`;
  }
  function stars(n) {
    n = Number(n) || 0;
    return `<span class="stars">${"*".repeat(n)}${"·".repeat(Math.max(0, 5 - n))}</span>`;
  }
  function fmtTime(ts) {
    return new Date((ts || 0) * 1000).toLocaleTimeString();
  }
  async function copyText(text, label = "Copied") {
    const value = text == null ? "" : String(text);
    try {
      await navigator.clipboard.writeText(value);
      toast(label, "success");
      return;
    } catch (_) {}
    try {
      const ta = document.createElement("textarea");
      ta.value = value;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      toast(label, "success");
    } catch (_) {
      toast("Copy failed.", "warning");
    }
  }
  function copyBtn(value, title = "Copy") {
    if (value == null || value === "") return "";
    return `<button class="btn sm ghost copy-btn" data-act="copy" data-copy="${esc(
      value
    )}" title="${esc(title)}" aria-label="${esc(title)}">&#x2398;</button>`;
  }
  function cmdBlock(text, title = "Copy command") {
    if (!text) return "";
    return `<div class="copy-row cmd-row"><pre class="cmd cmd-flex">${esc(
      text
    )}</pre>${copyBtn(text, title)}</div>`;
  }
  function linkRow(url, label = "Docs") {
    if (!url) return "";
    return `<span class="copy-row link-row"><a href="${esc(url)}" target="_blank" rel="noopener">${esc(
      label
    )}</a>${copyBtn(url, "Copy link")}</span>`;
  }

  function toast(msg, level = "info") {
    let host = $("#toasts");
    if (!host) {
      host = document.createElement("div");
      host.id = "toasts";
      document.body.appendChild(host);
    }
    const el = document.createElement("div");
    el.className = `toast ${level}`;
    el.textContent = msg;
    host.appendChild(el);
    setTimeout(() => el.classList.add("show"), 10);
    setTimeout(() => {
      el.classList.remove("show");
      setTimeout(() => el.remove(), 300);
    }, 4200);
  }

  // -- modal --------------------------------------------------------------------
  function openModal(title, bodyHtml, footHtml) {
    closeModal();
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.id = "modal";
    overlay.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <h3>${esc(title)}</h3>
          <button class="x" data-act="modal-close" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">${bodyHtml}</div>
        <div class="modal-foot">${footHtml || ""}</div>
      </div>`;
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });
    document.body.appendChild(overlay);
    return overlay;
  }
  function closeModal() {
    stopActionPolling();
    const m = $("#modal");
    if (m) m.remove();
    store.action = null;
  }

  // -- views --------------------------------------------------------------------
  async function renderOverview() {
    const host = $("#view-overview");
    const [snap, health, security] = await Promise.all([
      api("/api/state"),
      api("/api/health"),
      api("/api/security"),
    ]);
    const hw = snap.hardware || {};
    const c = health.counts || {};
    const ringColor =
      health.percent >= 80 ? "var(--green)" : health.percent >= 50 ? "var(--yellow)" : "var(--red)";
    const issues = (health.issues || []).map(issueCard).join("");
    const sec = security.summary || {};
    const secRows = (security.components || [])
      .slice(0, 6)
      .map(
        (item) =>
          `<tr><td>${esc(item.name)}</td><td class="muted">${esc(item.manager || item.method)}</td><td class="tiny muted">${esc(item.integrity)}</td></tr>`
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
        <div class="card-head">
          <h3>Security / integrity</h3>
          <span class="trust safe">${sec.package_manager || 0} via package manager</span>
        </div>
        <p class="muted tiny" style="margin:0 0 10px">
          Preferred manager: <strong>${esc(security.preferred_manager || "none")}</strong>.
          Official URL allowlist active; direct downloads would be SHA256-checked.
        </p>
        <table><thead><tr><th>Component</th><th>Source</th><th>Verification</th></tr></thead>
        <tbody>${secRows || '<tr><td colspan="3" class="empty">Run a scan to populate components.</td></tr>'}</tbody></table>
      </div>
      <div class="card" style="margin-top:16px">
        <h3>Issues (${(health.issues || []).length})</h3>
        ${issues || '<div class="empty">No issues detected. Your workstation looks healthy.</div>'}
      </div>`;
  }

  function issueCard(i) {
    const fix = fixButton(i);
    return `<div class="issue sev-${esc(i.severity)}">
      <h4>${esc(i.title)}</h4>
      <div class="muted">${esc(i.explanation || "")}</div>
      <div class="fix">Fix: ${esc(i.fix || "")}</div>
      ${i.why ? `<div class="why">${esc(i.why)}</div>` : ""}
      ${fix ? `<div class="issue-actions">${fix}</div>` : ""}
    </div>`;
  }

  function fixButton(i) {
    const a = i.fix_action;
    if (!a) return "";
    const key = i.component || "";
    if (a === "install")
      return `<button class="btn sm" data-act="install" data-key="${esc(key)}">Install ${esc(key)}</button>`;
    if (a === "update")
      return `<button class="btn sm warn" data-act="upgrade" data-key="${esc(key)}">Update ${esc(key)}</button>`;
    if (a === "start-ollama" || a === "start-docker")
      return `<button class="btn sm" data-act="repair" data-fix="${esc(a)}" data-key="${esc(key)}">Fix now</button>`;
    return "";
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
        <table><thead><tr><th>Component</th><th>State</th><th>Health</th><th>Version</th><th>Detail</th><th class="right">Actions</th></tr></thead>
        <tbody>${groups[cat].map(componentRow).join("")}</tbody></table></div>`
      )
      .join("");
  }

  function componentRow(c) {
    const key = c.key;
    const canAct = ["hardware", "os", "config"].indexOf(c.category) === -1;
    let actions = "";
    if (canAct) {
      if (c.state === "missing" || c.health === "gray") {
        actions += `<button class="btn sm" data-act="install" data-key="${esc(key)}">Install</button>`;
      } else if (c.state === "needs_update" || c.health === "yellow") {
        actions += `<button class="btn sm warn" data-act="upgrade" data-key="${esc(key)}">Update</button>`;
      } else if (c.state === "failed") {
        actions += `<button class="btn sm warn" data-act="install" data-key="${esc(key)}">Retry</button>`;
      }
      actions += `<button class="btn sm ghost" data-act="why" data-key="${esc(key)}" title="Why do I need this?">Why?</button>`;
      actions += `<button class="btn sm ghost" data-act="rescan" data-key="${esc(key)}" title="Re-detect">&#x21bb;</button>`;
    }
    const busy = ["installing", "configuring", "verifying", "repairing"].indexOf(c.state) !== -1;
    return `<tr data-row="${esc(key)}">
      <td><strong>${esc(c.name)}</strong></td>
      <td class="muted">${busy ? `<span class="spin"></span> ` : ""}${esc(c.state)}</td>
      <td>${badge(c.health)}</td>
      <td class="mono">${esc(c.version || "")}</td>
      <td class="muted">${esc(c.detail || "")}${c.error ? ` <span class="err-tip" title="${esc(c.error)}">&#9432;</span>` : ""}</td>
      <td class="right nowrap">${actions}</td>
    </tr>
    <tr class="why-row hidden" data-why="${esc(key)}"><td colspan="6"></td></tr>`;
  }

  async function renderModels() {
    const host = $("#view-models");
    const data = await api("/api/models");
    const recs = data.recommendations || [];
    const installed = data.installed || [];
    store.installed = new Set(installed.map((m) => m.name));
    const rows = recs.map(modelRow).join("");
    host.innerHTML = `
      <div class="card">
        <h3>Recommended for this machine</h3>
        <table><thead><tr><th>Model</th><th>Best for</th><th>Coding</th><th>Speed</th><th class="right">RAM</th><th class="right">tok/s</th><th>Fit</th><th class="right">Local</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="8" class="empty">Run a scan to size models.</td></tr>'}</tbody></table>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-head">
          <h3>Installed locally (${installed.length})</h3>
          <button class="btn sm ghost" data-act="refresh-models">&#x21bb; Refresh</button>
        </div>
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
            : '<div class="empty">No local models yet. Install one above, or start Ollama from Components.</div>'
        }
      </div>`;
  }

  function modelRow(r) {
    const local = store.installed.has(r.tag);
    const fitBadge =
      r.fit === "fits" ? badge("green") : r.fit === "tight" ? badge("yellow") : badge("red");
    const label = (r.labels || [])[0]
      ? `<span class="trust safe">${esc(r.labels[0])}</span>`
      : "";
    let action;
    if (local) {
      action = `<span class="tag local">installed</span>`;
    } else if (r.fit === "too_big") {
      action = `<button class="btn sm ghost" data-act="pull" data-key="${esc(r.key)}" title="May not run well on this machine">Install anyway</button>`;
    } else {
      action = `<button class="btn sm" data-act="pull" data-key="${esc(r.key)}">Install</button>`;
    }
    return `<tr>
      <td><strong>${esc(r.name)}</strong> ${label}</td>
      <td class="muted">${esc(r.best_for || "")}</td>
      <td>${stars(r.coding)}</td>
      <td>${stars(r.effective_speed)}</td>
      <td class="right">${esc(r.min_ram_gb ?? "")}G</td>
      <td class="right mono">${esc(r.tokens_per_sec ?? "")}</td>
      <td>${fitBadge} ${esc(r.fit || "")}</td>
      <td class="right">${action}</td>
    </tr>`;
  }

  async function renderConfig() {
    const host = $("#view-config");
    const [data, envData, backups] = await Promise.all([
      api("/api/config"),
      api("/api/env"),
      api("/api/backups"),
    ]);
    const cfgRows = (data.configs || [])
      .map(
        (cf) => `<tr>
        <td><strong>${esc(cf.name)}</strong><div class="muted tiny">${esc(cf.description || "")}</div></td>
        <td><span class="trust ${esc(cf.trust)}">${esc(cf.trust)}</span></td>
        <td>${cf.exists ? badge("green") : badge("gray")}</td>
        <td class="mono muted path-cell">
          <span class="copy-row">
            <span class="copy-text path-cell" data-act="edit-config" data-cfg="${esc(cf.key)}" title="Open / edit">${esc(cf.path || "")}</span>
            ${copyBtn(cf.path || "", "Copy path")}
          </span>
        </td>
        <td class="right"><button class="btn sm ghost" data-act="edit-config" data-cfg="${esc(cf.key)}">${cf.exists ? "Edit" : "Create"}</button></td>
      </tr>`
      )
      .join("");

    const p = data.path || {};
    const snapRows = (backups.snapshots || [])
      .map(
        (s) => `<tr>
        <td class="mono">${esc(s.id)}</td>
        <td>${s.file_count || 0}</td>
        <td class="right">
          <button class="btn sm ghost" data-act="restore-backup" data-id="${esc(s.id)}">Restore</button>
        </td>
      </tr>`
      )
      .join("");
    host.innerHTML = `
      <div class="card">
        <h3>Config files</h3>
        <table><thead><tr><th>File</th><th>Trust</th><th>Status</th><th>Path (click to edit)</th><th></th></tr></thead>
        <tbody>${cfgRows}</tbody></table>
      </div>
      <div class="grid cols-2" style="margin-top:16px">
        <div class="card">
          <div class="card-head">
            <h3>Environment variables</h3>
            <div class="seg">
              <button class="seg-btn ${store.envMode === "known" ? "on" : ""}" data-env="known">AI-relevant</button>
              <button class="seg-btn ${store.envMode === "all" ? "on" : ""}" data-env="all">All</button>
            </div>
          </div>
          <input class="search" id="env-search" placeholder="Filter variables..." value="${esc(store.envFilter)}" />
          <div id="env-list"></div>
        </div>
        <div class="card">
          <h3>PATH (${p.count || 0} entries)</h3>
          <div class="muted" style="margin-bottom:8px">
            ${(p.missing || []).length} missing · ${(p.duplicates || []).length} duplicate
          </div>
          <div class="mono pathbox">${(p.entries || [])
            .map(
              (e) =>
                `<div class="copy-row path-entry">
                  <span class="copy-text" title="${esc(e.path)}">${esc(e.path)} ${
                  e.exists ? "" : '<span style="color:var(--red)">MISSING</span>'
                } ${e.duplicate ? '<span style="color:var(--yellow)">DUP</span>' : ""}</span>
                  ${copyBtn(e.path, "Copy PATH entry")}
                </div>`
            )
            .join("")}</div>
        </div>
      </div>
      <div class="grid cols-2" style="margin-top:16px">
        <div class="card">
          <div class="card-head">
            <h3>Backups</h3>
            <button class="btn sm" data-act="create-backup">Create backup</button>
          </div>
          <p class="muted tiny">Global snapshots of Config Center files. Restore overwrites originals.</p>
          <table><thead><tr><th>Snapshot</th><th>Files</th><th></th></tr></thead>
          <tbody>${snapRows || '<tr><td colspan="3" class="empty">No snapshots yet.</td></tr>'}</tbody></table>
        </div>
        <div class="card">
          <h3>Diagnostics</h3>
          <p class="muted tiny" style="margin-bottom:12px">
            Bundle logs, state, and tool versions into a redacted zip for troubleshooting.
          </p>
          <button class="btn" data-act="download-diagnostics">Download diagnostics</button>
          <div id="diag-result" class="muted tiny" style="margin-top:10px"></div>
        </div>
      </div>`;
    store._env = envData;
    renderEnvList();
    const search = $("#env-search");
    if (search)
      search.addEventListener("input", (e) => {
        store.envFilter = e.target.value;
        renderEnvList();
      });
  }

  function renderEnvList() {
    const host = $("#env-list");
    if (!host || !store._env) return;
    const list = store.envMode === "all" ? store._env.all || [] : store._env.known || [];
    const q = store.envFilter.trim().toLowerCase();
    const rows = list
      .filter((e) => (store.envMode === "all" ? true : e.present))
      .filter((e) => !q || e.name.toLowerCase().includes(q))
      .map(
        (e) =>
          `<tr>
            <td class="mono">${esc(e.name)}${e.secret ? ' <span class="tag secret">secret</span>' : ""}</td>
            <td class="mono val">${
              e.present
                ? `<span class="copy-row"><span class="copy-text" title="${esc(e.value)}">${esc(
                    e.value
                  )}</span>${copyBtn(e.value, "Copy value")}</span>`
                : '<span class="muted">not set</span>'
            }</td>
          </tr>`
      )
      .join("");
    const count = list.filter((e) => (store.envMode === "all" ? true : e.present)).length;
    host.innerHTML = `<div class="muted tiny" style="margin:6px 0">${count} variable(s)</div>
      <table><tbody>${rows || '<tr><td class="empty">Nothing matches.</td></tr>'}</tbody></table>`;
  }

  function renderActivity() {
    const host = $("#view-activity");
    host.innerHTML = `<div class="card"><h3>Event stream</h3><div class="log" id="log"></div></div>`;
    const log = $("#log");
    log.innerHTML = store.events.slice(-500).map(logRow).join("");
    log.scrollTop = log.scrollHeight;
  }
  function logRow(e) {
    return `<div class="row"><span class="ts">${fmtTime(e.ts)}</span><span class="lvl ${esc(
      e.level
    )}">${esc(e.level)}</span><span>${esc(e.message)}</span></div>`;
  }

  async function renderUpdates() {
    const host = $("#view-updates");
    const data = await api("/api/updates");
    const self = data.self || {};
    const rows = (data.components || [])
      .map(
        (c) => `<tr>
        <td><strong>${esc(c.name)}</strong></td>
        <td class="mono">${esc(c.current || "missing")}</td>
        <td class="muted">${esc(c.minimum || "")}</td>
        <td class="right"><button class="btn sm warn" data-act="upgrade" data-key="${esc(c.key)}">Update</button></td>
      </tr>`
      )
      .join("");
    const selfBadge = self.update_available
      ? badge("yellow")
      : self.offline
        ? badge("gray")
        : badge("green");
    host.innerHTML = `
      <div class="card">
        <div class="card-head">
          <h3>Loadout</h3>
          <button class="btn sm ghost" data-act="refresh-updates">Check now</button>
        </div>
        <div class="kv">
          <div class="k">Installed</div><div class="v mono">${esc(self.current || "?")}</div>
          <div class="k">Latest (PyPI)</div><div class="v mono">${esc(self.latest || (self.offline ? "offline" : "?"))}</div>
          <div class="k">Status</div><div class="v">${selfBadge} ${self.update_available ? "update available" : self.offline ? "offline" : "up to date"}</div>
        </div>
        ${self.upgrade_hint ? `<p class="muted tiny">Upgrade: <code>${esc(self.upgrade_hint)}</code></p>` : ""}
        <p class="muted tiny">Rollback: <code>${esc((data.rollback || {}).loadout || "")}</code></p>
        ${self.changelog_url ? `<p class="muted tiny"><a href="${esc(self.changelog_url)}" target="_blank" rel="noopener">Changelog</a></p>` : ""}
      </div>
      <div class="card" style="margin-top:16px">
        <h3>Component upgrades (${(data.components || []).length})</h3>
        <table><thead><tr><th>Component</th><th>Version</th><th>Minimum</th><th></th></tr></thead>
        <tbody>${rows || '<tr><td colspan="4" class="empty">All managed components look current.</td></tr>'}</tbody></table>
      </div>`;
  }

  async function renderBenchmark() {
    const host = $("#view-benchmark");
    const data = await api("/api/benchmark/latest");
    const b = data.benchmark;
    const tier = b && b.tier ? b.tier.tier : "—";
    const label = b && b.tier ? b.tier.label : "Run a benchmark to size this machine.";
    host.innerHTML = `
      <div class="card">
        <div class="card-head">
          <h3>Latest results</h3>
          <button class="btn sm" data-act="run-benchmark">Run benchmark</button>
        </div>
        ${
          b
            ? `<div class="kv">
          <div class="k">Tier</div><div class="v"><span class="trust safe">${esc(tier)}</span> ${esc(label)}</div>
          <div class="k">CPU score</div><div class="v mono">${esc(b.cpu && b.cpu.score)}</div>
          <div class="k">Disk write</div><div class="v mono">${esc(b.disk && b.disk.write_mbps)} MB/s</div>
          <div class="k">Disk read</div><div class="v mono">${esc(b.disk && b.disk.read_mbps)} MB/s</div>
          <div class="k">RAM</div><div class="v">${esc(b.hardware && b.hardware.ram_gb)} GB</div>
          <div class="k">VRAM</div><div class="v">${esc(b.hardware && b.hardware.vram_gb)} GB</div>
          <div class="k">Inference</div><div class="v">${
            b.inference && b.inference.skipped
              ? esc("skipped (" + (b.inference.reason || "no Ollama") + ")")
              : esc((b.inference && b.inference.tokens_per_sec) + " tok/s")
          }</div>
        </div>`
            : '<div class="empty">No benchmark yet. Click Run benchmark (fast, ~1s).</div>'
        }
      </div>`;
  }

  async function renderVscode() {
    const host = $("#view-vscode");
    const data = await api("/api/vscode/preview");
    if (!data.ok) {
      host.innerHTML = `<div class="card"><div class="empty">${esc(data.reason || "Unavailable")}</div></div>`;
      return;
    }
    const extRows = (data.extensions || [])
      .map(
        (e) => `<tr><td class="mono">${esc(e.id)}</td><td>${esc(e.name)}</td><td class="muted tiny">${esc(e.reason || "")}</td>
        <td class="right"><button class="btn sm" data-act="install-ext" data-id="${esc(e.id)}">Install</button></td></tr>`
      )
      .join("");
    host.innerHTML = `
      <div class="card">
        <div class="card-head"><h3>${esc(data.editor)} settings</h3>
          <button class="btn sm" data-act="apply-vscode">Apply settings</button></div>
        <p class="muted tiny">Path: <span class="mono">${esc(data.settings_path)}</span></p>
        <p class="muted tiny">Keys to merge: ${esc((data.keys_added || []).join(", ") || "none")}</p>
        <pre class="pathbox mono" style="max-height:200px;overflow:auto">${esc(data.settings_content || "")}</pre>
      </div>
      <div class="card" style="margin-top:16px">
        <h3>Recommended extensions</h3>
        <table><thead><tr><th>ID</th><th>Name</th><th>Why</th><th></th></tr></thead>
        <tbody>${extRows}</tbody></table>
        <p class="muted tiny">Requires <code>code</code> or <code>cursor</code> on PATH.</p>
      </div>`;
  }

  async function renderContinue() {
    const host = $("#view-continue");
    const data = await api("/api/continue/preview");
    host.innerHTML = `
      <div class="card">
        <div class="card-head"><h3>Continue config (${esc(data.schema || "v1")})</h3>
          <button class="btn sm" data-act="apply-continue">Apply</button></div>
        <p class="muted tiny">${esc(data.note || "")}</p>
        <p class="muted tiny">Path: <span class="mono">${esc(data.path || "")}</span></p>
        <pre class="pathbox mono" style="max-height:320px;overflow:auto">${esc(data.content || "")}</pre>
      </div>`;
  }

  async function renderAgents() {
    const host = $("#view-agents");
    const data = await api("/api/agents/preview");
    const agents = (data.agents || [])
      .map((a) => `<li>${esc(a.name)} (${esc(a.key)})</li>`)
      .join("");
    const folders = (data.folders || [])
      .map((f) => `<li class="mono">${esc(f.path)} — ${esc(f.action)}</li>`)
      .join("");
    host.innerHTML = `
      <div class="card">
        <div class="card-head"><h3>Agent CLIs</h3>
          <button class="btn sm" data-act="apply-agents">Apply scaffold</button></div>
        <ul>${agents || "<li class='muted'>None detected yet — run Rescan.</li>"}</ul>
        <p class="muted tiny">${esc(data.note || "")}</p>
      </div>
      <div class="grid cols-2" style="margin-top:16px">
        <div class="card"><h3>MCP config preview</h3>
          <pre class="pathbox mono" style="max-height:200px;overflow:auto">${esc(data.mcp_content || "")}</pre></div>
        <div class="card"><h3>Folders</h3><ul class="mono tiny">${folders}</ul></div>
      </div>`;
  }

  async function renderTemplates() {
    const host = $("#view-templates");
    const data = await api("/api/templates");
    host.innerHTML = `<div class="panel"><h3>Project templates</h3>
      <div class="grid">${(data.templates || [])
        .map(
          (t) => `<div class="card"><strong>${esc(t.name)}</strong>
            <p class="muted tiny">${esc(t.description)}</p>
            <button class="btn sm" data-act="scaffold-template" data-key="${esc(t.key)}">Create project</button></div>`
        )
        .join("")}</div>
      <pre class="mono tiny" id="tpl-result"></pre></div>`;
  }

  async function renderProfiles() {
    const host = $("#view-profiles");
    const list = await api("/api/profiles");
    host.innerHTML = `<div class="panel"><h3>Profile install wizard</h3>
      <p class="muted">Preview a full install plan, confirm once, then steps run sequentially with streaming logs.</p>
      <div class="grid">${(list.profiles || [])
        .map(
          (p) => `<div class="card"><strong>${esc(p.name)}</strong>
            <p class="muted tiny">${esc(p.description)}</p>
            <p class="tiny">${p.deps} deps · ${p.runtimes} runtimes</p>
            <button class="btn sm" data-act="profile-install" data-key="${esc(p.key)}" ${
              store.online ? "" : 'disabled title="' + esc(netTip()) + '"'
            }>Install profile</button></div>`
        )
        .join("")}</div></div>`;
  }

  async function renderConnections() {
    const host = $("#view-connections");
    const data = await api("/api/connections");
    host.innerHTML = `<div class="panel"><h3>Provider connections</h3>
      <p class="muted tiny">${esc(data.note || "")}</p>
      <table class="tbl"><thead><tr><th>Provider</th><th>Status</th><th>Env vars</th><th>Unlocks</th></tr></thead>
      <tbody>${(data.connections || [])
        .map(
          (c) => `<tr><td>${esc(c.name)}</td>
            <td>${c.present ? badge("green") : badge("gray")}</td>
            <td class="mono tiny">${esc((c.env_vars || []).join(", "))}</td>
            <td class="tiny">${esc((c.unlocks || []).join("; "))}
              ${c.docs_url ? `<div>${linkRow(c.docs_url, "Setup docs")}</div>` : ""}</td></tr>`
        )
        .join("")}</tbody></table></div>`;
  }

  async function renderSettings() {
    const host = $("#view-settings");
    const tel = await api("/api/telemetry");
    const mon = await api("/api/monitor");
    const preview = tel.sample || {};
    host.innerHTML = `<div class="panel"><h3>Privacy & telemetry</h3>
      <p class="muted">Opt-in only, disabled by default. Local storage only — no transmission endpoint.</p>
      <label class="row"><input type="checkbox" id="tel-enabled" ${tel.enabled ? "checked" : ""} />
        Enable anonymous local telemetry</label>
      <p class="tiny muted"><a href="https://github.com/bnvukin/ai-loadout/blob/main/PRIVACY.md" target="_blank" rel="noopener">PRIVACY.md</a></p>
      <pre class="mono tiny">${esc(JSON.stringify(preview, null, 2))}</pre>
      <h3>Continuous monitor</h3>
      <p class="muted tiny">Optional periodic rescan (default off). Minimum interval 60s.</p>
      <label class="row"><input type="checkbox" id="mon-enabled" ${mon.settings.monitor_enabled ? "checked" : ""} />
        Enable auto-rescan</label>
      <label>Interval (seconds): <input type="number" id="mon-interval" min="60" value="${esc(
        mon.settings.monitor_interval_sec || 300
      )}" /></label>
      <button class="btn sm" id="save-settings">Save settings</button></div>`;
    $("#save-settings").addEventListener("click", saveSettings);
  }

  async function saveSettings() {
    const enabled = $("#tel-enabled").checked;
    const mon = $("#mon-enabled").checked;
    const interval = parseInt($("#mon-interval").value || "300", 10);
    await post("/api/telemetry", { enabled });
    await post("/api/monitor", { enabled: mon, interval });
    toast("Settings saved", "success");
    if (store.view === "settings") refresh();
  }

  async function startProfileInstall(key) {
    if (!store.online) return toast(netTip(), "warning");
    const dry = await post(`/api/profiles/${encodeURIComponent(key)}/install`, {});
    const plan = dry.json.plan || {};
    const steps = (plan.steps || []).filter((s) => s.action !== "skip");
    const body = `<p>Profile <strong>${esc(key)}</strong> — ${steps.length} actionable step(s).</p>
      <ul class="tiny">${steps
        .slice(0, 12)
        .map((s) => `<li>${esc(s.action)} ${esc(s.name)} — ${esc(s.command || s.reason || "")}</li>`)
        .join("")}</ul>
      <div class="banner warn">Installs run sequentially; network required.</div>`;
    openModal(`Install profile: ${key}`, body, `<button class="btn ghost" data-act="modal-close">Cancel</button>
      <button class="btn" id="confirm-profile">Install all</button>`);
    const run = $("#confirm-profile");
    if (run)
      run.addEventListener("click", async () => {
        closeModal();
        openActionLog(key, `Profile ${key}`);
        await post(`/api/profiles/${encodeURIComponent(key)}/install`, { confirm: true });
      });
  }

  const RENDERERS = {
    overview: renderOverview,
    components: renderComponents,
    models: renderModels,
    config: renderConfig,
    updates: renderUpdates,
    benchmark: renderBenchmark,
    vscode: renderVscode,
    continue: renderContinue,
    agents: renderAgents,
    templates: renderTemplates,
    profiles: renderProfiles,
    connections: renderConnections,
    settings: renderSettings,
    activity: renderActivity,
  };

  function refresh() {
    const fn = RENDERERS[store.view];
    if (fn) fn().catch((e) => console.error(e));
  }

  // -- actions ------------------------------------------------------------------
  async function startComponentAction(key, action) {
    if (!store.online) return toast(netTip(), "warning");
    const info = await api(`/api/component/${encodeURIComponent(key)}/advice`);
    const cmd = action === "upgrade" ? info.upgrade : info.install;
    const adv = info.advice || {};
    const body = cmd.ok
      ? `<p class="lead">${esc(adv.impact || "")}</p>
         ${adv.needed_for ? `<p class="muted">Unlocks: ${esc(adv.needed_for)}</p>` : ""}
         <div class="cmd-label">This command will run:</div>
         ${cmdBlock(cmd.display)}
         ${cmd.needs_admin ? '<div class="banner warn">This may prompt for administrator access (UAC / sudo).</div>' : ""}
         ${adv.link ? `<p class="muted tiny">${linkRow(adv.link)}</p>` : ""}`
      : `<p class="lead">${esc(adv.impact || "")}</p>
         <div class="banner warn">${esc(cmd.reason || "No automatic installer available.")}</div>
         ${adv.link ? `<p>${linkRow(adv.link, adv.link)}</p>` : ""}`;
    const foot = cmd.ok
      ? `<button class="btn ghost" data-act="modal-close">Cancel</button>
         <button class="btn" id="confirm-run">${action === "upgrade" ? "Update" : "Install"} now</button>`
      : `<button class="btn ghost" data-act="modal-close">Close</button>`;
    openModal(`${action === "upgrade" ? "Update" : "Install"} ${cmd.name || key}`, body, foot);
    const run = $("#confirm-run");
    if (run)
      run.addEventListener("click", async () => {
        openActionLog(key, `${action} ${cmd.name || key}`);
        const res = await post(`/api/component/${encodeURIComponent(key)}/${action}`, {
          confirm: true,
        });
        if (!res.ok || res.json.started === false)
          toast(res.json.busy ? "Another action is running." : "Could not start.", "warning");
      });
  }

  async function startModelPull(key) {
    if (!store.online) return toast(netTip(), "warning");
    const dry = await post(`/api/models/${encodeURIComponent(key)}/pull`, {});
    const cmd = (dry.json || {}).command || {};
    const body = cmd.ok
      ? `<p class="lead">Download and register this model with Ollama.</p>
         <div class="cmd-label">This command will run:</div>
         ${cmdBlock(cmd.display, "Copy pull command")}
         <div class="banner">Models are large (GBs) - the first pull can take a while.</div>`
      : `<div class="banner warn">${esc(cmd.reason || "Ollama is required to pull models.")}</div>
         <p>Install Ollama from the Components tab first.</p>`;
    const foot = cmd.ok
      ? `<button class="btn ghost" data-act="modal-close">Cancel</button>
         <button class="btn" id="confirm-pull">Install model</button>`
      : `<button class="btn ghost" data-act="modal-close">Close</button>`;
    openModal(`Install ${cmd.name || key}`, body, foot);
    const run = $("#confirm-pull");
    if (run)
      run.addEventListener("click", async () => {
        openActionLog(key, `pull ${cmd.name || key}`);
        await post(`/api/models/${encodeURIComponent(key)}/pull`, { confirm: true });
      });
  }

  async function refreshModels() {
    toast("Refreshing local models...");
    await post("/api/models/refresh", {});
    if (store.view === "models") refresh();
  }

  async function rescanComponent(key) {
    toast(`Re-detecting ${key}...`);
    const res = await post(`/api/component/${encodeURIComponent(key)}/rescan`, {});
    if (store.view === "components") refresh();
    const h = res.json && res.json.component && res.json.component.health;
    if (h) toast(`${key}: ${h}`, h === "green" ? "success" : "info");
  }

  async function startRepair(fix, key) {
    if (fix === "install") return startComponentAction(key, "install");
    if (fix === "update") return startComponentAction(key, "upgrade");
    if (fix === "path-dedupe" || fix === "fix-loadout-perms") {
      const label = fix === "path-dedupe" ? "Deduplicate PATH" : "Fix Loadout directory permissions";
      openModal(
        label,
        fix === "path-dedupe"
          ? "<p>Removes duplicate PATH entries. Your PATH is backed up first. On Windows, HKCU Path is updated.</p>"
          : "<p>Ensures ~/.ai-loadout directories exist and are writable.</p>",
        `<button class="btn ghost" data-act="modal-close">Cancel</button>
         <button class="btn" id="confirm-repair">Run repair</button>`
      );
      const run = $("#confirm-repair");
      if (run)
        run.addEventListener("click", async () => {
          closeModal();
          openActionLog(fix, label);
          await post("/api/repair", { action: fix, target: key || null, confirm: true });
        });
      return;
    }
    const label = fix === "start-ollama" ? "Start the Ollama server" : "Start Docker Desktop";
    openActionLog(key || fix, label);
    const res = await post("/api/repair", { action: fix, target: key || null });
    if (res.json && res.json.guidance) appendActionLog(res.json.guidance);
  }

  async function createBackup() {
    toast("Creating snapshot...");
    const res = await post("/api/backups", {});
    if (res.ok) {
      toast(`Backup ${res.json.id} created (${res.json.file_count} files).`, "success");
      if (store.view === "config") refresh();
    } else {
      toast("Backup failed.", "warning");
    }
  }

  async function startRestoreBackup(id) {
    const body = `<p class="lead">Restore snapshot <code>${esc(id)}</code>?</p>
      <div class="banner warn">This overwrites current config files with the snapshot copies.</div>
      <div class="confirm-gate"><label>Type <code>RESTORE</code> to proceed (EXPERT):</label>
      <input id="gate" placeholder="RESTORE" autocomplete="off" /></div>`;
    const foot = `<button class="btn ghost" data-act="modal-close">Cancel</button>
      <button class="btn warn" id="confirm-restore">Restore now</button>`;
    openModal("Restore backup", body, foot);
    const run = $("#confirm-restore");
    if (run)
      run.addEventListener("click", async () => {
        const token = ($("#gate").value || "").trim();
        const res = await post(`/api/backups/${encodeURIComponent(id)}/restore`, {
          confirm: token,
        });
        if (res.ok) {
          toast(`Restored ${res.json.file_count} file(s).`, "success");
          closeModal();
          if (store.view === "config") refresh();
        } else {
          const d = res.json.detail || res.json;
          toast((d && d.error) || "Restore blocked.", "warning");
        }
      });
  }

  async function downloadDiagnostics() {
    toast("Building diagnostics bundle...");
    const res = await post("/api/diagnostics", {});
    const host = $("#diag-result");
    if (!res.ok) {
      toast("Diagnostics failed.", "warning");
      return;
    }
    const j = res.json;
    const link = `/api/diagnostics/${encodeURIComponent(j.filename)}`;
    if (host)
      host.innerHTML = `Saved: <a href="${esc(link)}" download>${esc(j.filename)}</a> (${esc(j.path)})`;
    toast("Diagnostics ready.", "success");
  }

  async function refreshUpdates() {
    toast("Checking for updates...");
    if (store.view === "updates") refresh();
  }

  async function runBenchmark() {
    toast("Running benchmark...");
    openActionLog("benchmark", "Benchmark");
    const res = await post("/api/benchmark", {});
    if (!res.ok || res.json.started === false) {
      toast(res.json.busy ? "Another action is running." : "Could not start benchmark.", "warning");
    }
  }

  async function applyVscode() {
    openModal(
      "Apply VS Code settings",
      "<p>Merges recommended AI-dev defaults into settings.json. Your existing keys are preserved; a backup is created first.</p>",
      `<button class="btn ghost" data-act="modal-close">Cancel</button>
       <button class="btn" id="confirm-vscode">Apply settings</button>`
    );
    const run = $("#confirm-vscode");
    if (run)
      run.addEventListener("click", async () => {
        closeModal();
        openActionLog("vscode", "Apply VS Code settings");
        await post("/api/vscode/apply", { confirm: true });
      });
  }

  async function installExtension(id) {
    const dry = await post(`/api/vscode/extensions/${encodeURIComponent(id)}/install`, {});
    const cmd = dry.json.command || {};
    openModal(
      `Install ${id}`,
      cmd.ok
        ? `<div class="cmd-label">Command:</div>${cmdBlock(cmd.display)}`
        : `<div class="banner warn">${esc(cmd.reason || "Cannot install")}</div>`,
      cmd.ok
        ? `<button class="btn ghost" data-act="modal-close">Cancel</button><button class="btn" id="confirm-ext">Install</button>`
        : `<button class="btn ghost" data-act="modal-close">Close</button>`
    );
    const run = $("#confirm-ext");
    if (run)
      run.addEventListener("click", async () => {
        closeModal();
        openActionLog("vscode", `extension ${id}`);
        await post(`/api/vscode/extensions/${encodeURIComponent(id)}/install`, { confirm: true });
      });
  }

  async function applyContinue() {
    openModal(
      "Apply Continue config",
      "<p>Writes merged config to ~/.continue/. Secrets stay as env placeholders. Backup first.</p>",
      `<button class="btn ghost" data-act="modal-close">Cancel</button>
       <button class="btn" id="confirm-cont">Apply</button>`
    );
    const run = $("#confirm-cont");
    if (run)
      run.addEventListener("click", async () => {
        closeModal();
        openActionLog("continue", "Apply Continue config");
        await post("/api/continue/apply", { confirm: true });
      });
  }

  async function applyAgents() {
    openModal(
      "Apply agent / MCP scaffold",
      "<p>Creates starter MCP config and workspace folders. Backup if MCP file exists.</p>",
      `<button class="btn ghost" data-act="modal-close">Cancel</button>
       <button class="btn" id="confirm-agents">Apply</button>`
    );
    const run = $("#confirm-agents");
    if (run)
      run.addEventListener("click", async () => {
        closeModal();
        openActionLog("agents", "Agent scaffold");
        await post("/api/agents/apply", { confirm: true });
      });
  }

  async function startScaffoldTemplate(key) {
    const name = prompt("Project name:", "my-ai-project");
    if (!name) return;
    const dir = prompt("Target directory:", name);
    if (!dir) return;
    const dry = await post(`/api/templates/${encodeURIComponent(key)}/scaffold`, { name, dir });
    openModal(
      `Create ${key} project`,
      `<p>Scaffold <strong>${esc(name)}</strong> into <code>${esc(dir)}</code></p>`,
      `<button class="btn ghost" data-act="modal-close">Cancel</button>
       <button class="btn" id="confirm-tpl">Create</button>`
    );
    const run = $("#confirm-tpl");
    if (run)
      run.addEventListener("click", async () => {
        const res = await post(`/api/templates/${encodeURIComponent(key)}/scaffold`, {
          name,
          dir,
          confirm: true,
        });
        closeModal();
        if (res.ok) {
          toast(`Created in ${dir}`, "success");
          const host = $("#tpl-result");
          if (host) host.textContent = (res.json.written || []).join(", ");
        } else toast("Scaffold failed (dir not empty?).", "warning");
      });
  }

  async function toggleWhy(key, btn) {
    const row = $(`tr[data-why="${CSS.escape(key)}"]`);
    if (!row) return;
    if (!row.classList.contains("hidden")) {
      row.classList.add("hidden");
      return;
    }
    const cell = row.firstElementChild;
    cell.innerHTML = '<div class="why-box">Loading...</div>';
    row.classList.remove("hidden");
    const info = await api(`/api/component/${encodeURIComponent(key)}/advice`);
    const adv = info.advice || {};
    cell.innerHTML = `<div class="why-box">
      <div><strong>Impact if missing:</strong> ${esc(adv.impact || "")}</div>
      ${adv.needed_for ? `<div><strong>Needed for:</strong> ${esc(adv.needed_for)}</div>` : ""}
      <div class="muted tiny">${adv.optional ? "Optional" : "Recommended"}${
        adv.link ? ` · ${linkRow(adv.link, "documentation")}` : ""
      }</div>
      ${info.install && info.install.ok ? `<div class="cmd-label">Install command:</div>${cmdBlock(info.install.display)}` : ""}
      ${info.upgrade && info.upgrade.ok ? `<div class="cmd-label">Update command:</div>${cmdBlock(info.upgrade.display, "Copy update command")}` : ""}
    </div>`;
  }

  // -- config editor ------------------------------------------------------------
  async function openConfigEditor(key) {
    const res = await api(`/api/config/${encodeURIComponent(key)}?raw=1`);
    const meta = await api("/api/config"); // for trust/name
    const cf = (meta.configs || []).find((c) => c.key === key) || {};
    const trust = res.trust || cf.trust || "safe";
    const needsToken = trust === "advanced" ? "CONFIRM" : trust === "expert" ? "EDIT" : null;
    const content = res.content != null ? res.content : "";
    const secretWarn = cf.secret
      ? '<div class="banner warn">This file may contain secrets - they are shown in full here for editing. Be careful sharing your screen.</div>'
      : "";
    const body = `
      <div class="editor-meta"><span class="trust ${esc(trust)}">${esc(trust)}</span>
        <span class="copy-row"><span class="mono muted tiny">${esc(res.path || cf.path || "")}</span>${copyBtn(res.path || cf.path || "", "Copy path")}</span></div>
      ${secretWarn}
      <textarea class="editor" id="editor" spellcheck="false">${esc(content)}</textarea>
      ${
        needsToken
          ? `<div class="confirm-gate"><label>Type <code>${needsToken}</code> to save (${trust} file):</label>
             <input class="search" id="gate" placeholder="${needsToken}" /></div>`
          : ""
      }`;
    const foot = `<button class="btn ghost" data-act="modal-close">Cancel</button>
      <button class="btn" id="save-config">Save${res.exists === false ? " (create)" : ""}</button>`;
    openModal(`${cf.name || key}`, body, foot);
    $("#save-config").addEventListener("click", async () => {
      const payload = { content: $("#editor").value };
      if (needsToken) payload.confirm = ($("#gate").value || "").trim();
      const r = await post(`/api/config/${encodeURIComponent(key)}`, payload);
      if (r.ok) {
        toast(`Saved${r.json.backup ? " (backup made)" : ""}.`, "success");
        closeModal();
        if (store.view === "config") refresh();
      } else {
        const d = (r.json && r.json.detail) || {};
        toast(d.error || "Save failed.", "warning");
      }
    });
  }

  // -- action log modal (live install/pull output) -----------------------------
  function openActionLog(target, title) {
    const body = `<pre class="action-log" id="action-log">Starting...\n</pre>`;
    const foot = `<span class="muted tiny" id="action-done"></span>
      <button class="btn sm ghost" data-act="copy-log">Copy log</button>
      <button class="btn ghost" data-act="modal-close">Close</button>`;
    openModal(title, body, foot);
    store.action = { target, logEl: $("#action-log"), doneEl: $("#action-done") };
    startActionPolling();
  }
  function appendActionLog(line) {
    if (!store.action || !store.action.logEl) return;
    store.action.logEl.textContent += line + "\n";
    store.action.logEl.scrollTop = store.action.logEl.scrollHeight;
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
    if (ev.id > store.lastEventId) store.lastEventId = ev.id;
    store.events.push(ev);
    if (ev.message && /Scan started/i.test(ev.message)) store.tasks = {};
    if (ev.kind === "progress" && ev.data && ev.data.status) {
      store.tasks[ev.data.target] = ev.data.status;
      renderProgress();
      if (ev.data.status === "done") scheduleRefresh();
    }
    if (ev.kind === "step" && /complete/i.test(ev.message || "")) scheduleRefresh();

    // Live action / repair output -> the open action-log modal.
    if ((ev.source === "action" || ev.source === "repair") && store.action) {
      appendActionLog(ev.message || "");
      if (ev.level === "success" || ev.level === "error") {
        if (store.action.doneEl)
          store.action.doneEl.textContent = ev.level === "success" ? "Done." : "Failed - see log.";
        scheduleRefresh();
        if (store.view !== "components" && store.view !== "models") scheduleRefresh();
      }
    }
    // A component's state changed (install finished, rescan) -> refresh the grid live.
    if (ev.kind === "state" && (store.view === "components" || store.view === "models"))
      scheduleRefresh();

    if (store.view === "activity") {
      const log = $("#log");
      if (log) {
        log.insertAdjacentHTML("beforeend", logRow(ev));
        log.scrollTop = log.scrollHeight;
      }
    }
  }

  let actionPollTimer = null;
  let actionPollAfterId = 0;

  function stopActionPolling() {
    if (actionPollTimer) {
      clearInterval(actionPollTimer);
      actionPollTimer = null;
    }
  }

  async function startActionPolling() {
    stopActionPolling();
    try {
      const snap = await api("/api/events");
      actionPollAfterId = snap.last || store.lastEventId || 0;
    } catch (_) {
      actionPollAfterId = store.lastEventId || 0;
    }
    actionPollTimer = setInterval(async () => {
      if (!store.action) {
        stopActionPolling();
        return;
      }
      try {
        const snap = await api(`/api/events?after=${actionPollAfterId}`);
        actionPollAfterId = snap.last || actionPollAfterId;
        for (const ev of snap.events || []) handleEvent(ev);
      } catch (_) {}
    }, 1200);
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

  // -- global click delegation --------------------------------------------------
  function onClick(e) {
    const seg = e.target.closest("[data-env]");
    if (seg) {
      store.envMode = seg.dataset.env;
      renderConfig();
      return;
    }
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const act = el.dataset.act;
    if (act === "modal-close") return closeModal();
    if (act === "copy-log") {
      const log = $("#action-log");
      if (log) copyText(log.textContent || "", "Log copied");
      return;
    }
    if (act === "copy") return copyText(el.dataset.copy || "", el.dataset.label || "Copied");
    if (act === "install") return startComponentAction(el.dataset.key, "install");
    if (act === "upgrade") return startComponentAction(el.dataset.key, "upgrade");
    if (act === "rescan") return rescanComponent(el.dataset.key);
    if (act === "why") return toggleWhy(el.dataset.key, el);
    if (act === "pull") return startModelPull(el.dataset.key);
    if (act === "refresh-models") return refreshModels();
    if (act === "repair") return startRepair(el.dataset.fix, el.dataset.key);
    if (act === "edit-config") return openConfigEditor(el.dataset.cfg);
    if (act === "create-backup") return createBackup();
    if (act === "restore-backup") return startRestoreBackup(el.dataset.id);
    if (act === "download-diagnostics") return downloadDiagnostics();
    if (act === "refresh-updates") return refreshUpdates();
    if (act === "run-benchmark") return runBenchmark();
    if (act === "apply-vscode") return applyVscode();
    if (act === "install-ext") return installExtension(el.dataset.id);
    if (act === "apply-continue") return applyContinue();
    if (act === "apply-agents") return applyAgents();
    if (act === "scaffold-template") return startScaffoldTemplate(el.dataset.key);
    if (act === "profile-install") return startProfileInstall(el.dataset.key);
  }

  // -- boot ---------------------------------------------------------------------
  function init() {
    $$(".nav-item").forEach((n) => n.addEventListener("click", () => setView(n.dataset.view)));
    document.addEventListener("click", onClick);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
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
    api("/api/events")
      .then((snap) => {
        actionPollAfterId = snap.last || 0;
        for (const ev of snap.events || []) handleEvent(ev);
      })
      .catch(() => {});
    setView("overview");
    pollConnectivity();
    setInterval(pollConnectivity, 60000);
    connect();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
