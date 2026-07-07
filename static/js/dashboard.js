/**
 * WattWise AI v2 — Dashboard JavaScript
 * Renders Monthly Trend, Energy Distribution, Hourly charts.
 * Handles AI Insights refresh and Quick Investigate modal.
 */

document.addEventListener("DOMContentLoaded", () => {
  if (typeof ANALYSIS === "undefined") return;
  renderMonthlyTrendChart();
  renderDistributionChart();
  renderHourlyChart();
  initInsightsRefresh();
  initQuickInvestigate();
});

/* ---- Monthly Trend ---- */
function renderMonthlyTrendChart() {
  const trend  = ANALYSIS.monthly_trend || [];
  const labels = trend.map(t => t.month);
  const values = trend.map(t => t.kwh);
  createChart("monthlyTrendChart", "line", {
    labels,
    datasets: [{
      label: "kWh",
      data: values,
      borderColor: "#0f62fe",                   /* IBM Blue */
      backgroundColor: "rgba(15,98,254,0.10)",
      tension: 0.4,
      fill: true,
      pointBackgroundColor: "#0f62fe",
      pointRadius: 4,
      pointHoverRadius: 6,
    }],
  }, {
    plugins: { legend: { display: false } },
    scales: { y: { title: { display: true, text: "kWh" } } },
  });
}

/* ---- Distribution Doughnut ---- */
function renderDistributionChart() {
  const apps   = (ANALYSIS.appliances || []).slice(0, 8);
  const labels = apps.map(a => a.appliance);
  const values = apps.map(a => a.monthly_kwh);
  createChart("distributionChart", "doughnut", {
    labels,
    datasets: [{ data: values, backgroundColor: CHART_COLORS, borderWidth: 1 }],
  }, {
    plugins: {
      legend: {
        position: "right",
        labels: { font: { size: 11 }, padding: 10 },
      },
    },
    cutout: "58%",
  });
}

/* ---- Hourly Profile ---- */
function renderHourlyChart() {
  const hourly = ANALYSIS.hourly_usage || {};
  const hours  = Array.from({ length: 24 }, (_, i) => i);
  const labels = hours.map(h => {
    const s = h < 12 ? "AM" : "PM";
    const d = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${d}${s}`;
  });
  const values = hours.map(h => hourly[h] || 0);
  const bgColors = values.map(v =>
    v >= 2.0 ? "rgba(218,30,40,0.7)"   /* IBM Red — peak */
    : v >= 1.4 ? "rgba(241,194,27,0.7)" /* IBM Yellow — high */
    : "rgba(15,98,254,0.5)"             /* IBM Blue — normal */
  );
  createChart("hourlyChart", "bar", {
    labels,
    datasets: [{ label: "kWh", data: values, backgroundColor: bgColors, borderRadius: 4 }],
  }, {
    plugins: { legend: { display: false } },
    scales: { y: { title: { display: true, text: "kWh" } } },
  });
}

/* ---- AI Insights Refresh ---- */
function initInsightsRefresh() {
  const btn = document.getElementById("refreshInsightsBtn");
  const box = document.getElementById("aiInsightsBox");
  if (!btn || !box) return;

  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Generating…`;
    box.innerHTML = `<div class="text-center py-3">
      <div class="typing-indicator"><span></span><span></span><span></span></div>
      <div class="text-muted small mt-2">Agent Orchestrator analysing…</div>
    </div>`;
    try {
      const res = await postJson("/api/quick-insights");
      if (res.status === "ok") {
        box.innerHTML = `<div class="ai-insight-text">${nl2br(res.insights)}</div>`;
      } else {
        box.innerHTML = `<div class="alert alert-warning mb-0 small">${res.message}</div>`;
      }
    } catch (e) {
      box.innerHTML = `<div class="alert alert-danger mb-0 small">Network error: ${e.message}</div>`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<i class="bi bi-stars me-1"></i>AI Insights`;
    }
  });
}

/* ---- Quick Investigate Modal ---- */
function initQuickInvestigate() {
  const btn    = document.getElementById("quickInvestigateBtn");
  const modal  = document.getElementById("investigateModal");
  const runBtn = document.getElementById("runInvestigateBtn");
  if (!btn || !modal) return;

  const bsModal = new bootstrap.Modal(modal);
  btn.addEventListener("click", () => bsModal.show());

  // Wire up investigation preset buttons inside the modal
  modal.querySelectorAll(".investigate-preset").forEach(p => {
    p.addEventListener("click", () => {
      const qInput = document.getElementById("investigateQuestion");
      if (qInput) qInput.value = p.dataset.q;
    });
  });

  runBtn?.addEventListener("click", async () => {
    const question = document.getElementById("investigateQuestion")?.value.trim();
    if (!question) {
      document.getElementById("investigateQuestion")?.focus();
      return;
    }

    const progress  = document.getElementById("investigateProgress");
    const result    = document.getElementById("investigateResult");
    const phaseText = document.getElementById("investigatePhaseText");

    runBtn.disabled  = true;
    runBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span>Investigating…`;
    progress?.classList.remove("d-none");
    result?.classList.add("d-none");

    const cancelPhase = startLoadingAnimation("investigatePhaseText", "investigate");

    try {
      const res = await postJson("/api/investigate", { question });
      progress?.classList.add("d-none");
      cancelPhase();

      if (res.status === "ok" && res.report) {
        const r = res.report;
        const confColor = r.confidence_level === "High" ? "success"
          : r.confidence_level === "Medium" ? "warning" : "secondary";

        result.innerHTML = `
          <div class="alert alert-success d-flex align-items-center gap-2 mb-3">
            <i class="bi bi-check-circle-fill" aria-hidden="true"></i>
            <div>
              <strong>Case ${r.case_id}</strong> created —
              <span class="badge bg-${confColor} ms-1">${r.confidence_level} confidence
              (${Math.round(r.confidence_score * 100)}%)</span>
            </div>
          </div>
          <p class="small text-muted mb-2">${r.investigation_summary}</p>
          <p class="small mb-3"><strong>Primary Cause:</strong> ${r.primary_cause}</p>
          <a href="/reports/${r.case_id}" class="btn btn-sm btn-primary" target="_blank">
            <i class="bi bi-eye me-1" aria-hidden="true"></i>View Full Report
          </a>`;
        result.classList.remove("d-none");
        showToast("Investigation report generated.", "success");
      } else {
        result.innerHTML = `
          <div class="alert alert-danger d-flex align-items-center gap-2 mb-0">
            <i class="bi bi-exclamation-octagon-fill" aria-hidden="true"></i>
            <span>${res.message || "Investigation failed. Please try again."}</span>
          </div>`;
        result.classList.remove("d-none");
        showToast(res.message || "Investigation failed.", "danger");
      }
    } catch (_err) {
      progress?.classList.add("d-none");
      cancelPhase();
      result.innerHTML = `
        <div class="alert alert-danger d-flex align-items-center gap-2 mb-0">
          <i class="bi bi-wifi-off" aria-hidden="true"></i>
          <span>Network error. Please check your connection and try again.</span>
        </div>`;
      result.classList.remove("d-none");
      showToast("Network error during investigation.", "danger");
    } finally {
      runBtn.disabled  = false;
      runBtn.innerHTML = `<i class="bi bi-search me-1" aria-hidden="true"></i>Investigate`;
    }
  });
}
