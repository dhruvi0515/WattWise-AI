/**
 * WattWise AI v3.0 — Recommendations Page JavaScript
 * ====================================================
 * Uses shared loading state manager and toast notifications.
 * After generating recommendations, this script dynamically re-renders
 * both the structured XAI cards AND the AI narrative so the page updates
 * without a full reload.
 */

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("generateRecBtn")?.addEventListener("click", generateRecs);
});

async function generateRecs() {
  const btn      = document.getElementById("generateRecBtn");
  const progress = document.getElementById("recProgress");
  const content  = document.getElementById("recContent");
  if (!btn || !progress || !content) return;

  // Loading state
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span>Generating…`;
  progress.classList.remove("d-none");

  // Animate loading text
  const cancelAnimation = startLoadingAnimation("recLoadingText", "recommend");

  try {
    const res = await postJson("/api/recommendations");
    progress.classList.add("d-none");
    cancelAnimation();

    if (res.status === "ok") {
      // Re-render the AI narrative text card
      content.innerHTML = `
        <div class="card">
          <div class="card-header d-flex align-items-center justify-content-between">
            <span>
              <i class="bi bi-stars me-2 text-warning" aria-hidden="true"></i>
              AI-Generated Recommendations (Full Text)
            </span>
            <span class="badge bg-warning-subtle text-warning">IBM watsonx.ai</span>
          </div>
          <div class="card-body">
            <div class="ai-narrative">${nl2br(res.recommendations)}</div>
          </div>
        </div>`;

      // Re-build the structured XAI cards section if we have structured recs
      if (res.structured && res.structured.length > 0) {
        const cardsHtml = buildStructuredRecCards(res.structured);
        // Insert the cards container before the AI narrative
        const container = content.parentElement;
        let cardsSection = document.getElementById("structuredRecCards");
        if (!cardsSection) {
          // Create a new container if it doesn't exist
          cardsSection = document.createElement("div");
          cardsSection.id = "structuredRecCards";
          cardsSection.className = "col-12";
          container.insertBefore(cardsSection, content);
        }
        cardsSection.innerHTML = cardsHtml;
      }

      btn.innerHTML = `<i class="bi bi-stars me-1"></i>Regenerate Recommendations`;
      showToast("Recommendations generated successfully.", "success");
    } else {
      content.innerHTML = `
        <div class="alert alert-danger d-flex align-items-center gap-2" role="alert">
          <i class="bi bi-exclamation-octagon-fill flex-shrink-0" aria-hidden="true"></i>
          <div>${res.message || "Could not generate recommendations. Please try again."}</div>
        </div>`;
      btn.innerHTML = `<i class="bi bi-stars me-1"></i>Generate Recommendations`;
      showToast(res.message, "warning");
    }
  } catch (e) {
    progress.classList.add("d-none");
    cancelAnimation();
    content.innerHTML = `
      <div class="alert alert-danger d-flex align-items-center gap-2" role="alert">
        <i class="bi bi-wifi-off flex-shrink-0" aria-hidden="true"></i>
        <div>Network error. Please check your connection and try again.</div>
      </div>`;
    btn.innerHTML = `<i class="bi bi-stars me-1"></i>Generate Recommendations`;
    showToast("Network error. Please try again.", "danger");
  } finally {
    btn.disabled = false;
  }
}

/**
 * Build the HTML for structured XAI recommendation cards.
 * @param {Array} recs - Array of structured recommendation objects from API
 * @returns {string} Full HTML for the structured recommendation cards section
 */
function buildStructuredRecCards(recs) {
  const now = new Date().toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const cardsInnerHtml = recs.map(rec => {
    const ribbonClass =
      rec.priority === "High"   ? "ribbon-high" :
      rec.priority === "Medium" ? "ribbon-medium" : "ribbon-low";

    const difficultyBadge =
      rec.difficulty === "Easy"   ? "bg-success" :
      rec.difficulty === "Medium" ? "bg-warning text-dark" : "bg-danger";

    return `
      <div class="col-12 col-lg-6">
        <div class="card rec-card h-100 border-0 bg-body-secondary position-relative">
          <div class="priority-ribbon ${ribbonClass}">${rec.priority}</div>
          <div class="card-body pt-3">
            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="rec-icon-lg"><i class="bi ${rec.icon || 'bi-lightbulb'}"></i></span>
              <strong>${rec.title}</strong>
            </div>

            <!-- XAI: Why -->
            <div class="xai-block mb-2">
              <div class="xai-label">
                <i class="bi bi-question-circle-fill me-1 text-primary"></i>Why this recommendation?
              </div>
              <p class="small text-muted mb-0">${rec.why}</p>
            </div>

            <!-- XAI: Expected Benefit -->
            <div class="xai-block mb-2">
              <div class="xai-label">
                <i class="bi bi-graph-up-arrow me-1 text-success"></i>Expected Benefit
              </div>
              <p class="small text-muted mb-0">${rec.expected_benefit}</p>
            </div>

            <!-- Metrics Row -->
            <div class="d-flex flex-wrap gap-1 mt-2">
              <span class="badge bg-success-subtle text-success">
                <i class="bi bi-lightning me-1"></i>${rec.estimated_monthly_kwh_saving} kWh/mo saved
              </span>
              <span class="badge bg-primary-subtle text-primary">
                ${rec.currency}${rec.estimated_monthly_cost_saving}/mo
              </span>
              <span class="badge bg-warning-subtle text-warning">
                ${rec.currency}${rec.estimated_annual_cost_saving}/yr
              </span>
              <span class="badge bg-secondary-subtle text-secondary">
                <i class="bi bi-cloud me-1"></i>${rec.estimated_co2_saving_kg} kg CO₂
              </span>
            </div>

            <!-- Difficulty + Time -->
            <div class="d-flex flex-wrap gap-1 mt-1">
              <span class="badge ${difficultyBadge}">${rec.difficulty}</span>
              <span class="badge bg-info-subtle text-info">
                <i class="bi bi-clock me-1"></i>${rec.time_required}
              </span>
            </div>

          </div>
        </div>
      </div>`;
  }).join("");

  return `
    <div class="card mb-2">
      <div class="card-header d-flex align-items-center justify-content-between">
        <span>
          <i class="bi bi-list-ol me-2 text-primary"></i>Prioritised Action Plan
        </span>
        <span class="text-muted small">Generated: ${now}</span>
      </div>
      <div class="card-body">
        <div class="row g-3">
          ${cardsInnerHtml}
        </div>
      </div>
    </div>`;
}
