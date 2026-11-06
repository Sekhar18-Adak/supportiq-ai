(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const chat = $("#chat");
  const form = $("#chatForm");
  const question = $("#question");
  const trace = $("#trace");
  const sourceUsed = $("#sourceUsed");
  const modal = $("#uploadModal");
  let requestRunning = false;
  let documents = [];

  // Small safe text formatter. It intentionally does not interpret model output as HTML.
  function escapeHtml(value = "") {
    return String(value).replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[char]);
  }

  function renderBasicMarkdown(value = "") {
    // Safe, deliberately limited Markdown: headings, emphasis, inline code and lists.
    const lines = escapeHtml(value).split(/\r?\n/);
    let html = "", inList = false;
    const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };
    for (const line of lines) {
      const trimmed = line.trim();
      const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
      const bullet = trimmed.match(/^[-*]\s+(.+)$/);
      if (heading) {
        closeList();
        const level = heading[1].length;
        html += `<h${level}>${inlineFormat(heading[2])}</h${level}>`;
      } else if (bullet) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += `<li>${inlineFormat(bullet[1])}</li>`;
      } else {
        closeList();
        if (trimmed) html += `<p>${inlineFormat(trimmed)}</p>`;
      }
    }
    closeList();
    return html || "<p></p>";
  }

  function inlineFormat(text) {
    return text
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }

  function addMessage(role, text, source = "", citations = []) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;
    const content = document.createElement("div");
    content.className = "message-content";

    if (role === "assistant") {
      const avatar = document.createElement("div");
      avatar.className = "message-avatar";
      avatar.textContent = "S";
      wrapper.appendChild(avatar);
      const label = document.createElement("small");
      label.textContent = "SUPPORTIQ AI";
      content.appendChild(label);
    }

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (role === "assistant") bubble.innerHTML = renderBasicMarkdown(text);
    else bubble.textContent = text;
    if (source) {
      const sourceEl = document.createElement("div");
      sourceEl.className = "answer-source";
      sourceEl.textContent = `Source: ${source}`;
      bubble.appendChild(sourceEl);
    }
    if (Array.isArray(citations) && citations.length) {
      const citationBox = document.createElement("div");
      citationBox.className = "citations";
      const title = document.createElement("b");
      title.textContent = "Sources";
      citationBox.appendChild(title);
      citations.forEach((citation) => {
        const row = document.createElement("div");
        const label = String(citation.title || citation.source || "Source");
        if (citation.url && /^https?:\/\//i.test(citation.url)) {
          const link = document.createElement("a");
          link.href = citation.url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = label;
          row.appendChild(link);
        } else {
          row.textContent = label;
        }
        citationBox.appendChild(row);
      });
      bubble.appendChild(citationBox);
    }
    content.appendChild(bubble);
    wrapper.appendChild(content);
    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
  }

  function showTyping() {
    const row = document.createElement("div");
    row.className = "message assistant";
    row.id = "typingMessage";
    row.innerHTML = '<div class="message-avatar">S</div><div class="message-content"><small>SUPPORTIQ AI</small><div class="bubble"><span class="typing-dots"><i></i><i></i><i></i></span></div></div>';
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
  }

  function renderTrace(items = []) {
    trace.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No trace details were returned for this request.";
      trace.appendChild(empty);
      return;
    }
    items.forEach(item => {
      const node = document.createElement("div");
      node.className = "trace-item";
      node.textContent = typeof item === "string" ? item : JSON.stringify(item);
      trace.appendChild(node);
    });
  }

  async function askAgent(rawQuestion) {
    const q = rawQuestion.trim();
    if (!q || requestRunning) return;
    requestRunning = true;
    addMessage("user", q);
    question.value = "";
    renderTrace(["Running LangGraph workflow…"]);
    sourceUsed.textContent = "Processing";
    $("#sendButton").disabled = true;
    $$(".suggestion").forEach(button => button.disabled = true);
    showTyping();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      $("#typingMessage")?.remove();
      addMessage("assistant", data.answer || "The agent returned an empty answer.", data.source_used || "", data.citations || []);
      renderTrace(data.trace || []);
      sourceUsed.textContent = data.source_used || "Not specified";
    } catch (error) {
      $("#typingMessage")?.remove();
      addMessage("assistant", `I couldn't complete that request: ${error.message}`);
      renderTrace(["Request failed. Check the API terminal for details."]);
      sourceUsed.textContent = "Error";
    } finally {
      requestRunning = false;
      $("#sendButton").disabled = false;
      $$(".suggestion").forEach(button => button.disabled = false);
      question.focus();
    }
  }

  form?.addEventListener("submit", event => {
    event.preventDefault();
    askAgent(question.value);
  });
  question?.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  $$(".suggestion").forEach(button => button.addEventListener("click", () => askAgent(button.textContent)));
  $("#newChat")?.addEventListener("click", () => {
    if (requestRunning) return;
    chat.innerHTML = '<div class="message assistant"><div class="message-avatar">S</div><div class="message-content"><small>SUPPORTIQ AI</small><div class="bubble"><b>New conversation started.</b><p>What can I help you with?</p></div></div></div>';
    renderTrace([]);
    sourceUsed.textContent = "Not available yet";
  });

  // Navigation uses one landing dashboard and switches views without reloading the app.
  const titles = { dashboard: "Dashboard", chat: "AI Assistant", knowledge: "Uploaded Data", analytics: "Analytics", settings: "Settings" };
  function navigate(view) {
    if (!titles[view]) return;
    $$(".view").forEach(section => section.classList.toggle("active", section.id === `view-${view}`));
    $$(".nav-link").forEach(button => button.classList.toggle("active", button.dataset.view === view));
    $("#pageTitle").textContent = titles[view];
    $("#sidebar").classList.remove("open");
    if (view === "knowledge") loadDocuments();
    if (view === "analytics") loadAnalytics();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  $$(".nav-link").forEach(button => button.addEventListener("click", () => navigate(button.dataset.view)));
  $$("[data-go]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.go)));
  $$("[data-view-link]").forEach(link => link.addEventListener("click", event => { event.preventDefault(); navigate(link.dataset.viewLink); }));
  $("#menuToggle")?.addEventListener("click", () => $("#sidebar").classList.toggle("open"));

  /* =========================================
   ANALYTICS DASHBOARD
========================================= */

let queryActivityChart = null;
let sourceDistributionChart = null;

const analyticsColors = [
    "#a855f7",
    "#60a5fa",
    "#55d6a2",
    "#fb923c"
];

function formatMetric(value) {
    const number = Number(value ?? 0);

    return Number.isFinite(number)
        ? number.toLocaleString()
        : "—";
}

function formatResponseTime(value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    const number = Number(value);

    return Number.isFinite(number)
        ? `${number.toFixed(0)} ms`
        : "—";
}

function formatActivityDate(value) {
    if (!value) return "—";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? String(value)
        : date.toLocaleString();
}

function updateAnalyticsCards(overview = {}) {

    $("#totalQueries").textContent =
        formatMetric(overview.total_queries);

    $("#todayQueries").textContent =
        formatMetric(overview.today_queries);

    $("#successRate").textContent =
        `${Number(overview.success_rate ?? 0).toFixed(1)}%`;

    $("#avgResponseTime").textContent =
        formatResponseTime(overview.average_response_time_ms);

    $("#failedQueries").textContent =
        formatMetric(overview.failed_queries);

    $("#totalRetries").textContent =
        formatMetric(overview.total_retries);
}


/* Query Activity Chart */

function renderQueryActivity(items = []) {

    const canvas = $("#queryActivityChart");

    if (!canvas || typeof Chart === "undefined") return;

    const labels = items.map(item => item.date || "Unknown");

    const successful = items.map(item =>
        Number(item.successful_queries ?? 0)
    );

    const failed = items.map(item =>
        Number(item.failed_queries ?? 0)
    );

    if (queryActivityChart) {
        queryActivityChart.destroy();
    }

    queryActivityChart = new Chart(canvas, {
        type: "line",

        data: {
            labels,

            datasets: [
                {
                    label: "Successful",
                    data: successful,
                    borderColor: "#55d6a2",
                    backgroundColor: "#55d6a222",
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                },
                {
                    label: "Failed",
                    data: failed,
                    borderColor: "#fb7185",
                    backgroundColor: "#fb718522",
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                }
            ]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            interaction: {
                intersect: false,
                mode: "index"
            },

            plugins: {
                legend: {
                    labels: {
                        color: "#aaa6b7",
                        usePointStyle: true
                    }
                }
            },

            scales: {
                x: {
                    ticks: { color: "#9996aa" },
                    grid: { color: "#30304155" }
                },

                y: {
                    beginAtZero: true,
                    ticks: {
                        color: "#9996aa",
                        precision: 0
                    },
                    grid: { color: "#30304155" }
                }
            }
        }
    });
}


/* Source Distribution Chart */

function renderSourceDistribution(sourceData = {}) {

    const canvas = $("#sourceDistributionChart");

    if (!canvas || typeof Chart === "undefined") return;

    const sourceLabels = {
        private_kb: "Private Knowledge Base",
        web_search: "Web Search",
        direct: "Direct Answer",
        insufficient_evidence: "Insufficient Evidence"
    };

    const entries = Object.entries(sourceLabels);

    const labels = entries.map(([, label]) => label);

    const values = entries.map(([key]) =>
        Number(sourceData[key] ?? 0)
    );

    if (sourceDistributionChart) {
        sourceDistributionChart.destroy();
    }

    sourceDistributionChart = new Chart(canvas, {
        type: "doughnut",

        data: {
            labels,

            datasets: [{
                data: values,
                backgroundColor: analyticsColors,
                borderColor: "#1a1a25",
                borderWidth: 4,
                hoverOffset: 7
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            cutout: "70%",

            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    const legend = $("#sourceLegend");

    legend.replaceChildren();

    entries.forEach(([key, label], index) => {

        const row = document.createElement("div");
        row.className = "source-legend-item";

        const labelBox = document.createElement("div");
        labelBox.className = "legend-label";

        const dot = document.createElement("span");
        dot.className = "legend-dot";
        dot.style.backgroundColor = analyticsColors[index];

        const text = document.createElement("span");
        text.textContent = label;

        labelBox.append(dot, text);

        const count = document.createElement("strong");
        count.textContent = formatMetric(sourceData[key]);

        row.append(labelBox, count);

        legend.appendChild(row);
    });
}


/* Recent Activity Table */

function renderRecentActivity(items = []) {

    const tbody = $("#analyticsActivityRows");

    tbody.replaceChildren();

    if (!items.length) {

        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 6;
        cell.className = "table-empty";
        cell.textContent = "No activity recorded yet.";

        row.appendChild(cell);
        tbody.appendChild(row);

        return;
    }

    items.forEach(item => {

        const row = document.createElement("tr");

        const questionCell = document.createElement("td");
        questionCell.textContent = item.question || "Unknown question";

        const sourceCell = document.createElement("td");
        sourceCell.textContent = item.source_used || "—";

        const statusCell = document.createElement("td");

        const badge = document.createElement("span");

        const status = String(item.status || "success").toLowerCase();

        badge.className = `status-badge ${
            status === "success" ? "status-success" : "status-failed"
        }`;

        badge.textContent = status === "success" ? "Success" : "Failed";

        statusCell.appendChild(badge);

        const responseCell = document.createElement("td");
        responseCell.textContent =
            formatResponseTime(item.response_time_ms);

        const retryCell = document.createElement("td");
        retryCell.textContent = formatMetric(item.retry_count);

        const dateCell = document.createElement("td");
        dateCell.textContent = formatActivityDate(item.created_at);

        row.append(
            questionCell,
            sourceCell,
            statusCell,
            responseCell,
            retryCell,
            dateCell
        );

        tbody.appendChild(row);
    });
}


/* Fetch Analytics API */

async function loadAnalytics() {

    const status = $("#analyticsStatus");
    const refreshButton = $("#refreshAnalytics");
    const period = $("#analyticsPeriod")?.value || "7";

    if (status) {
        status.textContent = "Fetching analytics data...";
        status.classList.remove("error");
    }

    if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.textContent = "Loading...";
    }

    try {

        const response = await fetch(
            `/api/analytics?days=${encodeURIComponent(period)}`
        );

        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(result.detail || "Unable to load analytics");
        }

        const data = result.data || {};

        updateAnalyticsCards(data.overview || {});

        renderQueryActivity(data.daily_analytics || []);

        renderSourceDistribution(
            data.overview?.source_distribution || {}
        );

        renderRecentActivity(data.recent_activity || []);

        if (status) {
            status.textContent =
                `Analytics updated successfully · Last ${period} days`;
        }

    } catch (error) {

        console.error("Analytics error:", error);

        if (status) {
            status.textContent = `Analytics error: ${error.message}`;
            status.classList.add("error");
        }

    } finally {

        if (refreshButton) {
            refreshButton.disabled = false;
            refreshButton.textContent = "↻ Refresh";
        }
    }
}


/* Analytics Event Listeners */

$("#refreshAnalytics")?.addEventListener("click", loadAnalytics);

$("#analyticsPeriod")?.addEventListener("change", loadAnalytics);

  // Health check uses the existing endpoint; it does not touch model or vector settings.
  async function checkHealth() {
    try {
      const response = await fetch("/api/health");
      if (!response.ok) throw new Error("Health check failed");
      const data = await response.json();
      const label = data.status === "ok" ? "Connected" : (data.status || "Available");
      $("#apiStatus").textContent = label;
      $("#healthValue").textContent = label;
      $("#healthNote").textContent = data.service || "FastAPI is responding";
      $("#settingsHealth").textContent = label;
    } catch {
      $("#apiStatus").textContent = "Unavailable";
      $("#healthValue").textContent = "Offline";
      $("#healthNote").textContent = "Could not reach /api/health";
      $("#settingsHealth").textContent = "Unavailable";
    }
  }

  // Document list is provided by the optional GET /api/documents endpoint included in backend_additions.md.
  function formatBytes(bytes) {
    if (!Number.isFinite(Number(bytes))) return "—";
    const value = Number(bytes);
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }
  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
  }
  function renderDocuments(items) {
    const rows = $("#fileRows");
    rows.replaceChildren();
    if (!items.length) {
      const tr = document.createElement("tr"), td = document.createElement("td");
      td.colSpan = 5; td.className = "table-empty"; td.textContent = "No supported documents found in the configured folders.";
      tr.appendChild(td); rows.appendChild(tr); return;
    }
    items.forEach(file => {
      const tr = document.createElement("tr");
      const name = document.createElement("td");
      const fileName = document.createElement("div"); fileName.className = "file-name";
      const icon = document.createElement("span"); icon.className = "file-type-icon"; icon.textContent = String(file.extension || "").replace(".", "").toUpperCase().slice(0, 4) || "FILE";
      const text = document.createElement("div");
      const title = document.createElement("b"); title.textContent = file.name || "Untitled";
      const sub = document.createElement("small"); sub.textContent = file.path_label || "Knowledge file";
      text.append(title, sub); fileName.append(icon, text); name.appendChild(fileName); tr.appendChild(name);
      [String(file.extension || "—").toUpperCase(), file.location || "—", formatBytes(file.size), formatDate(file.modified_at)].forEach(value => {
        const td = document.createElement("td"); td.textContent = value; tr.appendChild(td);
      });
      rows.appendChild(tr);
    });
  }
  async function loadDocuments() {
    $("#fileRows").innerHTML = '<tr><td colspan="5" class="table-empty">Loading document library…</td></tr>';
    try {
      const response = await fetch("/api/documents");
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Document listing endpoint unavailable");
      documents = Array.isArray(data.documents) ? data.documents : [];
      $("#libraryTotal").textContent = data.total ?? documents.length;
      $("#uploadedTotal").textContent = data.uploaded_count ?? documents.filter(x => x.location === "Uploaded").length;
      $("#sampleTotal").textContent = data.sample_count ?? documents.filter(x => x.location === "Sample KB").length;
      $("#docCount").textContent = data.total ?? documents.length;
      $("#sourceCount").textContent = new Set(documents.map(x => x.location)).size;
      $("#docCountNote").textContent = "Files in configured knowledge folders";
      $("#libraryNotice").textContent = "Files are listed from the upload and sample KB folders. Removing a file here is not supported and does not alter Pinecone vectors.";
      applyFileFilter();
    } catch (error) {
      $("#fileRows").innerHTML = `<tr><td colspan="5" class="table-empty">${escapeHtml(error.message)}. Add the GET /api/documents endpoint from backend_additions.md.</td></tr>`;
      $("#libraryTotal").textContent = "—"; $("#uploadedTotal").textContent = "—"; $("#sampleTotal").textContent = "—";
      $("#docCount").textContent = "—"; $("#sourceCount").textContent = "—";
      $("#docCountNote").textContent = "Document listing API not connected";
    }
  }
  function applyFileFilter() {
    const query = ($("#fileSearch")?.value || "").trim().toLowerCase();
    const filtered = documents.filter(file => `${file.name} ${file.extension} ${file.location}`.toLowerCase().includes(query));
    renderDocuments(filtered);
  }
  $("#refreshFiles")?.addEventListener("click", loadDocuments);
  $("#fileSearch")?.addEventListener("input", applyFileFilter);

  // Upload modal and existing ingestion endpoint.
  function openModal() { modal.classList.remove("hidden"); $("#adminKey").focus(); }
  function closeModal() { modal.classList.add("hidden"); }
  $("#openUpload")?.addEventListener("click", openModal);
  $("#openUploadSecondary")?.addEventListener("click", openModal);
  $("#closeUpload")?.addEventListener("click", closeModal);
  modal?.addEventListener("click", event => { if (event.target === modal) closeModal(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeModal(); });

  $("#uploadBtn")?.addEventListener("click", async () => {
    const file = $("#fileInput").files[0];
    const key = $("#adminKey").value;
    const status = $("#modalUploadStatus");
    if (!file) { status.textContent = "Choose a file first."; return; }
    if (!/\.(pdf|txt|md|docx)$/i.test(file.name)) { status.textContent = "Unsupported file type."; return; }
    if (!key) { status.textContent = "Enter the admin API key."; return; }

    const button = $("#uploadBtn");
    button.disabled = true; status.textContent = "Uploading and indexing document…";
    const body = new FormData(); body.append("file", file);
    try {
      const response = await fetch("/api/ingest", { method: "POST", headers: { "X-Admin-Key": key }, body });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Upload failed (${response.status})`);
      const message = `Indexed ${data.file || file.name}: ${data.chunks ?? "?"} chunks.`;
      status.textContent = message;
      $("#uploadStatus").textContent = message;
      $("#uploadStatus").className = "upload-result";
      $("#fileInput").value = "";
      await loadDocuments();
    } catch (error) {
      status.textContent = `Error: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });

  checkHealth();
  loadDocuments();
})();