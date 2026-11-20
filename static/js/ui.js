import { programBadgeClass } from "./theme.js";

export function clearAlerts(alertContainer) {
  alertContainer.innerHTML = "";
}

export function showError(alertContainer, message) {
  const alert = document.createElement("div");
  alert.className = "alert alert-danger alert-dismissible fade show";
  alert.role = "alert";
  alert.textContent = message;
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "btn-close";
  closeBtn.setAttribute("data-bs-dismiss", "alert");
  closeBtn.setAttribute("aria-label", "Close");
  alert.appendChild(closeBtn);
  alertContainer.appendChild(alert);
}

export function showWarnings(alertContainer, warnings) {
  if (!warnings || warnings.length === 0) return;
  const alert = document.createElement("div");
  alert.className = "alert alert-warning alert-dismissible fade show small";
  alert.role = "alert";
  const list = document.createElement("ul");
  list.className = "mb-0 ps-3";
  warnings.forEach((w) => {
    const li = document.createElement("li");
    li.textContent = w;
    list.appendChild(li);
  });
  alert.appendChild(list);
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "btn-close";
  closeBtn.setAttribute("data-bs-dismiss", "alert");
  closeBtn.setAttribute("aria-label", "Close");
  alert.appendChild(closeBtn);
  alertContainer.appendChild(alert);
}

/** Event name linked to its events.vex.com page, or plain text if no SKU. */
export function eventLink(text, sku) {
  if (!sku) return el("span", { text: text || "" });
  return el("a", {
    href: `https://events.vex.com/${encodeURIComponent(sku)}.html`,
    target: "_blank",
    rel: "noopener noreferrer",
    text: text || sku,
  });
}

/** Team number badge linked to its events.vex.com team page. */
export function teamLink(number, program) {
  const className = `badge ${programBadgeClass(program)} text-decoration-none`;
  if (!number || !program) return el("span", { className, text: number || "" });
  return el("a", {
    className,
    href: `https://events.vex.com/teams/${encodeURIComponent(program)}/${encodeURIComponent(number)}`,
    target: "_blank",
    rel: "noopener noreferrer",
    text: number,
  });
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "text") {
      node.textContent = value;
    } else if (key === "html") {
      node.innerHTML = value;
    } else if (key.startsWith("data-")) {
      node.setAttribute(key, value);
    } else {
      node[key] = value;
    }
  }
  (Array.isArray(children) ? children : [children]).forEach((child) => {
    if (child == null) return;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  });
  return node;
}
