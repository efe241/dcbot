document.addEventListener("DOMContentLoaded", () => {
    checkAdminAuth();
    document.getElementById("coin-adjust-form").addEventListener("submit", handleCoinAdjustment);
});

async function checkAdminAuth() {
    try {
        const res = await fetch("/api/admin/stats");
        if (res.ok) {
            document.getElementById("admin-auth-modal").style.display = "none";
            document.getElementById("admin-dashboard-container").style.display = "block";
            loadAdminStats();
            loadPostbackLogs();
            loadUsers();
        } else {
            document.getElementById("admin-auth-modal").style.display = "flex";
            document.getElementById("admin-dashboard-container").style.display = "none";
        }
    } catch (err) {
        document.getElementById("admin-auth-modal").style.display = "flex";
        document.getElementById("admin-dashboard-container").style.display = "none";
    }
}

async function submitAdminLogin(e) {
    e.preventDefault();
    const errorDiv = document.getElementById("admin-login-error");
    const password = document.getElementById("admin-password-input").value.trim();

    errorDiv.style.display = "none";

    try {
        const res = await fetch("/api/admin/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password })
        });

        const data = await res.json();
        if (res.ok) {
            document.getElementById("admin-auth-modal").style.display = "none";
            document.getElementById("admin-dashboard-container").style.display = "block";
            loadAdminStats();
            loadPostbackLogs();
            loadUsers();
        } else {
            errorDiv.innerText = "❌ " + (data.detail || "Geçersiz şifre!");
            errorDiv.style.display = "block";
        }
    } catch (err) {
        errorDiv.innerText = "❌ Bağlantı hatası: " + err;
        errorDiv.style.display = "block";
    }
}

async function loadAdminStats() {
    try {
        const res = await fetch("/api/admin/stats");
        if (!res.ok) {
            checkAdminAuth();
            return;
        }
        const data = await res.json();

        document.getElementById("stat-total-rev").innerText = `$${data.total_revenue_usd.toLocaleString("en-US", {minimumFractionDigits: 2})}`;
        document.getElementById("stat-rev-user").innerText = `$${data.revenue_per_user.toFixed(4)}`;
        document.getElementById("stat-rev-survey").innerText = `$${data.revenue_per_survey.toFixed(4)}`;
        document.getElementById("stat-surveys").innerText = `${data.completed_surveys.toLocaleString()}`;
        document.getElementById("stat-users").innerText = `${data.total_users} / ${data.active_users}`;
        document.getElementById("stat-coins-issued").innerText = `${data.coins_distributed.toLocaleString()} Coins`;
        document.getElementById("stat-coins-spent").innerText = `${data.coins_spent.toLocaleString()} Coins`;
        document.getElementById("stat-completion-rate").innerText = `${data.completion_rate_pct}% (${data.reversals_count} Reversal)`;

    } catch (err) {
        console.error("Load admin stats failed:", err);
    }
}

async function loadPostbackLogs() {
    const tbody = document.getElementById("postback-logs-table");
    try {
        const res = await fetch("/api/admin/postback-logs");
        if (!res.ok) return;
        const logs = await res.json();

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">Postback kaydı bulunamadı.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => {
            const hashBadge = l.hash_valid ? `<span class="badge badge-success">Geçerli</span>` : `<span class="badge badge-danger">GEÇERSİZ</span>`;
            const ipBadge = l.ip_whitelisted ? `<span class="badge badge-success">Whitelisted</span>` : `<span class="badge badge-danger">REJECTED</span>`;
            const statusBadge = l.processed ? `<span class="badge badge-success">İşlendi</span>` : `<span class="badge badge-danger">Reddedildi</span>`;
            const dateStr = l.created_at ? new Date(l.created_at).toLocaleString("tr-TR") : "-";

            return `
                <tr>
                    <td style="font-size: 0.8rem; color: var(--text-muted);">${dateStr}</td>
                    <td style="font-family: monospace;">${escapeHtml(l.ip_address || '-')}</td>
                    <td style="font-family: monospace; font-size: 0.85rem;">${escapeHtml(l.trans_id || '-')}</td>
                    <td style="font-family: monospace;">${escapeHtml(l.user_id || '-')}</td>
                    <td><span class="badge ${l.status === 1 ? 'badge-success' : 'badge-warning'}">Status ${l.status}</span></td>
                    <td style="font-weight: 700; color: var(--accent-gold);">$${l.amount_usd.toFixed(4)}</td>
                    <td>${hashBadge}</td>
                    <td>${ipBadge}</td>
                    <td>${statusBadge} ${l.error_message ? `<span style="font-size: 0.75rem; color: var(--accent-red); display: block;">${escapeHtml(l.error_message)}</span>` : ''}</td>
                </tr>
            `;
        }).join("");

    } catch (err) {
        console.error("Load logs failed:", err);
    }
}

async function loadUsers() {
    const tbody = document.getElementById("users-table");
    try {
        const res = await fetch("/api/admin/users");
        if (!res.ok) return;
        const users = await res.json();

        tbody.innerHTML = users.map(u => {
            let riskBadge = `<span class="badge badge-success">Normal (${u.risk_score})</span>`;
            if (u.risk_score > 60) {
                riskBadge = `<span class="badge badge-danger">Yüksek Risk (${u.risk_score})</span>`;
            } else if (u.risk_score > 30) {
                riskBadge = `<span class="badge badge-warning">İnceleme (${u.risk_score})</span>`;
            }

            const dateStr = u.created_at ? new Date(u.created_at).toLocaleDateString("tr-TR") : "-";

            return `
                <tr>
                    <td style="font-family: monospace;">${escapeHtml(u.discord_id)}</td>
                    <td style="font-weight: 600;">${escapeHtml(u.discord_username)}</td>
                    <td style="font-weight: 700; color: var(--accent-gold);">${u.coin_balance.toLocaleString("en-US", {minimumFractionDigits: 2})} Coins</td>
                    <td>${riskBadge}</td>
                    <td>${u.is_banned ? '<span class="badge badge-danger">Banned</span>' : '<span class="badge badge-success">Active</span>'}</td>
                    <td>${dateStr}</td>
                </tr>
            `;
        }).join("");

    } catch (err) {
        console.error("Load users failed:", err);
    }
}

async function handleCoinAdjustment(e) {
    e.preventDefault();

    const discord_id = document.getElementById("target-user-id").value.trim();
    const amount = parseFloat(document.getElementById("adjust-amount").value);
    const action = document.getElementById("adjust-action").value;
    const reason = document.getElementById("adjust-reason").value.trim();

    try {
        const res = await fetch("/api/admin/adjust-coins", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ discord_id, amount, action, reason })
        });

        const data = await res.json();
        if (res.ok) {
            alert(`✅ Başarılı: ${data.message} | Yeni Bakiye: ${data.new_balance.toLocaleString()} Coins`);
            document.getElementById("coin-adjust-form").reset();
            loadAdminStats();
            loadUsers();
        } else {
            alert(`❌ Hata: ${data.detail || "İşlem başarısız."}`);
        }
    } catch (err) {
        alert("Coin ayar hatası: " + err);
    }
}

function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, match => {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[match];
    });
}
