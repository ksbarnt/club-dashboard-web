import { apiGet } from "./api.js";
import { showError, showWarnings, clearAlerts, el } from "./ui.js";
import { programBadgeClass, programTableClass } from "./theme.js";

export const REFRESH_MS = 5 * 60 * 1000;

function formatRank(rank) {
  return rank == null ? "--" : String(rank);
}

function formatScore(score, attempts) {
  if (score == null) return "-- (0/3)";
  return `${score} (${attempts ?? 0}/3)`;
}

function renderProgramTable(container, groups, programAbbr, label) {
  container.innerHTML = "";
  if (!groups || groups.length === 0) return;

  container.appendChild(el("h5", { className: "mt-3", text: label }));

  const table = el("table", { className: "table table-bordered table-sm align-middle" });
  const thead = el("thead", { className: programTableClass(programAbbr) }, [
    el("tr", {}, [
      el("th", { text: "Team" }),
      el("th", { text: "Rank" }),
      el("th", { text: "Skills Rank" }),
      el("th", { text: "Driver" }),
      el("th", { text: "Autonomous" }),
    ]),
  ]);
  const tbody = el("tbody");
  groups.forEach((group) => {
    tbody.appendChild(
      el("tr", {}, [
        el("td", {
          colSpan: 5,
          className: "table-group-header fw-semibold",
          text: group.eventName || "",
        }),
      ])
    );
    group.teams.forEach((team) => {
      const badge = el("span", {
        className: `badge ${programBadgeClass(programAbbr)}`,
        text: team.number,
      });
      tbody.appendChild(
        el("tr", {}, [
          el("td", {}, badge),
          el("td", { text: formatRank(team.eventRank) }),
          el("td", { text: formatRank(team.skillsRank) }),
          el("td", { text: formatScore(team.driverScore, team.driverAttempts) }),
          el("td", { text: formatScore(team.autoScore, team.autoAttempts) }),
        ])
      );
    });
  });
  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
}

export async function load() {
  const alerts = document.getElementById("active-teams-alerts");
  const iqContainer = document.getElementById("active-teams-iq");
  const v5Container = document.getElementById("active-teams-v5");
  const emptyMsg = document.getElementById("active-teams-empty");
  const noneToday = document.getElementById("active-teams-none-today");

  clearAlerts(alerts);
  noneToday.classList.add("d-none");
  emptyMsg.classList.add("d-none");

  try {
    const data = await apiGet("/api/active-teams");
    if (!data.teamsConfigured) {
      iqContainer.innerHTML = "";
      v5Container.innerHTML = "";
      emptyMsg.classList.remove("d-none");
      return;
    }

    renderProgramTable(iqContainer, data.IQ, "VIQRC", "VEX IQ Robotics Competition");
    renderProgramTable(v5Container, data.V5, "V5RC", "VEX V5 Robotics Competition");
    showWarnings(alerts, data.warnings);

    const hasAny = (data.IQ && data.IQ.length) || (data.V5 && data.V5.length);
    if (!hasAny) noneToday.classList.remove("d-none");
  } catch (err) {
    showError(alerts, err.message || "Failed to load active teams.");
  }
}
