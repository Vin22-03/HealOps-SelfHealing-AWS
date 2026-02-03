async function loadData() {
  const res = await fetch("/api/incidents/");
  const data = await res.json();

  document.getElementById("mttr").innerText =
    data.mttr ? data.mttr + " sec" : "—";

  const tbody = document.getElementById("incidents");
  tbody.innerHTML = "";

  data.incidents.forEach(i => {
    const mttr = i.resolved_at
      ? Math.round((new Date(i.resolved_at) - new Date(i.created_at)) / 1000) + "s"
      : "-";

    tbody.innerHTML += `
      <tr class="${i.severity}">
        <td>${i.id}</td>
        <td>${i.title}</td>
        <td>${i.severity}</td>
        <td>${i.status}</td>
        <td>${mttr}</td>
      </tr>
    `;
  });
}

async function breakIt(sev) {
  await fetch(`/api/incidents/break/${sev}`, { method: "POST" });
  loadData();
}

async function fix() {
  await fetch("/api/incidents/resolve", { method: "POST" });
  loadData();
}

setInterval(loadData, 2000);
loadData();
