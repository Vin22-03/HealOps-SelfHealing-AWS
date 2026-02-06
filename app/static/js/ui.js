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

  /* ---------------- DASHBOARD (UNCHANGED) ---------------- */

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
        <p class="value"><span class="badge"><span class="dot ok"></span>RUNNING</span></p>
        <div class="hint">ECS service maintaining desired tasks.</div>
      </div>

      <div class="card glass">
        <h3>Total Incidents</h3>
        <p class="value">${s.total_incidents}</p>
        <div class="hint">All failures recorded via EventBridge / CloudWatch.</div>
      </div>

      <div class="card glass">
        <h3>Average MTTR</h3>
        <p class="value">${avg}</p>
        <div class="hint">Calculated from observed recovery timestamps.</div>
      </div>

      <div class="card glass">
        <h3>Open vs Resolved</h3>
        <p class="value">${s.open_incidents} / ${s.resolved_incidents}</p>
        <div class="hint">Live operational state.</div>
      </div>

      <div class="card glass">
        <h3>Detection</h3>
        <p class="value">EventBridge</p>
        <div class="hint">ECS Task State Change events.</div>
      </div>

      <div class="card glass">
        <h3>Healing</h3>
        <p class="value">ECS Scheduler</p>
        <div class="hint">Desired count enforcement.</div>
      </div>
    `;

    tbody.innerHTML = "";

    if (data.latest) {
      const i = data.latest;
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${formatTime(i.failure_time)}</td>
        <td>${escapeHtml(i.component)} / ${escapeHtml(i.cluster || "healops-cluster")}</td>
        <td style="color:var(--bad);font-weight:700">${escapeHtml(i.incident_type)}</td>
        <td>${escapeHtml(i.detection)}</td>
        <td style="color:var(--ok);font-weight:700">
          ${escapeHtml(i.healing_action || "ECS Scheduler")}
        </td>
        <td><b>${i.mttr_human || "—"}</b></td>
      `;
      tbody.appendChild(row);
    }
  }

  /* ---------------- INCIDENTS (CLEAN + TRUSTWORTHY) ---------------- */

  async function loadIncidents() {
    const tbody = document.querySelector("#incTable tbody");
    const res = await fetch("/api/incidents");
    const data = await res.json();

    tbody.innerHTML = "";

    (data.items || []).forEach(i => {
      const tr = document.createElement("tr");

      tr.innerHTML = `
        <td><b>${formatTime(i.failure_time)}</b></td>
        <td>${escapeHtml(i.component)} / ${escapeHtml(i.cluster)}</td>
        <td style="color:var(--bad);font-weight:700">${escapeHtml(i.incident_type)}</td>
        <td>${escapeHtml(i.detection)}</td>
        <td style="color:var(--ok);font-weight:700">${escapeHtml(i.healing_action || "-")}</td>
        <td><b>${i.mttr_human || "—"}</b></td>
        <td>${escapeHtml(i.status)}</td>
      `;

      const detailTr = document.createElement("tr");
      detailTr.className = "detail-row";
      detailTr.style.display = "none";

      detailTr.innerHTML = `
        <td colspan="7">
          <div class="detail">

            <div class="box">
              <h4>Failure</h4>
              <p>${escapeHtml(i.failure_type)}</p>
            </div>

            <div class="box">
              <h4>Timeline</h4>
              <p>
                Detected: <b>${formatTime(i.failure_time)}</b><br/>
                Recovered: <b>${formatTime(i.healed_time)}</b><br/>
                MTTR: <b>${i.mttr_human || "—"}</b>
              </p>
            </div>

            ${
              i.desired_before != null || i.running_before != null
                ? `
            <div class="box">
              <h4>Autoscaling Evidence</h4>
              <p>
                Desired: <b>${fmt(i.desired_before)} → ${fmt(i.desired_after)}</b><br/>
                Running: <b>${fmt(i.running_before)} → ${fmt(i.running_after)}</b><br/>
                Alarm: ${escapeHtml(i.alarm_name || "-")}
              </p>
            </div>
            `
                : ""
            }

            ${
              i.task_arn
                ? `
            <div class="box">
              <h4>Task Evidence</h4>
              <p>
                Task ARN: ${escapeHtml(i.task_arn)}<br/>
                Exit Code: ${fmt(i.exit_code)}<br/>
                Last Status: ${escapeHtml(i.task_last_status || "-")}
              </p>
            </div>
            `
                : ""
            }

            <div class="box">
              <h4>DynamoDB Record</h4>
              <p>
                Service: <b>${escapeHtml(i.service)}</b><br/>
                Detection Time (SK): <b>${escapeHtml(i.failure_time)}</b>
              </p>
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

  /* ---------------- HELPERS (UNCHANGED) ---------------- */

  function humanize(secs) {
    if (secs == null) return "—";
    secs = Number(secs);
    if (secs < 60) return `${secs}s`;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  }

  function formatTime(t) {
    if (!t) return "—";
    try {
      return new Date(t).toISOString().replace("T", " ").replace("Z", " UTC");
    } catch {
      return t;
    }
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

  function fmt(v) {
    return v == null ? "-" : v;
  }
})();
