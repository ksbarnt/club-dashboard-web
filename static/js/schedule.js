import { apiGet } from "./api.js";
import { showError, showWarnings, clearAlerts, el } from "./ui.js";
import { programBadgeClass, programTableClass } from "./theme.js";

export const REFRESH_MS = 24 * 60 * 60 * 1000;

function formatDateRange(start, end) {
  if (!start) return "";
  const opts = { month: "short", day: "numeric", year: "numeric" };
  const startDate = new Date(start);
  const startStr = startDate.toLocaleDateString(undefined, opts);
  if (!end) return startStr;

  const endDate = new Date(end);
  if (endDate.toDateString() === startDate.toDateString()) return startStr;

  const sameYear = endDate.getFullYear() === startDate.getFullYear();
  const endStr = endDate.toLocaleDateString(
    undefined,
    sameYear ? { month: "short", day: "numeric" } : opts
  );
  return `${startStr} – ${endStr}`;
}

function renderProgram(container, events, programAbbr, label) {
  container.innerHTML = "";
  if (!events || events.length === 0) return;

  container.appendChild(el("h5", { className: "mt-3", text: label }));

  events.forEach((group) => {
    const card = el("div", { className: "mb-4" });
    card.appendChild(
      el("h6", { className: "mb-1" }, [
        el("span", { text: group.eventName || "" }),
        el("span", {
          className: "text-muted ms-2 small fw-normal",
          text: formatDateRange(group.start, group.end),
        }),
      ])
    );

    const table = el("table", { className: "table table-bordered table-sm align-middle mb-0" });
    const thead = el("thead", { className: programTableClass(programAbbr) }, [
      el("tr", {}, [el("th", { text: "Team" }), el("th", { text: "Name" })]),
    ]);
    const tbody = el("tbody");
    group.teams.forEach((team) => {
      const badge = el("span", {
        className: `badge ${programBadgeClass(programAbbr)}`,
        text: team.number,
      });
      tbody.appendChild(
        el("tr", {}, [el("td", {}, badge), el("td", { text: team.name || "" })])
      );
    });
    table.appendChild(thead);
    table.appendChild(tbody);
    card.appendChild(table);
    container.appendChild(card);
  });
}

export async function load() {
  const alerts = document.getElementById("schedule-alerts");
  const iqContainer = document.getElementById("schedule-iq");
  const v5Container = document.getElementById("schedule-v5");
  const emptyMsg = document.getElementById("schedule-empty");
  const noneMsg = document.getElementById("schedule-none");

  clearAlerts(alerts);
  emptyMsg.classList.add("d-none");
  noneMsg.classList.add("d-none");

  try {
    const data = await apiGet("/api/schedule");
    if (!data.teamsConfigured) {
      iqContainer.innerHTML = "";
      v5Container.innerHTML = "";
      emptyMsg.classList.remove("d-none");
      return;
    }

    const iqEvents = data.IQ || [];
    const v5Events = data.V5 || [];
    renderProgram(iqContainer, iqEvents, "VIQRC", "VEX IQ Robotics Competition");
    renderProgram(v5Container, v5Events, "V5RC", "VEX V5 Robotics Competition");
    showWarnings(alerts, data.warnings);

    if (iqEvents.length === 0 && v5Events.length === 0) noneMsg.classList.remove("d-none");
  } catch (err) {
    showError(alerts, err.message || "Failed to load schedule.");
  }
}
