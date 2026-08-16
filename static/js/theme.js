export const PROGRAM_BADGE_CLASS = {
  VIQRC: "bg-primary",
  V5RC: "bg-danger",
};

export const PROGRAM_TABLE_CLASS = {
  VIQRC: "table-primary",
  V5RC: "table-danger",
};

export function programBadgeClass(program) {
  return PROGRAM_BADGE_CLASS[program] || "bg-secondary";
}

export function programTableClass(program) {
  return PROGRAM_TABLE_CLASS[program] || "";
}
