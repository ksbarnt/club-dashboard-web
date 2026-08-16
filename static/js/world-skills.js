import { apiGet } from "./api.js";
import { showError, showWarnings, clearAlerts, el } from "./ui.js";
import { programBadgeClass, programTableClass } from "./theme.js";

export const REFRESH_MS = 24 * 60 * 60 * 1000;

const GRADE_LABEL = { ES: "Elementary School", MS: "Middle School", HS: "High School" };
const PROGRAM_LABEL = { VIQRC: "VEX IQ", V5RC: "VEX V5" };

function formatRank(rank) {
  return rank == null ? "--" : String(rank);
}

function formatScore(score) {
  return score == null ? "--" : String(score);
}

function renderGroup(container, group, eventRegion) {
  const heading = el("h5", {
    className: "mt-3",
    text: `${PROGRAM_LABEL[group.program] || group.program} — ${
      GRADE_LABEL[group.grade] || group.grade
    }`,
  });

  const table = el("table", { className: "table table-bordered table-sm align-middle" });
  const thead = el("thead", { className: programTableClass(group.program) }, [
    el("tr", {}, [
      el("th", { text: "Team" }),
      el("th", { text: `${eventRegion} Rank` }),
      el("th", { text: "World Rank" }),
      el("th", { text: "Overall Score" }),
      el("th", { text: "Driver Score" }),
      el("th", { text: "Autonomous Score" }),
    ]),
  ]);
  const tbody = el("tbody");
  group.teams.forEach((team) => {
    const badge = el("span", {
      className: `badge ${programBadgeClass(group.program)}`,
      text: team.number,
    });
    tbody.appendChild(
      el("tr", {}, [
        el("td", {}, badge),
        el("td", { text: formatRank(team.regionalRank) }),
        el("td", { text: formatRank(team.worldRank) }),
        el("td", { text: formatScore(team.overallScore) }),
        el("td", { text: formatScore(team.driverScore) }),
        el("td", { text: formatScore(team.autoScore) }),
      ])
    );
  });
  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(heading);
  container.appendChild(table);
}

export async function load() {
  const alerts = document.getElementById("world-skills-alerts");
  const container = document.getElementById("world-skills-groups");
  const emptyMsg = document.getElementById("world-skills-empty");

  clearAlerts(alerts);
  container.innerHTML = "";
  emptyMsg.classList.add("d-none");

  try {
    const data = await apiGet("/api/world-skills");
    if (!data.teamsConfigured || !data.eventRegionConfigured) {
      emptyMsg.classList.remove("d-none");
      return;
    }

    if (!data.groups || data.groups.length === 0) {
      container.appendChild(
        el("p", {
          className: "text-muted",
          text: "No world skills records found for your tracked teams.",
        })
      );
      return;
    }
    data.groups.forEach((group) => renderGroup(container, group, data.eventRegion));
    showWarnings(alerts, data.warnings);
  } catch (err) {
    showError(alerts, err.message || "Failed to load world skills rankings.");
  }
}
