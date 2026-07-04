import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
import asyncio

DATA_FILE = "protection_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class ProtectionSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Regex لاكتشاف أي روابط أو دعوات ديسكورد
        self.link_pattern = re.compile(r"(https?://[^\s]+)|(www\.[^\s]+)|(discord\.gg/[^\s]+)", re.IGNORECASE)

    @commands.Cog.listener()
    async def on_ready(self):
        print("🛡️ Protection System Cog is Ready.")

    # ------------------ أوامر السلاش للتحكم بالنظام ------------------ #

    @app_commands.command(name="start_protection", description="تشغيل نظام الحماية وتحديد روم السجلات (اللوق)")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_protection(self, interaction: discord.Interaction, log_channel: discord.TextChannel):
        data = load_data()
        guild_id = str(interaction.guild.id)
        
        data[guild_id] = {
            "enabled": True,
            "log_channel_id": log_channel.id
        }
        save_data(data)

        embed = discord.Embed(
            title="🛡️ تم تفعيل نظام الحماية",
            description=f"تم تفعيل الحماية بنجاح. سيتم إرسال جميع السجلات إلى {log_channel.mention}\n\n**الأنظمة المفعلة:**\n✅ حظر البوتات التي تحذف الرومات\n✅ منع إرسال الروابط\n✅ تسجيل تغييرات الصلاحيات",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stop_protection", description="إيقاف نظام الحماية بالكامل")
    @app_commands.checks.has_permissions(administrator=True)
    async def stop_protection(self, interaction: discord.Interaction):
        data = load_data()
        guild_id = str(interaction.guild.id)
        
        if guild_id in data:
            data[guild_id]["enabled"] = False
            save_data(data)
            await interaction.response.send_message("🛑 **تم إيقاف نظام الحماية بالكامل.**", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ نظام الحماية غير مفعل من الأساس.", ephemeral=True)

    # ------------------ الأحداث (Events) للحماية ------------------ #

    async def get_log_channel(self, guild):
        data = load_data()
        guild_data = data.get(str(guild.id))
        if guild_data and guild_data.get("enabled"):
            channel_id = guild_data.get("log_channel_id")
            return guild.get_channel(channel_id)
        return None

    # 1. منع الروابط
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        data = load_data()
        guild_data = data.get(str(message.guild.id), {})
        
        if not guild_data.get("enabled"):
            return

        # استثناء الإداريين من الحذف
        if message.author.guild_permissions.administrator:
            return

        if self.link_pattern.search(message.content):
            try:
                await message.delete()
                warning = await message.channel.send(f"⚠️ يمنع إرسال الروابط هنا يا {message.author.mention}!")
                await asyncio.sleep(5)
                await warning.delete()
                
                log_channel = await self.get_log_channel(message.guild)
                if log_channel:
                    embed = discord.Embed(title="🔗 نظام منع الروابط", color=discord.Color.orange())
                    embed.add_field(name="العضو", value=message.author.mention, inline=True)
                    embed.add_field(name="الروم", value=message.channel.mention, inline=True)
                    embed.add_field(name="المحتوى الذي تم حذفه", value=f"`{message.content}`", inline=False)
                    await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    # 2. تبنيد البوتات عند حذف الرومات (Anti-Nuke)
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        log_channel = await self.get_log_channel(guild)
        
        if not log_channel: # إذا كانت الحماية مغلقة
            return

        # انتظار ثانية لضمان تحديث الـ Audit Log
        await asyncio.sleep(1)

        # البحث في سجلات السيرفر لمعرفة من قام بالحذف
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                executor = entry.user
                
                # التحقق مما إذا كان المنفذ "بوت" وليس بوتنا نفسه
                if executor.bot and executor.id != self.bot.user.id:
                    try:
                        await guild.ban(executor, reason="Anti-Nuke: قام بحذف روم")
                        
                        embed = discord.Embed(title="🚨 تم تبنيد بوت مخرب (Anti-Nuke)!", color=discord.Color.red())
                        embed.add_field(name="البوت المخرب", value=executor.mention, inline=True)
                        embed.add_field(name="الروم المحذوف", value=f"`{channel.name}`", inline=True)
                        embed.set_footer(text="تم الحظر بنجاح لحماية السيرفر.")
                        
                        await log_channel.send(embed=embed)
                    except discord.Forbidden:
                        embed = discord.Embed(title="⚠️ تنبيه خطير", description=f"قام البوت {executor.mention} بحذف الروم `{channel.name}`.\n\n❌ **لم أتمكن من تبنيده لأن رتبتي أقل منه! يرجى رفع رتبتي للأعلى فوراً!**", color=discord.Color.dark_red())
                        await log_channel.send(embed=embed)
                break

    # 3. تسجيل تغييرات الصلاحيات للرتب
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.permissions == after.permissions:
            return # إذا لم تتغير الصلاحيات (مثل تغيير لون الرتبة فقط) فلا نفعل شيئاً

        guild = after.guild
        log_channel = await self.get_log_channel(guild)
        
        if not log_channel:
            return

        await asyncio.sleep(1)

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
            if entry.target.id == after.id:
                executor = entry.user
                
                embed = discord.Embed(title="⚙️ تعديل في صلاحيات رتبة", color=discord.Color.blue())
                embed.add_field(name="الرتبة", value=after.mention, inline=True)
                embed.add_field(name="المُعدل", value=executor.mention, inline=True)
                
                # لمعرفة ما هي الصلاحيات التي تم تغييرها تحديداً (متقدمة)
                changed_perms = []
                for perm, value in after.permissions:
                    before_value = getattr(before.permissions, perm)
                    if before_value != value:
                        status = "✅ تم تفعيل" if value else "❌ تم إيقاف"
                        changed_perms.append(f"{status}: `{perm}`")
                
                if changed_perms:
                    embed.add_field(name="الصلاحيات المُعدلة", value="\n".join(changed_perms), inline=False)
                
                await log_channel.send(embed=embed)
                break

async def setup(bot):
    await bot.add_cog(ProtectionSystem(bot))