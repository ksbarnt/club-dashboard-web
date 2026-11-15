// Global program filter: "both" (default), "VIQRC" (IQ only), or "V5RC" (V5 only).
//
// Display-only: views always fetch the full IQ + V5 payload and filter at
// render time. Never pass this value to the server -- the background
// refresh from events.vex.com (app/services/scheduler.py) must always
// fetch both programs so the shared cache stays complete.
const STORAGE_KEY = "programFilter";
const VALUES = ["both", "VIQRC", "V5RC"];

function readStored() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return VALUES.includes(value) ? value : "both";
  } catch {
    return "both";
  }
}

let current = readStored();

/** True if data for the given program ("VIQRC" or "V5RC") should be shown. */
export function includes(programAbbr) {
  return current === "both" || current === programAbbr;
}

export function init(onChange) {
  const inputs = document.querySelectorAll("input[name='program-filter']");
  inputs.forEach((input) => {
    input.checked = input.value === current;
    input.addEventListener("change", () => {
      if (!input.checked) return;
      current = input.value;
      try {
        localStorage.setItem(STORAGE_KEY, current);
      } catch {
        // Storage unavailable; filter still applies for this session.
      }
      onChange(current);
    });
  });
}
