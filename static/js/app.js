/**
 * WattWise AI v3.0 — Core Application JavaScript
 * ================================================
 * Shared infrastructure for every page:
 *  - Sidebar toggle + mobile overlay + keyboard navigation
 *  - Dark mode with localStorage persistence
 *  - AI status polling
 *  - Demo mode badge display
 *  - Toast notification system
 *  - Shared fetch helpers (postJson)
 *  - Chart.js factory with IBM theme
 *  - Professional loading state manager
 */

// ─────────────────────────────────────────────────────────────────────────────
// Boot — runs after DOM is ready
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  initDarkMode();
  checkAiStatus();
  initDemoModeBadge();
});

// ─────────────────────────────────────────────────────────────────────────────
// Sidebar (toggle + mobile overlay + keyboard close)
// ─────────────────────────────────────────────────────────────────────────────

function initSidebar() {
  const btn     = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("mobileOverlay");

  if (!btn || !sidebar) return;

  /** Toggle sidebar state based on viewport size. */
  function toggle() {
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
      const open = sidebar.classList.toggle("mobile-open");
      overlay?.classList.toggle("active", open);
      overlay?.setAttribute("aria-hidden", String(!open));
      btn.setAttribute("aria-expanded", String(open));
    } else {
      const collapsed = sidebar.classList.toggle("collapsed");
      btn.setAttribute("aria-expanded", String(!collapsed));
    }
  }

  btn.addEventListener("click", toggle);

  // Close sidebar when mobile overlay is clicked
  overlay?.addEventListener("click", () => {
    sidebar.classList.remove("mobile-open");
    overlay.classList.remove("active");
    overlay.setAttribute("aria-hidden", "true");
    btn.setAttribute("aria-expanded", "false");
  });

  // Close sidebar on Escape key (mobile)
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && window.innerWidth <= 768) {
      sidebar.classList.remove("mobile-open");
      overlay?.classList.remove("active");
      overlay?.setAttribute("aria-hidden", "true");
      btn.setAttribute("aria-expanded", "false");
      btn.focus();
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Dark Mode
// ─────────────────────────────────────────────────────────────────────────────

function initDarkMode() {
  const btn  = document.getElementById("darkModeToggle");
  const icon = document.getElementById("darkModeIcon");
  const html = document.documentElement;

  // Restore persisted preference or respect OS preference
  const saved = localStorage.getItem("ww-theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(saved);

  btn?.addEventListener("click", () => {
    const current = html.getAttribute("data-bs-theme") || "light";
    const next    = current === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("ww-theme", next);
  });

  /** Apply theme and sync icon + Chart.js defaults. */
  function applyTheme(theme) {
    html.setAttribute("data-bs-theme", theme);
    if (icon) {
      icon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill";
    }
    if (btn) {
      btn.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} mode`);
    }
    // Keep Chart.js defaults consistent with the active theme
    if (window.Chart) {
      const isDark = theme === "dark";
      Chart.defaults.color       = isDark ? "#a8a8a8" : "#6f6f6f";
      Chart.defaults.borderColor = isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.05)";
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AI Status Polling
// ─────────────────────────────────────────────────────────────────────────────

async function checkAiStatus() {
  const dot  = document.getElementById("ai-status-dot");
  const text = document.getElementById("ai-status-text");
  if (!dot || !text) return;

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 5000);
    const r = await fetch("/api/analysis-data", { signal: ctrl.signal });
    clearTimeout(timer);

    if (r.ok) {
      dot.className   = "status-dot status-online";
      dot.setAttribute("aria-label", "AI status: ready");
      text.textContent = "System Ready";
    } else {
      throw new Error("non-ok");
    }
  } catch (_err) {
    dot.className   = "status-dot status-offline";
    dot.setAttribute("aria-label", "AI status: offline");
    text.textContent = "Connecting…";
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Demo Mode Badge
// Show the "Demo" badge in the topbar when no real CSV is loaded.
// ─────────────────────────────────────────────────────────────────────────────

function initDemoModeBadge() {
  const badge = document.getElementById("demoModeBadge");
  if (!badge) return;

  // Fetch current analysis source; show badge only when source == "demo"
  fetch("/api/analysis-data")
    .then(r => r.json())
    .then(data => {
      const source = data?.analysis?.data_source;
      if (source === "demo" || !source) {
        badge.classList.remove("d-none");
      } else {
        badge.classList.add("d-none");
      }
    })
    .catch(() => { /* silently ignore */ });
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast Notification System
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Show a Bootstrap toast notification.
 * @param {string} message  - Message text (HTML safe — will be escaped if needed)
 * @param {"success"|"danger"|"warning"|"info"} type - Bootstrap colour variant
 * @param {number} delay    - Auto-dismiss after N ms (0 = persistent until closed)
 */
function showToast(message, type = "info", delay = 4500) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const iconMap = {
    success: "bi-check-circle-fill",
    danger:  "bi-exclamation-octagon-fill",
    warning: "bi-exclamation-triangle-fill",
    info:    "bi-info-circle-fill",
  };

  const el = document.createElement("div");
  el.className  = `toast align-items-center text-bg-${type} border-0 shadow-sm`;
  el.role       = "alert";
  el.setAttribute("aria-live", "assertive");
  el.setAttribute("aria-atomic", "true");
  el.innerHTML  = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center gap-2">
        <i class="bi ${iconMap[type] || "bi-info-circle-fill"} flex-shrink-0" aria-hidden="true"></i>
        <span>${message}</span>
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto"
              data-bs-dismiss="toast" aria-label="Dismiss notification"></button>
    </div>`;
  container.appendChild(el);

  const toast = new bootstrap.Toast(el, {
    delay:    delay || 999999,
    autohide: delay > 0,
  });
  toast.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

// ─────────────────────────────────────────────────────────────────────────────
// Professional Loading State Manager
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Phase messages displayed during each AI operation.
 * Reflects the actual agentic pipeline stages.
 */
const LOADING_MESSAGES = {
  investigate: [
    "Analysing energy data…",
    "Collecting evidence items…",
    "Investigating possible causes…",
    "Ranking evidence by severity…",
    "Building AI investigation context…",
    "Consulting IBM watsonx.ai…",
    "Preparing investigation report…",
  ],
  recommend: [
    "Analysing consumption patterns…",
    "Identifying saving opportunities…",
    "Building recommendation context…",
    "Generating AI recommendations…",
    "Calculating estimated savings…",
    "Finalising action plan…",
  ],
  scenario: [
    "Parsing scenario query…",
    "Running energy simulation…",
    "Calculating impact figures…",
    "Consulting AI for reasoning…",
    "Preparing scenario results…",
  ],
  insights: [
    "Reviewing your energy profile…",
    "Generating AI quick insights…",
    "Almost done…",
  ],
  upload: [
    "Reading your data file…",
    "Detecting column schema…",
    "Calculating consumption totals…",
    "Enriching with AI analysis…",
    "Finalising results…",
  ],
  chat: [
    "Detecting intent…",
    "Building evidence context…",
    "Consulting IBM watsonx.ai…",
    "Generating response…",
  ],
  default: ["Processing…", "Please wait…", "Almost ready…"],
};

/**
 * Animate a text element through loading messages at the given interval.
 * Returns a cancel function — always call it when the operation finishes.
 *
 * @param {string} elementId - ID of the element to animate
 * @param {string} type      - Key from LOADING_MESSAGES
 * @param {number} interval  - Milliseconds between message changes
 * @returns {function} cancel — call to stop the animation
 */
function startLoadingAnimation(elementId, type = "default", interval = 1800) {
  const el = document.getElementById(elementId);
  if (!el) return () => {};

  const messages = LOADING_MESSAGES[type] || LOADING_MESSAGES.default;
  let idx = 0;

  el.textContent = messages[0];
  const timer = setInterval(() => {
    idx = (idx + 1) % messages.length;
    el.textContent = messages[idx];
  }, interval);

  return () => {
    clearInterval(timer);
    el.textContent = "";
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// HTTP Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * POST JSON to a URL and return the parsed response object.
 * Always resolves; inspect res.status === "ok" for success.
 *
 * @param {string} url  - API endpoint path
 * @param {object} data - Request body (will be JSON-serialised)
 * @returns {Promise<object>} Parsed JSON response
 */
async function postJson(url, data = {}) {
  try {
    const r = await fetch(url, {
      method:  "POST",
      headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
      body:    JSON.stringify(data),
    });
    // Handle non-JSON responses (e.g. 500 HTML error pages)
    const contentType = r.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      return { status: "error", message: `Server error (${r.status}). Please try again.` };
    }
    return await r.json();
  } catch (err) {
    if (err.name === "AbortError") {
      return { status: "error", message: "Request timed out. Please try again." };
    }
    return { status: "error", message: "Network error. Please check your connection." };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Inline Alert Helper
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Render a dismissible Bootstrap alert inside a container element.
 *
 * @param {string} containerId - ID of the container element
 * @param {string} message     - Alert message text
 * @param {"success"|"danger"|"warning"|"info"} type - Bootstrap colour variant
 */
function showAlert(containerId, message, type = "info") {
  const el = document.getElementById(containerId);
  if (!el) return;

  const icons = {
    success: "bi-check-circle-fill",
    danger:  "bi-exclamation-octagon-fill",
    warning: "bi-exclamation-triangle-fill",
    info:    "bi-info-circle-fill",
  };

  el.innerHTML = `
    <div class="alert alert-${type} alert-dismissible fade show d-flex align-items-center gap-2 mb-0 mt-2" role="alert">
      <i class="bi ${icons[type] || "bi-info-circle-fill"} flex-shrink-0" aria-hidden="true"></i>
      <span>${message}</span>
      <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert" aria-label="Dismiss"></button>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Text / Format Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convert an AI-generated text string to safe HTML for display in chat bubbles.
 *
 * Mirrors the server-side nl2br Jinja2 filter so that dynamically injected
 * responses (JS-rendered) look identical to server-rendered responses.
 *
 * Supported conversions (applied in order):
 *   ## Heading   →  <h6 class="ai-heading">
 *   **text**     →  <strong>text</strong>
 *   *text*       →  <em>text</em>
 *   `code`       →  <code>code</code>
 *   - item       →  • item  (soft bullet span)
 *   1. item      →  styled numbered item
 *   blank line   →  paragraph break (<br /><br />)
 *   \n           →  <br />
 *
 * NOTE: Raw HTML is escaped first, so this function is XSS-safe.
 */
function nl2br(text) {
  if (!text) return "";

  // 1. Escape HTML entities first to prevent injection
  let s = String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  // 2. Headings: ##/### Title → compact <h6>
  s = s.replace(/^#{1,3}\s+(.+)$/gm, '<h6 class="ai-heading mt-2 mb-1">$1</h6>');

  // 3. Bold: **text** → <strong>
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // 4. Italic: *text* → <em>  (skip lone asterisks, don't re-match bold)
  s = s.replace(/\*([^*\n]+?)\*/g, "<em>$1</em>");

  // 5. Inline code: `code` → <code>
  s = s.replace(/`([^`\n]+?)`/g, "<code>$1</code>");

  // 6. Soft bullets: "- item" or "* item" at line start → bullet span
  s = s.replace(/^[-]\s+(.+)$/gm, '<span class="ai-bullet">\u2022 $1</span>');

  // 7. Numbered list items: "1. item" → styled span
  s = s.replace(/^(\d+)\.\s+(.+)$/gm, '<span class="ai-bullet"><strong>$1.</strong> $2</span>');

  // 8. Blank lines → paragraph break
  s = s.replace(/\n\n/g, "<br /><br />\n");

  // 9. Remaining single newlines → <br />
  s = s.replace(/\n/g, "<br />\n");

  return s;
}

/** Format a number as a kWh string. */
function fmtKwh(v) {
  return parseFloat(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " kWh";
}

/** Format a number as a currency string. */
function fmtCost(v, sym = "$") {
  return sym + parseFloat(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─────────────────────────────────────────────────────────────────────────────
// Chart.js Factory — IBM colour palette
// ─────────────────────────────────────────────────────────────────────────────

/** IBM Design Language–inspired chart colours. */
const CHART_COLORS = [
  "#0f62fe",   // IBM Blue
  "#198038",   // IBM Green
  "#f1c21b",   // IBM Yellow
  "#da1e28",   // IBM Red
  "#6929c4",   // IBM Purple
  "#007d79",   // IBM Teal
  "#fa4d56",   // IBM Red 40
  "#0072c3",   // IBM Cyan
  "#8a3ffc",   // IBM Purple 50
  "#42be65",   // IBM Green 40
];

/**
 * Create or replace a Chart.js chart on a canvas element.
 *
 * @param {string} canvasId - ID of the <canvas> element
 * @param {string} type     - Chart type: "bar" | "line" | "doughnut" | "pie"
 * @param {object} data     - Chart.js data object { labels, datasets }
 * @param {object} opts     - Additional Chart.js options (deep-merged with defaults)
 * @returns {Chart|null}    - Chart instance or null if canvas not found
 */
function createChart(canvasId, type, data, opts = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  // Destroy any existing instance to prevent canvas re-use errors
  if (canvas._chartInstance) {
    canvas._chartInstance.destroy();
    canvas._chartInstance = null;
  }

  const isDark    = document.documentElement.getAttribute("data-bs-theme") === "dark";
  const gridColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)";
  const textColor = isDark ? "#a8a8a8" : "#6f6f6f";

  const defaults = {
    responsive:          true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: {
          color:   textColor,
          font:    { size: 11, family: "'IBM Plex Sans', sans-serif" },
          padding: 14,
          boxWidth: 12,
        },
      },
      tooltip: {
        mode:      "index",
        intersect: false,
        titleFont: { family: "'IBM Plex Sans', sans-serif" },
        bodyFont:  { family: "'IBM Plex Sans', sans-serif" },
      },
    },
    scales: (type !== "doughnut" && type !== "pie") ? {
      x: {
        grid:  { color: gridColor },
        ticks: { color: textColor, font: { size: 11 } },
      },
      y: {
        grid:       { color: gridColor },
        ticks:      { color: textColor, font: { size: 11 } },
        beginAtZero: true,
      },
    } : undefined,
  };

  const chart = new Chart(canvas, {
    type,
    data,
    options: _mergeDeep(defaults, opts),
  });
  canvas._chartInstance = chart;
  return chart;
}

// ─────────────────────────────────────────────────────────────────────────────
// Deep-merge utility (used by createChart)
// ─────────────────────────────────────────────────────────────────────────────

function _mergeDeep(target, source) {
  const out = Object.assign({}, target);
  if (_isObject(target) && _isObject(source)) {
    for (const key of Object.keys(source)) {
      if (_isObject(source[key])) {
        out[key] = key in target ? _mergeDeep(target[key], source[key]) : source[key];
      } else {
        out[key] = source[key];
      }
    }
  }
  return out;
}

function _isObject(item) {
  return item !== null && typeof item === "object" && !Array.isArray(item);
}
