/**
 * WattWise AI v3.0 — Settings Page JavaScript
 * =============================================
 * Handles:
 *  - Electricity rate & currency save
 *  - User profile (location, household size, home type) save
 *  - Energy goals (savings target, AI personality) save
 *  - Theme switcher (light / dark / system)
 *  - Session reset
 */

document.addEventListener("DOMContentLoaded", () => {

  // ── Electricity & Currency settings form ──────────────────────────────────
  document.getElementById("settingsForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("saveSettingsBtn");
    setButtonLoading(btn, true, "Saving…");

    const rate     = parseFloat(document.getElementById("electricityRate")?.value || 0.12);
    const currency = (document.getElementById("currencySymbol")?.value || "$").trim();

    if (isNaN(rate) || rate <= 0 || rate > 10) {
      showAlert("settingsMsg", "Please enter a valid electricity rate (0.001 – 10).", "warning");
      setButtonLoading(btn, false, '<i class="bi bi-save me-1"></i>Save Settings');
      return;
    }

    try {
      const res = await postJson("/api/settings", { electricity_rate: rate, currency });
      if (res.status === "ok") {
        showAlert("settingsMsg", "Settings saved. Energy analysis will refresh on next page load.", "success");
        showToast("Settings saved successfully.", "success");
      } else {
        showAlert("settingsMsg", res.message || "Could not save settings.", "danger");
      }
    } catch (_err) {
      showAlert("settingsMsg", "Network error. Please try again.", "danger");
    } finally {
      setButtonLoading(btn, false, '<i class="bi bi-save me-1"></i>Save Settings');
    }
  });

  // ── User Profile form (Session Memory) ───────────────────────────────────
  document.getElementById("profileForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("saveProfileBtn");
    setButtonLoading(btn, true, "Saving…");

    const location   = document.getElementById("profileLocation")?.value.trim();
    const familySize = document.getElementById("profileFamilySize")?.value;
    const homeType   = document.getElementById("profileHomeType")?.value;

    try {
      const res = await postJson("/api/settings", {
        location:    location    || undefined,
        family_size: familySize  ? parseInt(familySize, 10) : undefined,
        home_type:   homeType    || undefined,
      });
      if (res.status === "ok") {
        showAlert("profileMsg", "Profile saved — AI will use this for personalised recommendations.", "success");
        showToast("Profile updated.", "success");
      } else {
        showAlert("profileMsg", res.message || "Could not save profile.", "danger");
      }
    } catch (_err) {
      showAlert("profileMsg", "Network error. Please try again.", "danger");
    } finally {
      setButtonLoading(btn, false, '<i class="bi bi-person-check me-1"></i>Save Profile');
    }
  });

  // ── Energy Goals form ─────────────────────────────────────────────────────
  document.getElementById("goalsForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const savingsGoal  = document.getElementById("savingsGoal")?.value;
    const aiPersonality = document.getElementById("aiPersonality")?.value;

    try {
      const res = await postJson("/api/settings", {
        savings_goal:   savingsGoal   ? parseInt(savingsGoal, 10)  : undefined,
        ai_personality: aiPersonality || undefined,
      });
      if (res.status === "ok") {
        showAlert("goalsMsg", "Goals saved. AI will use your targets in recommendations.", "success");
        showToast("Energy goals updated.", "success");
      } else {
        showAlert("goalsMsg", res.message || "Could not save goals.", "danger");
      }
    } catch (_err) {
      showAlert("goalsMsg", "Network error. Please try again.", "danger");
    }
  });

  // ── Theme switcher ────────────────────────────────────────────────────────
  const themeLabel = document.getElementById("currentThemeLabel");

  function applyTheme(theme) {
    const html  = document.documentElement;
    const icon  = document.getElementById("darkModeIcon");
    const saved = localStorage.getItem("ww-theme");

    let effectiveTheme = theme;
    if (theme === "system") {
      effectiveTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      localStorage.removeItem("ww-theme");
    } else {
      localStorage.setItem("ww-theme", theme);
    }

    html.setAttribute("data-bs-theme", effectiveTheme);
    if (icon) icon.className = effectiveTheme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill";
    if (themeLabel) themeLabel.textContent = theme === "system" ? "System default" : (theme.charAt(0).toUpperCase() + theme.slice(1));
  }

  // Initialise label
  const currentTheme = localStorage.getItem("ww-theme") || "system";
  if (themeLabel) themeLabel.textContent = currentTheme === "system" ? "System default" : currentTheme.charAt(0).toUpperCase() + currentTheme.slice(1);

  document.getElementById("setLightTheme")?.addEventListener("click",  () => applyTheme("light"));
  document.getElementById("setDarkTheme")?.addEventListener("click",   () => applyTheme("dark"));
  document.getElementById("setSystemTheme")?.addEventListener("click", () => applyTheme("system"));

  // ── Demo mode loader ──────────────────────────────────────────────────────
  document.getElementById("loadDemoBtn")?.addEventListener("click", async () => {
    const btn = document.getElementById("loadDemoBtn");
    setButtonLoading(btn, true, "Loading…");
    try {
      const res = await postJson("/api/demo");
      if (res.status === "ok") {
        showAlert("demoMsg",
          `Demo dataset loaded (${res.appliances} appliances). Redirecting to dashboard…`,
          "success");
        showToast("Demo mode activated.", "info");
        setTimeout(() => window.location.replace("/"), 1400);
      } else {
        showAlert("demoMsg", res.message || "Could not load demo dataset.", "danger");
      }
    } catch (_err) {
      showAlert("demoMsg", "Network error. Please try again.", "danger");
    } finally {
      setButtonLoading(btn, false, '<i class="bi bi-play-circle me-1"></i>Load Demo Dataset');
    }
  });

  // ── Session reset ─────────────────────────────────────────────────────────
  document.getElementById("resetSessionBtn")?.addEventListener("click", async () => {
    if (!confirm(
      "Reset session?\n\nThis will clear:\n• All uploaded data\n• Conversation history\n• Generated reports\n• User profile\n\nThe app will return to demo mode."
    )) return;

    try {
      const res = await postJson("/api/reset");
      if (res.status === "ok") {
        showAlert("resetMsg", "Session reset. Reloading…", "success");
        setTimeout(() => window.location.replace("/"), 1400);
      } else {
        showAlert("resetMsg", res.message || "Could not reset session.", "danger");
      }
    } catch (_err) {
      showAlert("resetMsg", "Network error. Please try again.", "danger");
    }
  });

  // ── Helper: button loading state ──────────────────────────────────────────
  function setButtonLoading(btn, loading, label) {
    if (!btn) return;
    btn.disabled = loading;
    btn.innerHTML = loading
      ? `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>${label}`
      : label;
  }
});
