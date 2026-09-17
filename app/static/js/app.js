(() => {
  const landing = document.getElementById("landing");
  const run = document.getElementById("run");
  const skuGrid = document.getElementById("sku-grid");
  const skuBrief = document.getElementById("sku-brief");
  const shotList = document.getElementById("shot-list");
  const resultsGrid = document.getElementById("results-grid");
  const modePill = document.getElementById("mode-pill");
  const channelPills = document.getElementById("channel-pills");
  const backBtn = document.getElementById("back-btn");
  const downloadBtn = document.getElementById("download-btn");
  const compareToggle = document.getElementById("compare-toggle");
  const progressBar = document.getElementById("progress-bar");
  const progressLabel = document.getElementById("progress-label");
  const runTitle = document.getElementById("run-title");
  const runSub = document.getElementById("run-sub");
  const runBrand = document.getElementById("run-brand");
  const statusBanner = document.getElementById("status-banner");

  let pollTimer = null;
  let currentJobId = null;
  let currentSku = null;
  let showCompare = true;
  let starting = false;
  let skuList = [];

  async function getJson(url, fallback) {
    try {
      const res = await fetch(url);
      if (!res.ok) return fallback;
      return await res.json();
    } catch (err) {
      return fallback;
    }
  }

  function showBanner(message, tone) {
    statusBanner.textContent = message;
    statusBanner.classList.remove("hidden");
    statusBanner.dataset.tone = tone;
  }

  async function init() {
    const [health, skusRaw, channelsRaw] = await Promise.all([
      getJson("/api/health", { ok: false, boot_error: "The API is unreachable." }),
      getJson("/api/skus", []),
      getJson("/api/channels", []),
    ]);
    const skus = Array.isArray(skusRaw) ? skusRaw : [];
    const channels = Array.isArray(channelsRaw) ? channelsRaw : [];
    skuList = skus;

    if (!health.ok) {
      showBanner(
        `The application did not start correctly: ${health.boot_error || "unknown error"}`,
        "error"
      );
    } else if (health.degraded_reason) {
      showBanner(health.degraded_reason, "warn");
    }

    if (health.mock_mode) {
      modePill.textContent = "Mock mode";
      modePill.classList.add("mock");
    } else {
      modePill.textContent = "Live generation";
      modePill.classList.remove("mock");
    }

    channelPills.innerHTML = channels
      .map((c) => `<span class="pill">${escapeHtml(c.display_name)}</span>`)
      .join("");

    skuGrid.innerHTML = skus
      .map(
        (s) => `
      <button class="sku-card" data-brand="${escapeHtml(s.brand_ruleset)}" data-sku="${escapeHtml(s.sku)}" type="button"${s.can_generate ? "" : " disabled"}>
        <div class="sku-media"><img src="${escapeHtml(s.hero_thumbnail_url)}" alt="" onerror="this.remove()" /></div>
        <div class="sku-body">
          <span class="sku-brand">${s.brand_ruleset === "coastwide" ? "Coastwide Professional" : "Staples"}</span>
          <h3>${escapeHtml(s.card_label)}</h3>
          <div class="sku-meta">
            <span>${s.shot_count} images</span>
            <span>${s.reference_count} Staples refs</span>
          </div>
          ${s.can_generate ? "" : `<p class="sku-unavailable">${escapeHtml(s.unavailable_reason || "Unavailable")}</p>`}
        </div>
      </button>`
      )
      .join("");

    if (!skus.length) {
      skuGrid.innerHTML = `<p class="empty-state">No products could be loaded.</p>`;
    }

    skuGrid.querySelectorAll(".sku-card:not([disabled])").forEach((btn) => {
      btn.addEventListener("click", () => previewSku(btn.dataset.sku));
    });
  }

  async function previewSku(sku) {
    const detail = await getJson(`/api/skus/${sku}`, null);
    if (!detail) {
      showBanner("Could not load this product's brief.", "error");
      return;
    }
    const meta = skuList.find((x) => x.sku === sku);
    const refs = (detail.reference_shots || []).filter((r) => r.has_reference);
    const bullets = (detail.marketplace_bullets || [])
      .slice(0, 4)
      .map((b) => `<li>${escapeHtml(b)}</li>`)
      .join("");

    skuBrief.classList.remove("hidden");
    skuBrief.innerHTML = `
      <img src="${escapeHtml(detail.hero_thumbnail_url)}" alt="Hero from Staples Assets" onerror="this.remove()" />
      <div>
        <p class="eyebrow">From Staples Assets · ${escapeHtml((detail.hero_path || "").split("/").slice(-2).join("/"))}</p>
        <h3>${escapeHtml(detail.card_label)}</h3>
        ${detail.headliner ? `<p class="headliner">${escapeHtml(detail.headliner)}</p>` : ""}
        ${
          detail.brand_voice_summary
            ? `<p class="voice"><strong>Brand voice (${escapeHtml(detail.brand_voice_tone || detail.brand_ruleset)}):</strong> ${escapeHtml(detail.brand_voice_summary)}</p>`
            : ""
        }
        ${bullets ? `<ul>${bullets}</ul>` : ""}
        <div class="ref-strip">
          ${refs
            .map(
              (r) => `
            <figure>
              <img src="${escapeHtml(r.reference_url)}" alt="${escapeHtml(r.shot_id)}" />
              <figcaption>${escapeHtml(r.shot_id)}</figcaption>
            </figure>`
            )
            .join("")}
        </div>
        <div class="brief-actions">
          <button type="button" class="primary-btn" id="generate-btn">Generate image stack</button>
          <button type="button" class="ghost-btn" id="dismiss-brief">Dismiss</button>
        </div>
      </div>`;

    document.getElementById("generate-btn").addEventListener("click", () => startJob(sku, meta));
    document.getElementById("dismiss-brief").addEventListener("click", () => {
      skuBrief.classList.add("hidden");
    });
    skuBrief.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function startJob(sku, meta) {
    if (starting) return;
    starting = true;
    try {
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail ?? err.error;
        const message =
          typeof detail === "string"
            ? detail
            : detail?.error || "Could not start job";
        showBanner(message, "error");
        return;
      }
      const data = await res.json();
      currentJobId = data.job_id;
      currentSku = meta;
      landing.classList.add("hidden");
      run.classList.remove("hidden");
      runBrand.textContent =
        meta.brand_ruleset === "coastwide" ? "Coastwide Professional" : "Staples";
      runTitle.textContent = meta.card_label;
      runSub.textContent = `${meta.shot_count} shots · compare against Staples Assets production art`;
      downloadBtn.classList.add("disabled");
      downloadBtn.setAttribute("aria-disabled", "true");
      downloadBtn.removeAttribute("href");
      compareToggle.checked = true;
      showCompare = true;
      shotList.innerHTML = "";
      resultsGrid.innerHTML = "";
      poll();
      pollTimer = setInterval(poll, 1500);
    } finally {
      starting = false;
    }
  }

  async function poll() {
    if (!currentJobId) return;
    const res = await fetch(`/api/jobs/${currentJobId}`);
    if (!res.ok) return;
    const job = await res.json();
    renderJob(job);

    if (["completed", "completed_with_flags", "failed"].includes(job.status)) {
      clearInterval(pollTimer);
      pollTimer = null;
      downloadBtn.classList.remove("disabled");
      downloadBtn.setAttribute("aria-disabled", "false");
      downloadBtn.href = `/api/jobs/${currentJobId}/package`;
    }
  }

  function renderJob(job) {
    const finished = job.counts.done + job.counts.needs_review + job.counts.failed;
    const pct = job.counts.total ? Math.round((finished / job.counts.total) * 100) : 0;
    progressBar.style.width = `${pct}%`;
    progressLabel.textContent = `${finished} / ${job.counts.total} · ${job.status.replaceAll("_", " ")}`;

    shotList.innerHTML = job.shots
      .map((s) => {
        const active = !["done", "needs_review", "failed", "pending"].includes(s.status);
        const thumb = s.thumbnail_url
          ? `<img class="shot-thumb" src="${escapeHtml(s.thumbnail_url)}" alt="" />`
          : `<div class="shot-thumb placeholder">${active ? '<span class="spinner"></span>' : "—"}</div>`;
        const badges = [];
        if (s.is_placeholder) badges.push('<span class="mini ph">placeholder copy</span>');
        if (s.type === "graphic_only" || s.type === "graphic_only_with_generated_tiles") {
          badges.push('<span class="mini">graphic</span>');
        }
        if (s.acceptance_reference_url) badges.push('<span class="mini">has ref</span>');
        if (s.status === "needs_review") {
          badges.push(`<span class="mini" title="${escapeHtml((s.flags || []).join("; "))}">needs review</span>`);
        }
        return `
          <li class="shot-row ${s.status} ${active ? "active" : ""}" title="${escapeHtml((s.flags || []).join("; "))}">
            ${thumb}
            <div>
              <p class="shot-label">${escapeHtml(shortLabel(s.label))}</p>
              <p class="shot-status">${escapeHtml(s.status_label)}</p>
            </div>
            <div class="shot-badges">${badges.join("")}</div>
          </li>`;
      })
      .join("");

    const doneShots = job.shots.filter((s) => s.thumbnail_url);
    resultsGrid.classList.toggle("compare-on", showCompare);
    resultsGrid.innerHTML = doneShots
      .map((s) => {
        const label = escapeHtml(shortLabel(s.label));
        if (showCompare && s.acceptance_reference_url) {
          return `
            <article class="compare-pair">
              <div class="pane">
                <img src="${escapeHtml(s.thumbnail_url)}" alt="${label} generated" />
                <div class="cap">Generated · ${label}</div>
              </div>
              <div class="pane">
                <img src="${escapeHtml(s.acceptance_reference_url)}" alt="${label} Staples Assets reference" />
                <div class="cap ref">Staples Assets reference · ${label}</div>
              </div>
            </article>`;
        }
        if (showCompare && !s.acceptance_reference_url) {
          return `
            <article class="result-card">
              <img src="${escapeHtml(s.thumbnail_url)}" alt="${label}" />
              <div class="cap">${label} · no Staples reference for this shot</div>
            </article>`;
        }
        return `
          <article class="result-card">
            <img src="${escapeHtml(s.thumbnail_url)}" alt="${label}" />
            <div class="cap">${label} · Generated</div>
          </article>`;
      })
      .join("");
  }

  function shortLabel(label) {
    return String(label).replace(/^SKU_\d+\s*-\s*/i, "");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  backBtn.addEventListener("click", () => {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    currentJobId = null;
    run.classList.add("hidden");
    landing.classList.remove("hidden");
  });

  compareToggle.addEventListener("change", () => {
    showCompare = compareToggle.checked;
    if (currentJobId) poll();
  });

  init().catch((err) => {
    console.error(err);
    skuGrid.innerHTML = `<p class="sub">Failed to load products. Is the API running?</p>`;
  });
})();
