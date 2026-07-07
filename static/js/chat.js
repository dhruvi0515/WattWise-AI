/**
 * WattWise AI v3.0 — Chat Page JavaScript
 * ========================================
 * Manages the AI chat interface:
 * - Sends messages and renders responses
 * - Shows AI thinking bar + phase text during processing
 * - Animates the agent workflow pipeline
 * - Updates session memory panel and recent reports list
 * - Handles quick prompts and sample question chips
 */

(function () {
  // DOM is already parsed when this script runs (placed at end of <body>).
  // Using an IIFE instead of DOMContentLoaded avoids the race where
  // DOMContentLoaded fired before this listener was registered.
  if (document.readyState === "loading") {
    // Fallback: script loaded very early, wait for DOM
    document.addEventListener("DOMContentLoaded", initChat);
  } else {
    initChat();
  }

  function initChat() {
  var input    = document.getElementById("chatInput");
  var sendBtn  = document.getElementById("sendChatBtn");
  var clearBtn = document.getElementById("clearChatBtn");
  var win      = document.getElementById("chatWindow");
  var statusEl = document.getElementById("chatStatus");

  if (!input || !sendBtn || !win) {
    console.error("WattWise Chat: required DOM elements not found", {
      input: !!input, sendBtn: !!sendBtn, win: !!win
    });
    return;
  }

  // ── Helper: postJson Utility Function ──────────────────────────────────────
  function postJson(url, data) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: data ? JSON.stringify(data) : JSON.stringify({})
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("HTTP error! Status: " + response.status);
      }
      return response.json();
    });
  }

  // ── Event listeners ────────────────────────────────────────────────────────

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener("click", function () {
    sendMessage();
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", clearChat);
  }

  document.querySelectorAll(".quick-prompt").forEach(function (b) {
    b.addEventListener("click", function () {
      input.value = b.dataset.prompt || "";
      sendMessage();
    });
  });

  document.querySelectorAll(".sample-q-btn").forEach(function (b) {
    b.addEventListener("click", function () {
      input.value = b.dataset.prompt || "";
      input.focus();
      sendMessage();
    });
  });

  scrollToBottom();

  // ── Send Message ──────────────────────────────────────────────────────────

  function sendMessage() {
    var msg = input.value.trim();
    if (!msg) return;
    if (sendBtn.disabled) return;

    input.value = "";

    appendMessage("user", msg);
    showTyping();
    setThinking(true, "Detecting intent\u2026");
    setSendEnabled(false);
    animateAgentFlow("af-intent");

    var cancelPhase = (typeof startLoadingAnimation === "function")
      ? startLoadingAnimation("loadingPhaseText", "chat")
      : function () {};

    postJson("/api/chat", { message: msg })
      .then(function (res) {
        hideTyping();
        setThinking(false);
        cancelPhase();

        if (res.status === "ok") {
          var badge = document.getElementById("intentBadge");
          if (badge && res.intent) {
            var intentLabels = {
              investigate: "Investigate",
              scenario:    "Scenario",
              recommend:   "Recommend",
              question:    "Question",
            };
            badge.textContent = intentLabels[res.intent] || res.intent;
            badge.style.removeProperty("display");
            setTimeout(function () {
              badge.style.setProperty("display", "none", "important");
            }, 5000);
          }

          appendMessage("bot", res.response || "(no response)");
          markAgentFlowDone();

          if (res.report_id) {
            appendReportLink(res.report_id);
            addToRecentReports(res.report_id);
          }

          setStatus("");
        } else {
          appendMessage("bot", "\u26a0 " + (res.message || "An error occurred. Please try again."));
          setStatus("Error \u2014 please try again.");
          markAgentFlowDone(false);
        }
      })
      .catch(function (err) {
        hideTyping();
        setThinking(false);
        cancelPhase();
        appendMessage("bot", "\u26a0 Network error. Please check your connection and try again.");
        setStatus("Connection failed.");
        markAgentFlowDone(false);
      })
      .finally(function () {
        setSendEnabled(true);
      });
  }

  // ── Agent flow animation ──────────────────────────────────────────────────

  var AF_ORDER = ["af-intent", "af-data", "af-context", "af-watsonx", "af-report"];
  var afTimer  = null;

  function animateAgentFlow(startId) {
    if (afTimer) clearInterval(afTimer);
    AF_ORDER.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) { el.classList.remove("active", "done"); }
    });
    if (!startId) return;

    var idx = AF_ORDER.indexOf(startId);

    function step() {
      AF_ORDER.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) { el.classList.remove("active", "done"); }
      });
      var el = document.getElementById(AF_ORDER[idx]);
      if (el) el.classList.add("active");
      idx = (idx + 1) % AF_ORDER.length;
    }
    step();
    afTimer = setInterval(step, 650);
  }

  function markAgentFlowDone(success) {
    if (success === undefined) success = true;
    if (afTimer) { clearInterval(afTimer); afTimer = null; }
    AF_ORDER.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        el.classList.remove("active");
        if (success) el.classList.add("done");
      }
    });
    setTimeout(function () {
      AF_ORDER.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.classList.remove("active", "done");
      });
    }, 2500);
  }

  // ── Append message bubble ─────────────────────────────────────────────────

  function appendMessage(role, content) {
    var div = document.createElement("div");
    div.className = "chat-message " + (role === "user" ? "user-message" : "bot-message");

    var avatarHtml = role === "user"
      ? '<div class="message-avatar user-avatar" aria-hidden="true"><i class="bi bi-person-fill"></i></div>'
      : '<div class="message-avatar" aria-hidden="true"><i class="bi bi-lightning-charge-fill"></i></div>';

    var bubbleContent = role === "bot"
      ? ((typeof nl2br === "function") ? nl2br(content) : escapeHtml(content))
      : "<span>" + escapeHtml(content) + "</span>";

    div.innerHTML = role === "user"
      ? '<div class="message-bubble">' + bubbleContent + "</div>" + avatarHtml
      : avatarHtml + '<div class="message-bubble">' + bubbleContent + "</div>";

    win.appendChild(div);
    scrollToBottom();
  }

  // ── Report link bubble ────────────────────────────────────────────────────

  function appendReportLink(caseId) {
    var div = document.createElement("div");
    div.className = "chat-message bot-message";
    div.setAttribute("role", "status");
    div.innerHTML =
      '<div class="message-avatar" aria-hidden="true">' +
        '<i class="bi bi-file-earmark-text-fill text-ibm-blue"></i>' +
      "</div>" +
      '<div class="message-bubble" style="background:var(--ww-blue-light);">' +
        '<i class="bi bi-shield-check me-1 text-ibm-blue" aria-hidden="true"></i>' +
        "Investigation report generated: " +
        '<a href="/reports/' + escapeHtml(caseId) + '" ' +
           'class="btn btn-sm btn-primary ms-2" ' +
           'aria-label="View report ' + escapeHtml(caseId) + '">' +
          '<i class="bi bi-eye me-1" aria-hidden="true"></i>View ' + escapeHtml(caseId) +
        "</a>" +
      "</div>";
    win.appendChild(div);
    scrollToBottom();
  }

  // ── Recent reports sidebar ────────────────────────────────────────────────

  function addToRecentReports(caseId) {
    var list = document.getElementById("recentReportsList");
    if (!list) return;
    var placeholder = list.querySelector(".text-muted");
    if (placeholder) placeholder.remove();

    var item = document.createElement("a");
    item.href      = "/reports/" + escapeHtml(caseId);
    item.className = "list-group-item list-group-item-action small py-2";
    item.setAttribute("role", "listitem");
    item.innerHTML = '<i class="bi bi-file-earmark-text me-1 text-ibm-blue" aria-hidden="true"></i>' + escapeHtml(caseId);
    list.insertBefore(item, list.firstChild);
  }

  // ── Typing indicator ──────────────────────────────────────────────────────

  function showTyping() {
    var div = document.createElement("div");
    div.id        = "typingIndicator";
    div.className = "chat-message bot-message";
    div.setAttribute("aria-label", "WattWise AI is thinking");
    div.innerHTML =
      '<div class="message-avatar" aria-hidden="true"><i class="bi bi-lightning-charge-fill"></i></div>' +
      '<div class="message-bubble">' +
        '<div class="typing-indicator" aria-hidden="true">' +
          "<span></span><span></span><span></span>" +
        "</div>" +
        '<div class="small text-muted mt-1">Agent Orchestrator processing\u2026</div>' +
      "</div>";
    win.appendChild(div);
    scrollToBottom();
  }

  // ── Hide typing indicator ─────────────────────────────────────────────────

  function hideTyping() {
    var ti = document.getElementById("typingIndicator");
    if (ti) ti.remove();
  }

  // ── AI thinking bar ───────────────────────────────────────────────────────

  function setThinking(active, message) {
    var bar = document.getElementById("aiThinkingBar");
    if (bar) bar.classList.toggle("d-none", !active);
    if (statusEl) statusEl.textContent = active ? (message || "") : "";
  }

  // ── Clear chat ────────────────────────────────────────────────────────────

  function clearChat() {
    if (!confirm("Clear the entire conversation? This cannot be undone.")) return;
    postJson("/api/reset").then(function () {
      win.innerHTML = "";
      appendMessage("bot", "Conversation cleared.\nHow can I help you investigate your energy usage?");
      var recentList = document.getElementById("recentReportsList");
      if (recentList) {
        recentList.innerHTML =
          '<div class="list-group-item text-muted small py-2">' +
            '<i class="bi bi-info-circle me-1"></i>No reports yet.' +
          "</div>";
      }
    });
  }

  // ── Utilities ─────────────────────────────────────────────────────────────

  function scrollToBottom() {
    setTimeout(function () {
      win.scrollTop = win.scrollHeight;
    }, 0);
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  function setSendEnabled(enabled) {
    sendBtn.disabled = !enabled;
    input.disabled   = !enabled;
  }

  function escapeHtml(t) {
    return String(t)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  } // end initChat
}()); // end IIFE