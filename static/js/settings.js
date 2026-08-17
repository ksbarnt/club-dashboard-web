import { EVENT_REGIONS } from "./regions.js";

const GRADE_OPTIONS = {
  VIQRC: [
    { value: "ES", label: "Elementary School (ES)" },
    { value: "MS", label: "Middle School (MS)" },
  ],
  V5RC: [
    { value: "MS", label: "Middle School (MS)" },
    { value: "HS", label: "High School (HS)" },
  ],
};

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "text") node.textContent = value;
    else if (key.startsWith("data-")) node.setAttribute(key, value);
    else node[key] = value;
  }
  (Array.isArray(children) ? children : [children]).forEach((child) => {
    if (child == null) return;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  });
  return node;
}

function gradeOptionsFor(program) {
  return GRADE_OPTIONS[program] || [];
}

function refreshGradeOptions(gradeSelect, programSelect, selectedGrade) {
  gradeSelect.innerHTML = "";
  const options = gradeOptionsFor(programSelect.value);
  gradeSelect.disabled = options.length === 0;
  gradeSelect.appendChild(el("option", { value: "", text: options.length ? "Grade..." : "Select program first" }));
  options.forEach((opt) => {
    const optionEl = el("option", { value: opt.value, text: opt.label });
    if (selectedGrade && opt.value === selectedGrade) optionEl.selected = true;
    gradeSelect.appendChild(optionEl);
  });
}

function wireTeamRow(row) {
  const programSelect = row.querySelector('[data-role="program"]');
  const gradeSelect = row.querySelector('[data-role="grade"]');
  const removeBtn = row.querySelector(".remove-team-btn");

  refreshGradeOptions(gradeSelect, programSelect, gradeSelect.dataset.selected || "");
  programSelect.addEventListener("change", () => refreshGradeOptions(gradeSelect, programSelect));
  removeBtn.addEventListener("click", () => row.remove());
}

function buildTeamRow() {
  const numberInput = el("input", { type: "text", className: "form-control", name: "team_number", placeholder: "Team #" });
  const programSelect = el("select", { className: "form-select", name: "team_program" }, [
    el("option", { value: "", text: "Program..." }),
    el("option", { value: "VIQRC", text: "VIQRC" }),
    el("option", { value: "V5RC", text: "V5RC" }),
  ]);
  programSelect.dataset.role = "program";
  const gradeSelect = el("select", { className: "form-select", name: "team_grade" });
  gradeSelect.dataset.role = "grade";
  const removeBtn = el("button", { type: "button", className: "btn btn-outline-danger btn-sm remove-team-btn", text: "Remove" });

  const row = el("div", { className: "row g-2 align-items-center mb-2 team-row" }, [
    el("div", { className: "col-4" }, numberInput),
    el("div", { className: "col-3" }, programSelect),
    el("div", { className: "col-3" }, gradeSelect),
    el("div", { className: "col-2" }, removeBtn),
  ]);
  wireTeamRow(row);
  return row;
}

async function populateSeasonOptions(selectEl, program, selectedId, token) {
  selectEl.innerHTML = "";
  selectEl.appendChild(el("option", { value: "", text: "Loading..." }));
  try {
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const resp = await fetch(`/api/seasons?program=${encodeURIComponent(program)}`, { headers });
    if (!resp.ok) throw new Error("request failed");
    const seasons = await resp.json();
    selectEl.innerHTML = "";
    selectEl.appendChild(el("option", { value: "", text: "Select a season..." }));
    seasons.forEach((season) => {
      const opt = el("option", { value: String(season.id), text: season.name });
      if (selectedId != null && String(season.id) === String(selectedId)) opt.selected = true;
      selectEl.appendChild(opt);
    });
  } catch (err) {
    selectEl.innerHTML = "";
    selectEl.appendChild(el("option", { value: "", text: "Enter an API token and save to load seasons" }));
  }
}

function populateRegionOptions(selectEl, selectedRegion) {
  selectEl.innerHTML = "";
  selectEl.appendChild(el("option", { value: "", text: "Select a region..." }));
  EVENT_REGIONS.forEach((region) => {
    const opt = el("option", { value: region, text: region });
    if (region === selectedRegion) opt.selected = true;
    selectEl.appendChild(opt);
  });
}

const REFRESH_SECTION_LABEL = { active_teams: "Active Teams", world_skills: "World Skills", awards: "Awards" };

function describeRefreshResult(result) {
  if (result.status === "ok") return `updated ${new Date(result.updatedAt).toLocaleString()}`;
  if (result.status === "skipped") return `skipped (${result.message})`;
  return `error (${result.message})`;
}

async function runRefreshNow(button, status, resultsList) {
  button.disabled = true;
  status.textContent = "Refreshing...";
  resultsList.innerHTML = "";
  try {
    const resp = await fetch("/settings/refresh", { method: "POST" });
    const data = await resp.json();
    status.textContent = "Done.";
    Object.entries(data).forEach(([key, result]) => {
      const label = REFRESH_SECTION_LABEL[key] || key;
      resultsList.appendChild(el("li", { text: `${label}: ${describeRefreshResult(result)}` }));
    });
  } catch (err) {
    status.textContent = "Failed to refresh.";
  } finally {
    button.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const initial = window.__SETTINGS__ || { eventRegion: "", viqrcSeason: null, v5rcSeason: null };
  const tokenInput = document.getElementById("api_token");
  const regionSelect = document.getElementById("event_region");
  const viqrcSeasonSelect = document.getElementById("viqrc_season");
  const v5rcSeasonSelect = document.getElementById("v5rc_season");
  const teamsList = document.getElementById("settings-teams-list");
  const addTeamBtn = document.getElementById("settings-add-team");
  const refreshBtn = document.getElementById("refresh-now-btn");
  const refreshStatus = document.getElementById("refresh-now-status");
  const refreshResults = document.getElementById("refresh-now-results");

  populateRegionOptions(regionSelect, initial.eventRegion);
  teamsList.querySelectorAll(".team-row").forEach(wireTeamRow);
  addTeamBtn.addEventListener("click", () => teamsList.appendChild(buildTeamRow()));

  populateSeasonOptions(viqrcSeasonSelect, "VIQRC", initial.viqrcSeason, tokenInput.value);
  populateSeasonOptions(v5rcSeasonSelect, "V5RC", initial.v5rcSeason, tokenInput.value);

  refreshBtn.addEventListener("click", () => runRefreshNow(refreshBtn, refreshStatus, refreshResults));
});
