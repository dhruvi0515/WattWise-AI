/**
 * WattWise AI — Analysis Page JavaScript
 * Renders all 4 analysis charts from ANALYSIS data.
 */

document.addEventListener("DOMContentLoaded", () => {
  if (typeof ANALYSIS === "undefined") return;
  renderApplianceBarChart();
  renderCostPieChart();
  renderMonthlyChart();
  renderHourlyAnalysisChart();
});

function renderApplianceBarChart() {
  const apps   = (ANALYSIS.appliances || []).slice(0, 10);
  const labels = apps.map(a => a.appliance);
  const values = apps.map(a => a.monthly_kwh);

  createChart("applianceBarChart", "bar", {
    labels,
    datasets: [{
      label: "kWh / Month",
      data: values,
      backgroundColor: CHART_COLORS,
      borderRadius: 6,
    }],
  }, {
    indexAxis: "y",
    plugins: { legend: { display: false } },
  });
}

function renderCostPieChart() {
  const apps   = (ANALYSIS.appliances || []).slice(0, 8);
  const labels = apps.map(a => a.appliance);
  const values = apps.map(a => a.monthly_cost);

  createChart("costPieChart", "pie", {
    labels,
    datasets: [{
      data: values,
      backgroundColor: CHART_COLORS,
      borderWidth: 1,
    }],
  }, {
    plugins: {
      legend: { position: "right", labels: { font: { size: 11 } } },
      tooltip: {
        callbacks: {
          label: (ctx) => ` ${ANALYSIS.currency || "$"}${parseFloat(ctx.raw).toFixed(2)}`,
        },
      },
    },
  });
}

function renderMonthlyChart() {
  const trend  = ANALYSIS.monthly_trend || [];
  const labels = trend.map(t => t.month);
  const values = trend.map(t => t.kwh);

  createChart("monthlyChart", "line", {
    labels,
    datasets: [{
      label: "kWh",
      data: values,
      borderColor: "#0f62fe",
      backgroundColor: "rgba(15,98,254,0.08)",
      tension: 0.35,
      fill: true,
      pointRadius: 5,
      pointBackgroundColor: "#0f62fe",
    }],
  });
}

function renderHourlyAnalysisChart() {
  const hourly = ANALYSIS.hourly_usage || {};
  const hours  = Array.from({ length: 24 }, (_, i) => i);
  const labels = hours.map(h => {
    const s = h < 12 ? "AM" : "PM";
    const d = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${d}${s}`;
  });
  const values = hours.map(h => hourly[h] || 0);

  createChart("hourlyAnalysisChart", "bar", {
    labels,
    datasets: [{
      label: "kWh",
      data: values,
      backgroundColor: values.map(v =>
        v >= 2.0 ? "rgba(218,30,40,0.65)" :   /* IBM Red */
        v >= 1.4 ? "rgba(241,194,27,0.65)" :  /* IBM Yellow */
                   "rgba(15,98,254,0.55)"),    /* IBM Blue */
      borderRadius: 3,
    }],
  }, {
    plugins: { legend: { display: false } },
  });
}
