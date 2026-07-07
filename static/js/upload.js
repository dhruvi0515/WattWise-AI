/**
 * WattWise AI v2.1 — Upload Page JavaScript
 * Handles drag-and-drop, file selection, upload, validation, and result display.
 */

document.addEventListener("DOMContentLoaded", () => {
  const dropZone   = document.getElementById("dropZone");
  const fileInput  = document.getElementById("fileInput");
  const fileInfo   = document.getElementById("fileInfo");
  const uploadBtn  = document.getElementById("uploadBtn");
  const progressEl = document.getElementById("uploadProgress");
  const resultDiv  = document.getElementById("uploadResult");
  const resultBody = document.getElementById("uploadResultBody");

  let selectedFile = null;

  // ── Drag-and-drop ──────────────────────────────────────────────────────────

  ["dragenter", "dragover"].forEach((ev) =>
    dropZone?.addEventListener(ev, (e) => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    dropZone?.addEventListener(ev, (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
    })
  );
  dropZone?.addEventListener("drop", (e) => {
    const file = e.dataTransfer?.files[0];
    if (file) _handleFileSelect(file);
  });

  // ── File input ─────────────────────────────────────────────────────────────

  fileInput?.addEventListener("change", (e) => {
    if (e.target.files[0]) _handleFileSelect(e.target.files[0]);
  });

  // ── Upload button ──────────────────────────────────────────────────────────

  uploadBtn?.addEventListener("click", _doUpload);

  // ── Private helpers ────────────────────────────────────────────────────────

  function _handleFileSelect(file) {
    // Basic client-side validation
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["csv", "xlsx"].includes(ext)) {
      showToast("Please select a CSV or Excel (.xlsx) file.", "warning");
      return;
    }
    if (file.size > 16 * 1024 * 1024) {
      showToast("File exceeds the 16 MB limit. Please select a smaller file.", "warning");
      return;
    }

    selectedFile = file;
    document.getElementById("fileName").textContent = file.name;
    document.getElementById("fileSize").textContent = _formatBytes(file.size);
    fileInfo?.classList.remove("d-none");
    uploadBtn?.classList.remove("d-none");
    resultDiv?.classList.add("d-none");
  }

  async function _doUpload() {
    if (!selectedFile) return;

    // Loading state
    progressEl?.classList.remove("d-none");
    uploadBtn?.classList.add("d-none");

    const cancelAnim = startLoadingAnimation("uploadLoadingText", "default");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const r   = await fetch("/api/upload", { method: "POST", body: formData });
      const res = await r.json();
      progressEl?.classList.add("d-none");
      cancelAnim();

      if (res.status === "ok") {
        _showResult(res);
        showToast(res.message, "success");
      } else {
        _showError(res.message || "Upload failed. Please check the file and try again.");
        uploadBtn?.classList.remove("d-none");
        showToast(res.message, "danger");
      }
    } catch (e) {
      progressEl?.classList.add("d-none");
      cancelAnim();
      _showError("Network error. Please check your connection and try again.");
      uploadBtn?.classList.remove("d-none");
      showToast("Network error during upload.", "danger");
    }
  }

  function _showResult(res) {
    if (!resultDiv || !resultBody) return;
    const a     = res.analysis || {};
    const stats = res.stats    || {};

    // Warnings from the validator
    const warningsHtml = (stats.warnings || []).map((w) =>
      `<div class="alert alert-warning alert-sm mb-2 py-2 small">
         <i class="bi bi-exclamation-triangle-fill me-1" aria-hidden="true"></i>${w}
       </div>`
    ).join("");

    resultBody.innerHTML = `
      <div class="row g-3 mb-3">
        <div class="col-6 col-md-3 text-center">
          <div class="fw-bold fs-5 text-primary">${a.total_monthly_kwh || 0}</div>
          <div class="small text-muted">kWh/Month</div>
        </div>
        <div class="col-6 col-md-3 text-center">
          <div class="fw-bold fs-5 text-success">${a.currency || "$"}${a.total_monthly_cost || 0}</div>
          <div class="small text-muted">Est. Bill</div>
        </div>
        <div class="col-6 col-md-3 text-center">
          <div class="fw-bold fs-5 text-warning" style="font-size:0.9rem!important">${a.top_appliance || "N/A"}</div>
          <div class="small text-muted">Top Consumer</div>
        </div>
        <div class="col-6 col-md-3 text-center">
          <div class="fw-bold fs-5 text-info">${(stats.rows || 0).toLocaleString()}</div>
          <div class="small text-muted">Rows Analysed</div>
        </div>
      </div>

      <div class="d-flex flex-wrap gap-2 mb-3">
        <span class="badge bg-primary-subtle text-primary">
          Score: ${a.energy_score || "N/A"}/100
        </span>
        <span class="badge bg-secondary-subtle text-secondary">
          ${a.efficiency_rating || "N/A"}
        </span>
        <span class="badge bg-success-subtle text-success">
          Data quality: ${stats.quality_score || 0}%
        </span>
      </div>

      ${warningsHtml}
    `;
    resultDiv.classList.remove("d-none");
  }

  function _showError(msg) {
    if (!resultDiv || !resultBody) return;
    resultBody.innerHTML = `
      <div class="alert alert-danger d-flex align-items-center gap-2 mb-0" role="alert">
        <i class="bi bi-exclamation-octagon-fill flex-shrink-0" aria-hidden="true"></i>
        <div>${msg}</div>
      </div>`;
    resultDiv.classList.remove("d-none");
    // Swap card style to danger
    const card   = resultDiv.querySelector(".card");
    const header = resultDiv.querySelector(".card-header");
    card?.classList.replace("border-success", "border-danger");
    if (header) {
      header.classList.replace("bg-success", "bg-danger");
      header.textContent = "Upload Failed";
    }
  }

  function _formatBytes(bytes) {
    if (bytes < 1024)     return bytes + " B";
    if (bytes < 1048576)  return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  }
});
