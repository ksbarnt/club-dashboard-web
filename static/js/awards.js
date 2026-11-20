import { apiGet } from "./api.js";
import { showError, showWarnings, clearAlerts, el, eventLink, teamLink } from "./ui.js";
import { programTableClass } from "./theme.js";
import { includes as showProgram } from "./program-filter.js";

export const REFRESH_MS = 24 * 60 * 60 * 1000;

const PROGRAM_LABEL = { VIQRC: "VEX IQ Robotics Competition", V5RC: "VEX V5 Robotics Competition" };

function renderProgramTable(container, teams, programAbbr) {
  container.appendChild(el("h5", { className: "mt-3", text: PROGRAM_LABEL[programAbbr] }));

  if (!teams || teams.length === 0) {
    container.appendChild(el("p", { className: "text-muted", text: "No awards yet." }));
    return;
  }

  const table = el("table", { className: "table table-bordered table-sm align-middle" });
  const thead = el("thead", { className: programTableClass(programAbbr) }, [
    el("tr", {}, [el("th", { text: "Team" }), el("th", { text: "Event" }), el("th", { text: "Award" })]),
  ]);
  const tbody = el("tbody");

  teams.forEach((team) => {
    const totalAwards = team.events.reduce((sum, e) => sum + e.awards.length, 0);
    let teamCellUsed = false;

    team.events.forEach((eventGroup) => {
      let cityCellUsed = false;

      eventGroup.awards.forEach((award) => {
        const row = el("tr");

        if (!teamCellUsed) {
          const badge = teamLink(team.number, programAbbr);
          row.appendChild(el("td", { rowSpan: totalAwards }, badge));
          teamCellUsed = true;
        }

        if (!cityCellUsed) {
          row.appendChild(
            el("td", { rowSpan: eventGroup.awards.length }, eventLink(eventGroup.eventLabel, eventGroup.sku))
          );
          cityCellUsed = true;
        }

        row.appendChild(el("td", { text: award.title }));
        tbody.appendChild(row);
      });
    });
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
}

export async function load() {
  const alerts = document.getElementById("awards-alerts");
  const container = document.getElementById("awards-tables");
  const emptyMsg = document.getElementById("awards-empty");

  clearAlerts(alerts);
  container.innerHTML = "";
  emptyMsg.classList.add("d-none");

  try {
    const data = await apiGet("/api/awards");
    if (!data.teamsConfigured) {
      emptyMsg.classList.remove("d-none");
      return;
    }

    if (showProgram("VIQRC")) renderProgramTable(container, data.VIQRC, "VIQRC");
    if (showProgram("V5RC")) renderProgramTable(container, data.V5RC, "V5RC");
    showWarnings(alerts, data.warnings);
  } catch (err) {
    showError(alerts, err.message || "Failed to load awards.");
  }
}
