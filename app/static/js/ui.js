(function () {
  const route = window.HEALOPS_PAGE || "";
  markActiveNav();

  if (route === "dashboard") loadDashboard();
  if (route === "incidents") loadIncidents();

  function markActiveNav() {
    const map = { dashboard: "/dashboard", incidents: "/incidents", about: "/about" };
    const active = map[route] || window.location.pathname;
    document.querySelectorAll(".nav-link").forEach(a => {
      if (a.getAttribute("href") === active) a.classList.add("active");
    });
  }

  async function loadDashboard() {
    const cardsEl = document.getElementById("dashCards");
    const tbody = document.querySelector("#latestTable tbody");

    const res = await fetch("/api/dashboard");
    const data = await res.json();

    const s = data.summary;
    const avg = s.avg_mttr_seconds == null ? "—" : humanize(s.avg_mttr_seconds);

    cardsEl.innerHTML = `
      <div class="card glass">
        <h3>System Status</h3>
        <p class="value">
          <span class="badge"><span class="dot ok"></span>RUNNING</span>
        </p>
        <div class="hint">ALB reachable, ECS desired tasks maintained.</div>
      </div>

      <div class="card glass">
        <h3>Total Incidents</h3>
        <p class="value">${s.total_incidents}</p>
        <div class="hint">All observed failures recorded with recovery time and action.</div>
      </div>

      <div class="card glass">
        <h3>Average MTTR</h3>
        <p class="value">${avg}</p>
        <div class="hint">Mean time to recovery across resolved incidents.</div>
      </div>

      <div class="card glass">
        <h3>Open vs Resolved</h3>
        <p class="value">${s.open} / ${s.resolved}</p>
        <div class="hint">Open incidents still active; resolved incidents recovered.</div>
      </div>

      <div class="card glass">
        <h3>Detection Coverage</h3>
        <p class="value">CloudWatch</p>
        <div class="hint">Detection source is documented per incident (demo now, live later).</div>
      </div>

      <div class="card glass">
        <h3>Healing Mechanism</h3>
        <p class="value">ECS Scheduler</p>
        <div class="hint">Service scheduler replaces failed tasks automatically.</div>
      </div>
    `;

    tbody.innerHTML = "";
    (data.latest || []).forEach(i => {
      const sev = `<span class="tag ${i.severity === "P1" ? "p1" : "p2"}">${i.severity}</span>`;
      const st = i.status === "RESOLVED"
        ? `<span class="tag res">RESOLVED</span>`
        : `<span class="tag open">OPEN</span>`;

      const row = document.createElement("tr");
      row.innerHTML = `
        <td><b>${i.id}</b> — ${escapeHtml(i.title)}</td>
        <td>${sev}</td>
        <td>${st}</td>
        <td>${escapeHtml(i.detection)}</td>
        <td>${escapeHtml(i.healing_action)}</td>
        <td><b>${i.mttr_human || "—"}</b></td>
      `;
      tbody.appendChild(row);
    });
  }

  async function loadIncidents() {
    const tbody = document.querySelector("#incTable tbody");
    const res = await fetch("/api/incidents");
    const data = await res.json();

    tbody.innerHTML = "";
    (data.items || []).forEach((i, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><b>${i.failure_hm}</b></td>
        <td>${escapeHtml(i.component || "ECS Service")}</td>
        <td style="color:var(--bad); font-weight:700">${escapeHtml(i.failure || "Task exited")}</td>
        <td>${escapeHtml(i.detection)}</td>
        <td style="color:var(--ok); font-weight:700">${escapeHtml(i.healing_action)}</td>
        <td><b>${i.mttr_human || "—"}</b></td>
      `;

      const detailTr = document.createElement("tr");
      detailTr.className = "detail-row";
      detailTr.style.display = "none";
      detailTr.innerHTML = `
        <td colspan="6">
          <div class="detail">
            <div class="box">
              <h4>What broke</h4>
              <p>${escapeHtml(i.what_broke || "ECS task exited; service briefly dropped below desired count.")}</p>
            </div>
            <div class="box">
              <h4>Impact</h4>
              <p>${escapeHtml(i.impact || "Users could not reach the service until a healthy target returned.")}</p>
            </div>
            <div class="box">
              <h4>Detected by</h4>
              <p>${escapeHtml(i.detection_detail || "CloudWatch observed service health / task count anomaly.")}</p>
            </div>
            <div class="box">
              <h4>How it healed</h4>
              <p>${escapeHtml(i.healing_detail || "ECS scheduler replaced the failed task; ALB health checks confirmed recovery.")}</p>
            </div>
            <div class="box">
              <h4>Timeline</h4>
              <p>
                Failure: <b>${i.failure_hm}</b> • Recovery: <b>${i.recovery_hm}</b> • MTTR: <b>${i.mttr_human || "—"}</b>
              </p>
            </div>
            <div class="box">
              <h4>Learning</h4>
              <p>${escapeHtml(i.learning || "Self-healing is not magic — it’s health checks + scheduler behavior + observable timelines.")}</p>
            </div>
          </div>
        </td>
      `;

      tr.addEventListener("click", () => {
        detailTr.style.display = detailTr.style.display === "none" ? "" : "none";
      });

      tbody.appendChild(tr);
      tbody.appendChild(detailTr);
    });
  }

  function humanize(secs) {
    if (secs < 60) return `${secs}s`;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    if (m < 60) return `${m}m ${s}s`;
    const h = Math.floor(m / 60);
    const rm = m % 60;
    return `${h}h ${rm}m`;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
})();
