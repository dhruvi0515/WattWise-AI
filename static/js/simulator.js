/**
 * WattWise AI v2.1 — Scenario Simulator JavaScript
 * Uses loading state animations and toast notifications.
 */

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("simulateBtn")?.addEventListener("click", runSimulation);
  document.getElementById("newSimBtn")?.addEventListener("click", resetSimulator);
  document.querySelectorAll(".scenario-preset").forEach((p) =>
    p.addEventListener("click", () => {
      const input = document.getElementById("scenarioInput");
      if (input) input.value = p.dataset.q;
      runSimulation();
    })
  );
});

async function runSimulation() {
  const query   = document.getElementById("scenarioInput")?.value.trim();
  const simBtn  = document.getElementById("simulateBtn");
  const progress = document.getElementById("simProgress");
  const results  = document.getElementById("simResults");

  if (!query) {
    showToast("Please enter a scenario query first.", "warning");
    document.getElementById("scenarioInput")?.focus();
    return;
  }

  // Loading state
  if (simBtn)  simBtn.disabled = true;
  progress?.classList.remove("d-none");
  results?.classList.add("d-none");

  // Animate the progress bar text
  const cancelAnim = startLoadingAnimation("simLoadingText", "scenario");

  try {
    const res = await postJson("/api/simulate", { query });
    progress?.classList.add("d-none");
    cancelAnim();

    if (res.status === "ok") {
      _renderImpactCards(res.impact, res.description);
      _renderAiReasoning(res.ai_reasoning);
      _renderScenarioChart(res.impact);
      results?.classList.remove("d-none");
      showToast("Scenario simulation complete.", "success");
    } else {
      showToast(res.message || "Simulation failed. Please try again.", "danger");
    }
  } catch (e) {
    progress?.classList.add("d-none");
    cancelAnim();
    showToast("Network error. Please check your connection.", "danger");
  } finally {
    if (simBtn) simBtn.disabled = false;
  }
}

function _renderImpactCards(impact, description) {
  const container   = document.getElementById("impactCards");
  if (!container) return;

  const cur        = "$";   // currency from analysis if available
  const isReduction = impact.direction === "reduction";
  const sign       = isReduction ? "-" : "+";
  const colorClass = isReduction ? "text-success" : "text-danger";

  container.innerHTML = `
    <div class="col-12">
      <div class="alert alert-primary d-flex align-items-center gap-2 mb-0" role="alert">
        <i class="bi bi-sliders fs-5" aria-hidden="true"></i>
        <div><strong>Scenario:</strong> ${description}</div>
      </div>
    </div>
    ${[
      ["Monthly kWh",   "bi-lightning-charge-fill", `${sign}${impact.monthly_kwh_change} kWh`],
      ["Monthly Cost",  "bi-currency-dollar",        `${sign}${cur}${impact.monthly_cost_change}`],
      ["Annual Cost",   "bi-calendar3",              `${sign}${cur}${impact.annual_cost_change}`],
      ["% of Total Bill","bi-percent",               `${sign}${impact.percentage_saving}%`],
    ].map(([label, icon, val]) => `
      <div class="col-6 col-md-3">
        <div class="card kpi-card text-center h-100">
          <div class="card-body">
            <div class="kpi-icon ${colorClass}">
              <i class="bi ${icon}" aria-hidden="true"></i>
            </div>
            <div class="kpi-value ${colorClass}">${val}</div>
            <div class="kpi-label">${label}</div>
          </div>
        </div>
      </div>`).join("")}
  `;
}

function _renderAiReasoning(text) {
  const el = document.getElementById("aiReasoningText");
  if (el) {
    el.innerHTML = nl2br(text || "AI reasoning is not available — configure IBM watsonx.ai credentials to enable.");
  }
}

function _renderScenarioChart(impact) {
  const before = parseFloat(impact.current_monthly_kwh || 0);
  const after  = parseFloat(impact.new_monthly_kwh || 0);

  createChart("scenarioChart", "bar", {
    labels: ["Before", "After"],
    datasets: [{
      label: "Monthly kWh",
      data: [before, after],
      backgroundColor: [
        "rgba(239,68,68,0.65)",
        "rgba(23,178,106,0.65)",
      ],
      borderRadius: 8,
    }],
  }, {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true } },
  });
}

function resetSimulator() {
  const input   = document.getElementById("scenarioInput");
  const results = document.getElementById("simResults");
  if (input)   input.value = "";
  if (results) results.classList.add("d-none");
  input?.focus();
}
