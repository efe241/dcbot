/**
 * PROCHECK v2.0 - FRONTEND APPLICATION SCRIPT
 */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let socket = null;
    let isScraping = false;
    let isChecking = false;
    let results = [];
    let currentFilter = {
        protocol: "all",
        status: "all",
        search: "",
        maxLatency: 10000
    };

    // Settings State
    let settings = {
        concurrency: 150,
        timeout: 5.0,
        targetUrl: "http://httpbin.org/ip"
    };

    // DOM Elements
    const wsStatus = document.getElementById("wsStatus");
    const engineStatus = document.getElementById("engineStatus");

    // Stats
    const statScraped = document.getElementById("statScraped");
    const statChecked = document.getElementById("statChecked");
    const statAlive = document.getElementById("statAlive");
    const statDead = document.getElementById("statDead");
    const statLatency = document.getElementById("statLatency");

    // Progress Bar
    const progressContainer = document.getElementById("progressContainer");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    const progressPercent = document.getElementById("progressPercent");

    // Buttons
    const btnScrape = document.getElementById("btnScrape");
    const btnCheck = document.getElementById("btnCheck");
    const btnStop = document.getElementById("btnStop");
    const btnCustom = document.getElementById("btnCustom");
    const btnSettings = document.getElementById("btnSettings");
    const btnExportToggle = document.getElementById("btnExportToggle");
    const exportMenu = document.getElementById("exportMenu");

    // Filters
    const searchInput = document.getElementById("searchInput");
    const protocolPills = document.getElementById("protocolPills");
    const statusPills = document.getElementById("statusPills");
    const latencySelect = document.getElementById("latencySelect");

    // Table
    const proxyTableBody = document.getElementById("proxyTableBody");
    const resultsCount = document.getElementById("resultsCount");

    // Modals
    const customModal = document.getElementById("customModal");
    const closeCustomModal = document.getElementById("closeCustomModal");
    const cancelCustomModal = document.getElementById("cancelCustomModal");
    const confirmCustomModal = document.getElementById("confirmCustomModal");
    const customProxyText = document.getElementById("customProxyText");

    const settingsModal = document.getElementById("settingsModal");
    const closeSettingsModal = document.getElementById("closeSettingsModal");
    const saveSettingsModal = document.getElementById("saveSettingsModal");
    const settingConcurrency = document.getElementById("settingConcurrency");
    const valConcurrency = document.getElementById("valConcurrency");
    const settingTimeout = document.getElementById("settingTimeout");
    const valTimeout = document.getElementById("valTimeout");
    const settingTargetUrl = document.getElementById("settingTargetUrl");

    // Toast Container
    const toastContainer = document.getElementById("toastContainer");

    // Initialize WebSocket
    initWebSocket();

    function initWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            wsStatus.innerHTML = '<span class="dot green"></span> Sunucu Bağlı';
            showToast("Sunucu ile canlı bağlantı kuruldu", "success");
        };

        socket.onclose = () => {
            wsStatus.innerHTML = '<span class="dot red"></span> Bağlantı Koptu';
            setTimeout(initWebSocket, 3000);
        };

        socket.onerror = (err) => {
            console.error("WS error:", err);
            wsStatus.innerHTML = '<span class="dot red"></span> Bağlantı Hatası';
        };

        socket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWsMessage(msg);
            } catch (e) {
                console.error("JSON parse error:", e);
            }
        };
    }

    function handleWsMessage(msg) {
        const { type, data } = msg;

        switch (type) {
            case "init":
                updateStats(data.stats);
                statScraped.textContent = data.scraped_count || 0;
                if (data.scraped_count > 0 && !data.is_checking) {
                    btnCheck.disabled = false;
                }
                break;

            case "scrape_start":
                isScraping = true;
                setEngineStatus("scrape");
                showProgress("Proxyler internet kaynaklarından çekiliyor...");
                showToast("Proxy kazıma (scrape) işlemi başlatıldı", "info");
                break;

            case "scrape_done":
                isScraping = false;
                setEngineStatus("idle");
                hideProgress();
                statScraped.textContent = data.count;
                btnCheck.disabled = data.count === 0;
                showToast(`${data.count} adet benzersiz proxy çekildi!`, "success");
                break;

            case "check_start":
                isChecking = true;
                results = [];
                renderTable();
                setEngineStatus("check");
                showProgress("Proxyler test ediliyor...", 0);
                showToast("Proxy doğrulama & checkleme başladı", "info");
                break;

            case "check_progress":
                if (data.result) {
                    results.unshift(data.result); // Newest at top
                    updateStats(data.stats);
                    updateProgress(data.stats);
                    renderTable();
                }
                break;

            case "check_done":
                isChecking = false;
                setEngineStatus("idle");
                hideProgress();
                showToast(`Test tamamlandı! ${data.alive_total} çalışan proxy bulundu.`, "success");
                break;

            case "check_stopped":
                isChecking = false;
                setEngineStatus("idle");
                hideProgress();
                showToast("Proxy doğrulama işlemi durduruldu.", "error");
                break;
        }
    }

    // Engine Status Helper
    function setEngineStatus(status) {
        if (status === "scrape") {
            engineStatus.innerHTML = '<span class="dot yellow"></span> Proxyler Çekiliyor...';
            btnScrape.disabled = true;
            btnCheck.disabled = true;
            btnStop.style.display = "none";
        } else if (status === "check") {
            engineStatus.innerHTML = '<span class="dot green"></span> Test Yapılıyor...';
            btnScrape.disabled = true;
            btnCheck.disabled = true;
            btnStop.style.display = "inline-flex";
        } else {
            engineStatus.innerHTML = '<span class="dot grey"></span> Hazır';
            btnScrape.disabled = false;
            btnCheck.disabled = parseInt(statScraped.textContent) === 0 && results.length === 0;
            btnStop.style.display = "none";
        }
    }

    // Update Stats UI
    function updateStats(stats) {
        if (!stats) return;
        statScraped.textContent = stats.total_scraped || 0;
        statChecked.textContent = stats.total_checked || 0;
        statAlive.textContent = stats.alive_count || 0;
        statDead.textContent = stats.dead_count || 0;
        statLatency.innerHTML = `${stats.avg_latency || 0} <small>ms</small>`;
    }

    function updateProgress(stats) {
        if (!stats || !stats.total_scraped) return;
        const percent = Math.min(100, Math.round((stats.total_checked / stats.total_scraped) * 100));
        progressBar.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        progressText.textContent = `Test ediliyor: ${stats.total_checked} / ${stats.total_scraped}`;
    }

    function showProgress(text, percent = 0) {
        progressContainer.style.display = "block";
        progressBar.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        progressText.textContent = text;
    }

    function hideProgress() {
        progressContainer.style.display = "none";
    }

    // Table Rendering
    function renderTable() {
        const filtered = results.filter(r => {
            // Search
            if (currentFilter.search) {
                const s = currentFilter.search.toLowerCase();
                const matchIp = r.proxy.toLowerCase().includes(s);
                const matchAnon = (r.anonymity || "").toLowerCase().includes(s);
                if (!matchIp && !matchAnon) return false;
            }
            // Protocol
            if (currentFilter.protocol !== "all") {
                if ((r.protocol || "http").toLowerCase() !== currentFilter.protocol) return false;
            }
            // Status
            if (currentFilter.status === "alive" && !r.alive) return false;
            if (currentFilter.status === "dead" && r.alive) return false;
            // Latency
            if (currentFilter.maxLatency < 10000) {
                if (!r.latency || r.latency > currentFilter.maxLatency) return false;
            }
            return true;
        });

        resultsCount.textContent = filtered.length;

        if (filtered.length === 0) {
            proxyTableBody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="8">
                        <div class="empty-state">
                            <i class="fa-solid fa-filter"></i>
                            <p>Kriterlere uygun proxy sonucu bulunamadı.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        const rows = filtered.slice(0, 200).map((item, index) => {
            const protoClass = (item.protocol || "http").toLowerCase();
            let latencyClass = "latency-slow";
            if (item.latency < 300) latencyClass = "latency-fast";
            else if (item.latency < 700) latencyClass = "latency-med";

            const statusBadge = item.alive
                ? '<span class="badge-status alive"><i class="fa-solid fa-check"></i> Çalışıyor</span>'
                : '<span class="badge-status dead"><i class="fa-solid fa-xmark"></i> Ölü</span>';

            const latencyDisplay = item.alive && item.latency !== null
                ? `<span class="latency-val ${latencyClass}">${item.latency} ms</span>`
                : '<span style="color: var(--text-dim);">-</span>';

            return `
                <tr>
                    <td>${index + 1}</td>
                    <td class="proxy-ip">${item.ip}</td>
                    <td class="proxy-ip">${item.port}</td>
                    <td><span class="badge-proto ${protoClass}">${item.protocol || 'HTTP'}</span></td>
                    <td>${latencyDisplay}</td>
                    <td>${item.anonymity || 'Unknown'}</td>
                    <td>${statusBadge}</td>
                    <td style="text-align: right;">
                        <button class="btn btn-secondary btn-sm" onclick="copyText('${item.proxy}')" title="Kopyala">
                            <i class="fa-solid fa-copy"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        proxyTableBody.innerHTML = rows.join("");
    }

    // Global copy function
    window.copyText = (text) => {
        navigator.clipboard.writeText(text);
        showToast(`Kopyalandı: ${text}`, "success");
    };

    // Event Handlers
    btnScrape.addEventListener("click", async () => {
        try {
            const resp = await fetch("/api/scrape", { method: "POST" });
            const data = await resp.json();
            if (data.status !== "started") {
                showToast(data.message || "Hata oluştu", "error");
            }
        } catch (e) {
            showToast("Bağlantı hatası!", "error");
        }
    });

    btnCheck.addEventListener("click", async () => {
        try {
            const resp = await fetch("/api/check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    concurrency: settings.concurrency,
                    timeout: settings.timeout,
                    target_url: settings.targetUrl
                })
            });
            const data = await resp.json();
            if (data.status !== "started") {
                showToast(data.message || "Hata oluştu", "error");
            }
        } catch (e) {
            showToast("Bağlantı hatası!", "error");
        }
    });

    btnStop.addEventListener("click", async () => {
        await fetch("/api/stop", { method: "POST" });
    });

    // Custom Modal
    btnCustom.addEventListener("click", () => customModal.classList.add("show"));
    closeCustomModal.addEventListener("click", () => customModal.classList.remove("show"));
    cancelCustomModal.addEventListener("click", () => customModal.classList.remove("show"));

    confirmCustomModal.addEventListener("click", async () => {
        const text = customProxyText.value.trim();
        if (!text) {
            showToast("Lütfen proxy listesi girin!", "error");
            return;
        }
        const lines = text.split("\n");
        customModal.classList.remove("show");

        try {
            const resp = await fetch("/api/check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    concurrency: settings.concurrency,
                    timeout: settings.timeout,
                    target_url: settings.targetUrl,
                    custom_proxies: lines
                })
            });
            const data = await resp.json();
            if (data.status === "started") {
                showToast(`${lines.length} adet özel proxy yüklendi ve test başlatıldı`, "success");
            }
        } catch (e) {
            showToast("Özel proxy yüklenemedi", "error");
        }
    });

    // Settings Modal
    btnSettings.addEventListener("click", () => settingsModal.classList.add("show"));
    closeSettingsModal.addEventListener("click", () => settingsModal.classList.remove("show"));
    
    settingConcurrency.addEventListener("input", (e) => {
        valConcurrency.textContent = `${e.target.value} Thread`;
    });
    settingTimeout.addEventListener("input", (e) => {
        valTimeout.textContent = `${e.target.value}s`;
    });

    saveSettingsModal.addEventListener("click", () => {
        settings.concurrency = parseInt(settingConcurrency.value);
        settings.timeout = parseFloat(settingTimeout.value);
        settings.targetUrl = settingTargetUrl.value.trim() || "http://httpbin.org/ip";
        settingsModal.classList.remove("show");
        showToast("Ayarlar kaydedildi!", "success");
    });

    // Export Dropdown Toggle
    btnExportToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        exportMenu.classList.toggle("show");
    });
    document.addEventListener("click", () => exportMenu.classList.remove("show"));

    document.getElementById("exportTxt").addEventListener("click", () => window.location.href = "/api/export?format_type=txt");
    document.getElementById("exportJson").addEventListener("click", () => window.location.href = "/api/export?format_type=json");
    document.getElementById("exportCsv").addEventListener("click", () => window.location.href = "/api/export?format_type=csv");

    document.getElementById("copyAlive").addEventListener("click", async () => {
        const aliveProxies = results.filter(r => r.alive).map(r => r.proxy).join("\n");
        if (!aliveProxies) {
            showToast("Çalışan proxy bulunmuyor", "error");
            return;
        }
        await navigator.clipboard.writeText(aliveProxies);
        showToast("Tüm çalışan proxyler panoya kopyalandı!", "success");
    });

    // Filters
    searchInput.addEventListener("input", (e) => {
        currentFilter.search = e.target.value.trim();
        renderTable();
    });

    protocolPills.querySelectorAll(".pill").forEach(pill => {
        pill.addEventListener("click", () => {
            protocolPills.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentFilter.protocol = pill.dataset.protocol;
            renderTable();
        });
    });

    statusPills.querySelectorAll(".pill").forEach(pill => {
        pill.addEventListener("click", () => {
            statusPills.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentFilter.status = pill.dataset.status;
            renderTable();
        });
    });

    latencySelect.addEventListener("change", (e) => {
        currentFilter.maxLatency = parseInt(e.target.value);
        renderTable();
    });

    // Toast Notification Helper
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-circle-xmark";

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(50px)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
});
