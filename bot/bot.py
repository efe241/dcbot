import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import logging
import asyncio
from decimal import Decimal

# Add root project path to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models.user import User
from backend.models.ledger import CoinLedger
from backend.models.transaction import CPXTransaction
from backend.models.reward_item import RewardItem
from backend.services.reward_service import RewardService
from sqlalchemy import select, func, desc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord_bot")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class TasksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        web_url = f"{settings.BASE_URL}/tasks"
        self.add_item(discord.ui.Button(label="🎯 Görevler ve Anketler", url=web_url, style=discord.ButtonStyle.link))

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

# --- USER COMMANDS ---

@bot.tree.command(name="balance", description="Mevcut Coin bakiyenizi görüntüleyin.")
async def balance_cmd(interaction: discord.Interaction):
    discord_id = str(interaction.user.id)
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.discord_id == discord_id)
        user = (await db.execute(stmt)).scalar_one_or_none()
        balance = float(user.coin_balance) if user else 0.0

    embed = discord.Embed(
        title="💰 Bakiye Bilgisi",
        description=f"Merhaba **{interaction.user.display_name}**,\n\nMevcut Bakiyeniz: **{balance:,.2f} Coins**",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Coinler sanal puandır. Gerçek para değildir ve nakde çevrilemez.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="bakiye", description="Mevcut Coin bakiyenizi görüntüleyin.")
async def bakiye_cmd(interaction: discord.Interaction):
    await balance_cmd(interaction)

@bot.tree.command(name="tasks", description="Görevler sayfasına gidin ve CPX anketleriyle Coin kazanın.")
async def tasks_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎯 CPX Research Görev Salonu",
        description=(
            "Aşağıdaki butona tıklayarak web platformuna erişebilir, "
            "izin verilen CPX Research anketlerini tamamlayarak sanal **Coin** kazanabilirsiniz!\n\n"
            "⚠️ **Önemli Kurallar:**\n"
            "• Coinler platform içi sanal ödüllerdir.\n"
            "• Gerçek para ödemesi veya nakit çekim imkanı yoktur.\n"
            "• Bot/Proxy/VPN kullanımı ve sahte işlemler otomatik iptal edilir."
        ),
        color=discord.Color.purple()
    )
    view = TasksView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="gorevler", description="Görevler sayfasına gidin ve CPX anketleriyle Coin kazanın.")
async def gorevler_cmd(interaction: discord.Interaction):
    await tasks_cmd(interaction)

@bot.tree.command(name="rewards", description="Coinlerinizi harcayabileceğiniz dijital ödülleri görün.")
async def rewards_cmd(interaction: discord.Interaction):
    async with AsyncSessionLocal() as db:
        stmt = select(RewardItem).where(RewardItem.is_active == True)
        items = (await db.execute(stmt)).scalars().all()

    embed = discord.Embed(
        title="🎁 Ödül Mağazası",
        description="Kazandığınız Coinler ile aşağıdaki sunucu içi dijital ödülleri alabilirsiniz:",
        color=discord.Color.blue()
    )

    if items:
        for item in items:
            embed.add_field(
                name=f"{item.icon_emoji} {item.name} — {float(item.coin_price):,.0f} Coins",
                value=f"{item.description or 'Sunucu içi dijital ödül'}",
                inline=False
            )
    else:
        embed.description += "\n\n*Henüz aktif bir ödül bulunmuyor.*"

    embed.set_footer(text="Ödülleri web uygulamasındaki mağazadan veya admin yetkilileri üzerinden talep edebilirsiniz.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="magaza", description="Coinlerinizi harcayabileceğiniz dijital ödülleri görün.")
async def magaza_cmd(interaction: discord.Interaction):
    await rewards_cmd(interaction)

@bot.tree.command(name="leaderboard", description="En çok Coin kazanan kullanıcılar sıralaması.")
async def leaderboard_cmd(interaction: discord.Interaction):
    async with AsyncSessionLocal() as db:
        stmt = select(User).order_by(desc(User.coin_balance)).limit(10)
        users = (await db.execute(stmt)).scalars().all()

    embed = discord.Embed(
        title="🏆 Coin Liderlik Tablosu",
        color=discord.Color.gold()
    )

    desc_lines = []
    medals = ["🥇", "🥈", "🥉"]
    for idx, u in enumerate(users):
        prefix = medals[idx] if idx < 3 else f"#{idx+1}"
        desc_lines.append(f"{prefix} **{u.discord_username}** — {float(u.coin_balance):,.2f} Coins")

    embed.description = "\n".join(desc_lines) if desc_lines else "Henüz kimse Coin kazanmadı."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="liderlik", description="En çok Coin kazanan kullanıcılar sıralaması.")
async def liderlik_cmd(interaction: discord.Interaction):
    await leaderboard_cmd(interaction)

@bot.tree.command(name="history", description="Son Coin işlem geçmişinizi görüntüleyin.")
async def history_cmd(interaction: discord.Interaction):
    discord_id = str(interaction.user.id)
    async with AsyncSessionLocal() as db:
        stmt = select(CoinLedger).where(
            CoinLedger.discord_user_id == discord_id
        ).order_by(desc(CoinLedger.created_at)).limit(10)
        records = (await db.execute(stmt)).scalars().all()

    embed = discord.Embed(
        title="📜 İşlem Geçmişi",
        color=discord.Color.dark_teal()
    )

    if records:
        lines = []
        for r in records:
            sign = "+" if r.amount > 0 else ""
            lines.append(f"• `{sign}{float(r.amount):,.2f} Coins` | **{r.type}** — {r.description}")
        embed.description = "\n".join(lines)
    else:
        embed.description = "Henüz kaydolmuş bir Coin işleminiz bulunmuyor."

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="gecmis", description="Son Coin işlem geçmişinizi görüntüleyin.")
async def gecmis_cmd(interaction: discord.Interaction):
    await history_cmd(interaction)

@bot.tree.command(name="help", description="Sistem ve kurallar hakkında bilgi alın.")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❓ Yardım & Sistem Kuralları",
        description=(
            "**Coin Nedir?**\n"
            "Discord sunucumuzda izin verilen CPX Research anketlerini tamamlayarak kazandığınız sanal puandır.\n\n"
            "**Kurallar:**\n"
            "1️⃣ Coinler kesinlikle gerçek para değildir, nakit çekilemez.\n"
            "2️⃣ Sahte anket tamamlama, bot, proxy veya VPN tespiti durumunda Coinler iptal edilir.\n"
            "3️⃣ Tek bir kullanıcı birden fazla Discord hesabı ile işlem yapamaz.\n\n"
            "**Komutlar:**\n"
            "• `/bakiye` veya `/balance` — Bakiyeni gör\n"
            "• `/gorevler` veya `/tasks` — Görev salonuna git\n"
            "• `/magaza` veya `/rewards` — Ödül mağazası\n"
            "• `/liderlik` veya `/leaderboard` — Liderlik tablosu\n"
            "• `/gecmis` veya `/history` — Son işlemlerin"
        ),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="yardim", description="Sistem ve kurallar hakkında bilgi alın.")
async def yardim_cmd(interaction: discord.Interaction):
    await help_cmd(interaction)

# --- ADMIN COMMANDS ---

@bot.tree.command(name="addcoins", description="[ADMIN] Belirtilen kullanıcıya Coin ekler.")
@app_commands.describe(user="Hedef kullanıcı", amount="Eklenecek miktar")
async def addcoins_cmd(interaction: discord.Interaction, user: discord.User, amount: float):
    if not (str(interaction.user.id) in settings.admin_ids_list or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)
        return

    async with AsyncSessionLocal() as db:
        success, msg, new_bal = await RewardService.admin_adjust_coins(
            db, str(user.id), Decimal(str(amount)), True, str(interaction.user.id), "Discord command addition"
        )

    await interaction.response.send_message(
        f"✅ **{user.display_name}** kullanıcısına **{amount:,.2f} Coins** eklendi! Yeni Bakiye: **{float(new_bal):,.2f} Coins**",
        ephemeral=True
    )

@bot.tree.command(name="removecoins", description="[ADMIN] Belirtilen kullanıcıdan Coin düşer.")
@app_commands.describe(user="Hedef kullanıcı", amount="Düşülecek miktar")
async def removecoins_cmd(interaction: discord.Interaction, user: discord.User, amount: float):
    if not (str(interaction.user.id) in settings.admin_ids_list or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)
        return

    async with AsyncSessionLocal() as db:
        success, msg, new_bal = await RewardService.admin_adjust_coins(
            db, str(user.id), Decimal(str(amount)), False, str(interaction.user.id), "Discord command removal"
        )

    await interaction.response.send_message(
        f"🔻 **{user.display_name}** kullanıcısından **{amount:,.2f} Coins** düşüldü! Yeni Bakiye: **{float(new_bal):,.2f} Coins**",
        ephemeral=True
    )

@bot.tree.command(name="stats", description="[ADMIN] Sistem istatistiklerini gösterir.")
async def stats_cmd(interaction: discord.Interaction):
    if not (str(interaction.user.id) in settings.admin_ids_list or interaction.user.guild_permissions.administrator):
        await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yok.", ephemeral=True)
        return

    async with AsyncSessionLocal() as db:
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        completed_surveys = (await db.execute(select(func.count(CPXTransaction.id)).where(CPXTransaction.status == 1))).scalar() or 0
        reversals = (await db.execute(select(func.count(CPXTransaction.id)).where(CPXTransaction.status == 2))).scalar() or 0
        revenue = (await db.execute(select(func.sum(CPXTransaction.amount_usd)).where(CPXTransaction.status == 1))).scalar() or Decimal("0.00")

    embed = discord.Embed(
        title="📊 Sistem Genel İstatistikleri",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name="Toplam Kullanıcı", value=f"{total_users:,}", inline=True)
    embed.add_field(name="Tamamlanan Anket", value=f"{completed_surveys:,}", inline=True)
    embed.add_field(name="İptal/Reversal", value=f"{reversals:,}", inline=True)
    embed.add_field(name="Toplam CPX Geliri", value=f"${float(revenue):,.2f} USD", inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

def main():
    token = settings.DISCORD_BOT_TOKEN
    if not token or token == "mock_bot_token":
        raise RuntimeError("DISCORD_BOT_TOKEN is missing or not configured in environment variables!")
    bot.run(token)

if __name__ == "__main__":
    main()
