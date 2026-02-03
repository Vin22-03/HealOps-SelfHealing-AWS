async function load() {
  const summary = await fetch("/api/summary").then(r => r.json());
  const incidents = await fetch("/api/incidents").then(r => r.json());

  document.getElementById("total").textContent = summary.total_incidents;
  document.getElementById("open").textContent = summary.open_incidents;
  document.getElementById("resolved").textContent = summary.resolved_incidents;
  document.getElementById("mttr").textContent = summary.avg_mttr_seconds ?? "—";
  document.getElementById("generated").textContent = "Updated: " + summary.generated_at;

  document.getElementById("last").textContent = summary.last_incident
    ? JSON.stringify(summary.last_incident, null, 2)
    : "No incidents yet.";

  const rows = incidents.incidents.slice(0, 8);
  const tbody = document.getElementById("rows");
  tbody.innerHTML = "";

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">No incidents yet.</td></tr>`;
    return;
  }

  for (const i of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i.id}</td>
      <td>${i.title}</td>
      <td>${i.severity}</td>
      <td>${i.status}</td>
      <td>${i.mttr_seconds ?? "—"}</td>
      <td>${i.detection ?? "—"}</td>
      <td>${i.healing_action ?? "—"}</td>
    `;
    tbody.appendChild(tr);
  }
}

// refresh every 3 seconds (live feel)
load();
setInterval(load, 3000);
