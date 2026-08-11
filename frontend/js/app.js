const API_BASE = (window.location.hostname.includes("web.app") || window.location.hostname.includes("firebaseapp.com"))
    ? "https://surveytr.vercel.app"
    : "";

let currentUser = null;
let selectedRewardId = null;

document.addEventListener("DOMContentLoaded", () => {
    if (API_BASE) {
        document.querySelectorAll('a[href^="/api/auth/login"]').forEach(a => {
            a.href = `${API_BASE}/api/auth/login`;
        });
    }
    initApp();
});

async function initApp() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`, { credentials: "include" });
        if (res.ok) {
            currentUser = await res.json();
            renderUserHeader();
            loadCPXWall();
            loadAdGemWall();
            loadRewards();
            loadHistory();
        } else {
            showUnauthenticatedState();
        }
    } catch (err) {
        console.error("Auth check failed:", err);
        showUnauthenticatedState();
    }
}

async function loadAdGemWall() {
    const container = document.getElementById("adgem-offerwall-container");
    if (!currentUser) return;

    try {
        const res = await fetch(`${API_BASE}/api/adgem/script-config`, { credentials: "include" });
        if (!res.ok) {
            container.innerHTML = `<div style="padding: 2rem; color: var(--accent-red);">AdGem Yapılandırması Yüklenemedi.</div>`;
            return;
        }

        const config = await res.json();
        
        container.innerHTML = `
            <iframe src="${config.iframe_url}" 
                    style="width: 100%; height: 750px; border: none; border-radius: var(--radius-md);" 
                    allow="geolocation" 
                    title="AdGem Offerwall">
            </iframe>
        `;

    } catch (err) {
        console.error("AdGem Wall error:", err);
        container.innerHTML = `<div style="padding: 2rem; color: var(--accent-red);">AdGem duvarı yüklenirken hata oluştu.</div>`;
    }
}

function showUnauthenticatedState() {
    document.getElementById("user-name").innerText = "Giriş Yapılmadı";
    document.getElementById("user-discord-id").innerText = "Yok";
    document.getElementById("mock-login-banner").style.display = "block";
    document.getElementById("cpx-loading-text").innerHTML = `
        Görüntülemek için lütfen <a href="https://surveytr.vercel.app/api/auth/login" class="btn btn-discord" style="padding: 0.4rem 1rem; margin: 0 0.5rem;">Discord ile Giriş Yapın</a> veya yukarıdaki test modunu kullanın.
    `;
}

function renderUserHeader() {
    document.getElementById("mock-login-banner").style.display = "none";
    document.getElementById("user-name").innerText = currentUser.discord_username;
    document.getElementById("user-discord-id").innerText = currentUser.discord_id;
    
    const formattedBalance = currentUser.coin_balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    document.getElementById("user-balance-badge").innerText = formattedBalance;
    document.getElementById("profile-balance").innerText = `${formattedBalance} Coins`;
    document.getElementById("logout-btn").style.display = "inline-flex";

    if (currentUser.is_admin) {
        document.getElementById("admin-link-btn").style.display = "inline-flex";
    }

    if (currentUser.discord_avatar) {
        const avatarUrl = `https://cdn.discordapp.com/avatars/${currentUser.discord_id}/${currentUser.discord_avatar}.png`;
        document.getElementById("user-avatar").innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;" alt="Avatar" />`;
    }

    const badgeEl = document.getElementById("risk-badge");
    if (currentUser.is_banned) {
        badgeEl.className = "badge badge-danger";
        badgeEl.innerText = "Yasaklı";
    } else if (currentUser.risk_score > 60) {
        badgeEl.className = "badge badge-warning";
        badgeEl.innerText = "İncelemede";
    } else {
        badgeEl.className = "badge badge-success";
        badgeEl.innerText = "Doğrulanmış";
    }
}

async function quickMockLogin(discordId, username) {
    try {
        const res = await fetch(`${API_BASE}/api/auth/mock-login?discord_id=${discordId}&username=${username}`, { method: "POST", credentials: "include" });
        if (res.ok) {
            window.location.reload();
        }
    } catch (err) {
        alert("Mock login failed: " + err);
    }
}

async function logout() {
    await fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
    window.location.reload();
}

function switchTab(tabId, btnEl) {
    document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
    
    document.getElementById(tabId).style.display = "block";
    btnEl.classList.add("active");
}

async function loadCPXWall() {
    const container = document.getElementById("cpx-surveywall-container");
    if (!currentUser) return;

    try {
        const res = await fetch(`${API_BASE}/api/cpx/script-config`, { credentials: "include" });
        if (!res.ok) {
            container.innerHTML = `<div style="padding: 2rem; color: var(--accent-red);">CPX Yapılandırması Yüklenemedi.</div>`;
            return;
        }

        const config = await res.json();
        
        // Construct standard CPX iframe URL
        const iframeUrl = `https://offers.cpx-research.com/index.php?app_id=${encodeURIComponent(config.app_id)}&ext_user_id=${encodeURIComponent(config.ext_user_id)}&secure_hash=${encodeURIComponent(config.secure_hash)}&username=${encodeURIComponent(config.username)}&email=${encodeURIComponent(config.email)}`;

        container.innerHTML = `
            <iframe src="${iframeUrl}" 
                    style="width: 100%; height: 750px; border: none; border-radius: var(--radius-md);" 
                    allow="geolocation" 
                    title="CPX Research SurveyWall">
            </iframe>
        `;

    } catch (err) {
        console.error("CPX Wall error:", err);
        container.innerHTML = `<div style="padding: 2rem; color: var(--accent-red);">Anket yüklenirken hata oluştu.</div>`;
    }
}

async function loadRewards() {
    const grid = document.getElementById("rewards-grid");
    try {
        const res = await fetch(`${API_BASE}/api/rewards/items`);
        if (!res.ok) return;
        const items = await res.json();

        grid.innerHTML = items.map(item => `
            <div class="reward-card">
                <div>
                    <div class="reward-header">
                        <div class="reward-icon">${item.icon_emoji}</div>
                        <div>
                            <div class="reward-title">${escapeHtml(item.name)}</div>
                            <span class="badge badge-warning" style="margin-top: 0.2rem;">${item.reward_type}</span>
                        </div>
                    </div>
                    <div class="reward-desc">${escapeHtml(item.description || '')}</div>
                </div>
                <div class="reward-footer">
                    <div class="reward-price">${item.coin_price.toLocaleString("en-US")} Coins</div>
                    <button class="btn btn-primary" onclick="openPurchaseModal(${item.id}, '${escapeHtml(item.name)}', ${item.coin_price})">
                        Satın Al
                    </button>
                </div>
            </div>
        `).join("");

    } catch (err) {
        console.error("Load rewards failed:", err);
    }
}

async function loadHistory() {
    const tbody = document.getElementById("history-table-body");
    if (!currentUser) return;

    try {
        const res = await fetch(`${API_BASE}/api/users/me/history`, { credentials: "include" });
        if (!res.ok) return;
        const history = await res.json();

        if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Henüz bir işlem kaydı yok.</td></tr>`;
            return;
        }

        tbody.innerHTML = history.map(item => {
            const isCredit = item.amount > 0;
            const badgeClass = isCredit ? "badge-success" : "badge-danger";
            const sign = isCredit ? "+" : "";
            const dateStr = item.created_at ? new Date(item.created_at).toLocaleString("tr-TR") : "-";

            return `
                <tr>
                    <td>${dateStr}</td>
                    <td><span class="badge ${badgeClass}">${escapeHtml(item.type)}</span></td>
                    <td>${escapeHtml(item.description || '-')}</td>
                    <td style="font-family: monospace; font-size: 0.85rem; color: var(--text-muted);">${escapeHtml(item.reference_id || '-')}</td>
                    <td style="font-weight: 700; color: ${isCredit ? 'var(--accent-green)' : 'var(--accent-red)'};">
                        ${sign}${item.amount.toLocaleString("en-US", {minimumFractionDigits: 2})} Coins
                    </td>
                </tr>
            `;
        }).join("");

    } catch (err) {
        console.error("Load history failed:", err);
    }
}

function openPurchaseModal(id, name, price) {
    if (!currentUser) {
        alert("Lütfen önce giriş yapın.");
        return;
    }
    selectedRewardId = id;
    document.getElementById("modal-title").innerText = `Ödül Satın Al: ${name}`;
    document.getElementById("modal-desc").innerText = `Bu ödülü almak için hesabınızdan ${price.toLocaleString("en-US")} Coins düşülecektir. Onaylıyor musunuz?`;
    document.getElementById("purchase-modal").classList.add("active");
}

function closeModal() {
    selectedRewardId = null;
    document.getElementById("purchase-modal").classList.remove("active");
}

async function confirmPurchase() {
    if (!selectedRewardId) return;

    try {
        const res = await fetch(`${API_BASE}/api/rewards/purchase`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ item_id: selectedRewardId })
        });

        const data = await res.json();
        closeModal();

        if (res.ok) {
            alert(`🎉 Tebrikler! ${data.message}`);
            window.location.reload();
        } else {
            alert(`❌ Hata: ${data.detail || "Satın alma gerçekleştirilemedi."}`);
        }
    } catch (err) {
        alert("Satın alma hatası: " + err);
    }
}

function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, match => {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[match];
    });
}
