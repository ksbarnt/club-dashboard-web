import * as activeTeams from "./active-teams.js";
import * as worldSkills from "./world-skills.js";
import * as awards from "./awards.js";

const VIEWS = {
  "active-teams": activeTeams,
  "world-skills": worldSkills,
  awards,
};

let currentView = null;
let refreshTimer = null;

function showSection(viewName) {
  document.querySelectorAll("[data-view-section]").forEach((section) => {
    section.classList.toggle("d-none", section.dataset.viewSection !== viewName);
  });
  document.querySelectorAll("[data-view-nav]").forEach((navBtn) => {
    navBtn.classList.toggle("active", navBtn.dataset.viewNav === viewName);
  });
}

export async function activate(viewName) {
  const module = VIEWS[viewName];
  if (!module) return;

  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }

  currentView = viewName;
  showSection(viewName);
  await module.load();

  if (module.REFRESH_MS) {
    refreshTimer = setInterval(() => {
      if (currentView === viewName) module.load();
    }, module.REFRESH_MS);
  }
}

export function init() {
  document.querySelectorAll("[data-view-nav]").forEach((navBtn) => {
    navBtn.addEventListener("click", (event) => {
      event.preventDefault();
      activate(navBtn.dataset.viewNav);
    });
  });
  activate("active-teams");
}
