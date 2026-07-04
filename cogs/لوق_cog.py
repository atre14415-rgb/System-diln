import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime

# ملف حفظ الإعدادات
DATA_FILE = "log_channels.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class LogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # كاش للدعوات لتتبع رابح الدعوة عند دخول الأعضاء
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
            except discord.Forbidden:
                pass

    # دالة جلب روم اللوق المخصص
    async def get_log_channel(self, guild_id, log_type):
        data = load_data()
        guild_data = data.get(str(guild_id), {})
        channel_id = guild_data.get(log_type)
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    # دالة ذكية ومحدثة لجلب الإداري (المنفذ) من الـ Audit Logs لمنع التداخل
    async def get_executor(self, guild, action, target_id=None, delay=7):
        try:
            async for entry in guild.audit_logs(action=action, limit=5):
                # التحقق أن الحدث حصل في غضون ثوانٍ بسيطة لتجنب جلب القديم
                if (discord.utils.utcnow() - entry.created_at).total_seconds() < delay:
                    if target_id and entry.target.id != target_id:
                        continue
                    return entry.user
        except discord.Forbidden:
            return None
        return None

    # ==========================================
    # أمر إعداد وتسطيب الرومات (Slash Command)
    # ==========================================
    @app_commands.command(name="setup_logs", description="تسطيب وتحديد رومات نظام اللوق")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_logs(self, interaction: discord.Interaction, 
                         msg_log: discord.TextChannel = None,
                         role_log: discord.TextChannel = None,
                         channel_log: discord.TextChannel = None,
                         member_log: discord.TextChannel = None,
                         mod_log: discord.TextChannel = None,
                         reaction_log: discord.TextChannel = None,
                         invite_log: discord.TextChannel = None,
                         voice_log: discord.TextChannel = None):
        
        data = load_data()
        guild_id = str(interaction.guild.id)
        if guild_id not in data:
            data[guild_id] = {}

        if msg_log: data[guild_id]["msg_log"] = msg_log.id
        if role_log: data[guild_id]["role_log"] = role_log.id
        if channel_log: data[guild_id]["channel_log"] = channel_log.id
        if member_log: data[guild_id]["member_log"] = member_log.id
        if mod_log: data[guild_id]["mod_log"] = mod_log.id
        if reaction_log: data[guild_id]["reaction_log"] = reaction_log.id
        if invite_log: data[guild_id]["invite_log"] = invite_log.id
        if voice_log: data[guild_id]["voice_log"] = voice_log.id

        save_data(data)
        
        embed = discord.Embed(title="✅ تم حفظ الرومات بنجاح", description="تم تحديث وإعداد رومات اللوق التي قمت بتحديدها للتو.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # 2. لوق الرسائل (حذف وتعديل) مع المنفذ
    # ==========================================
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild: return
        log_channel = await self.get_log_channel(message.guild.id, "msg_log")
        if not log_channel: return

        # البحث إن كان هناك إداري حذف الرسالة
        executor = await self.get_executor(message.guild, discord.AuditLogAction.message_delete, message.author.id)
        # إذا لم يُعثر على إداري حذفها خلال الثواني الماضية، فالمنفذ هو صاحب الرسالة نفسه
        final_executor = executor.mention if executor else message.author.mention

        embed = discord.Embed(title="🗑️ حذف رسالة", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ", value=final_executor, inline=True)
        embed.add_field(name="صاحب الرسالة", value=message.author.mention, inline=True)
        embed.add_field(name="الروم", value=message.channel.mention, inline=False)
        content = message.content[:1024] if message.content else "لا يوجد نص (صورة أو ملف مرفق)"
        embed.add_field(name="المحتوى الأصل", value=content, inline=False)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content: return
        log_channel = await self.get_log_channel(before.guild.id, "msg_log")
        if not log_channel: return

        embed = discord.Embed(title="✏️ تعديل رسالة", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ (الكاتب)", value=before.author.mention, inline=True)
        embed.add_field(name="الروم", value=before.channel.mention, inline=True)
        embed.add_field(name="قبل التعديل", value=before.content[:1024] or "فارغ", inline=False)
        embed.add_field(name="بعد التعديل", value=after.content[:1024] or "فارغ", inline=False)
        embed.add_field(name="رابط المعاينة", value=f"[اضغط هنا للانتقال]({after.jump_url})", inline=False)
        await log_channel.send(embed=embed)

    # ==========================================
    # 3. لوق الرتب (إنشاء، حذف، إعطاء، سحب) مع المنفذ
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_channel = await self.get_log_channel(role.guild.id, "role_log")
        if not log_channel: return
        executor = await self.get_executor(role.guild, discord.AuditLogAction.role_create, role.id)

        embed = discord.Embed(title="🛡️ إنشاء رتبة جديدة", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ", value=executor.mention if executor else "غير معروف", inline=True)
        embed.add_field(name="الرتبة", value=role.mention, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_channel = await self.get_log_channel(role.guild.id, "role_log")
        if not log_channel: return
        executor = await self.get_executor(role.guild, discord.AuditLogAction.role_delete, role.id)

        embed = discord.Embed(title="🗑️ حذف رتبة", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ", value=executor.mention if executor else "غير معروف", inline=True)
        embed.add_field(name="اسم الرتبة المحذوفة", value=role.name, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        log_channel = await self.get_log_channel(before.guild.id, "role_log")
        mod_channel = await self.get_log_channel(before.guild.id, "mod_log")
        
        # تتبع إعطاء وسحب الرتب ومعرفة المنفذ
        if len(before.roles) != len(after.roles) and log_channel:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            executor = await self.get_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
            executor_mention = executor.mention if executor else "غير معروف"
            
            if added:
                embed = discord.Embed(title="➕ إعطاء رتبة لعضو", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
                embed.add_field(name="المنفذ", value=executor_mention, inline=True)
                embed.add_field(name="المستلم", value=after.mention, inline=True)
                embed.add_field(name="الرتب المضافة", value=" ".join([r.mention for r in added]), inline=False)
                await log_channel.send(embed=embed)
                
            if removed:
                embed = discord.Embed(title="➖ سحب رتبة من عضو", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="المنفذ", value=executor_mention, inline=True)
                embed.add_field(name="العضو", value=after.mention, inline=True)
                embed.add_field(name="الرتب المسحوبة", value=" ".join([r.mention for r in removed]), inline=False)
                await log_channel.send(embed=embed)

        # تتبع التايم أوت (كتم الأعضاء) ومعرفة المنفذ
        if before.timed_out_until != after.timed_out_until and mod_channel:
            executor = await self.get_executor(after.guild, discord.AuditLogAction.member_update, after.id)
            executor_mention = executor.mention if executor else "غير معروف"
            if after.timed_out_until:
                embed = discord.Embed(title="⏱️ تطبيق تايم أوت", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                embed.add_field(name="المنفذ", value=executor_mention, inline=True)
                embed.add_field(name="المستهدف", value=after.mention, inline=True)
                embed.add_field(name="ينتهي في", value=f"<t:{int(after.timed_out_until.timestamp())}:R>", inline=False)
                await mod_channel.send(embed=embed)
            else:
                embed = discord.Embed(title="⏱️ فك التايم أوت", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                embed.add_field(name="المنفذ", value=executor_mention, inline=True)
                embed.add_field(name="العضو", value=after.mention, inline=True)
                await mod_channel.send(embed=embed)

    # ==========================================
    # 4. لوق الرومات (إنشاء، حذف، تعديل وتعديل صلاحيات)
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id, "channel_log")
        if not log_channel: return
        executor = await self.get_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)

        embed = discord.Embed(title="📁 إنشاء روم جديد", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ", value=executor.mention if executor else "غير معروف", inline=True)
        embed.add_field(name="الروم", value=channel.mention, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = await self.get_log_channel(channel.guild.id, "channel_log")
        if not log_channel: return
        executor = await self.get_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)

        embed = discord.Embed(title="🗑️ حذف روم", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ", value=executor.mention if executor else "غير معروف", inline=True)
        embed.add_field(name="اسم الروم", value=channel.name, inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild.id, "channel_log")
        if not log_channel: return

        # فحص تعديل الصلاحيات أو تعديل الإعدادات العامة للروم
        executor = await self.get_executor(after.guild, discord.AuditLogAction.channel_update, after.id)
        if not executor:
            executor = await self.get_executor(after.guild, discord.AuditLogAction.overwrite_update, after.id)

        executor_mention = executor.mention if executor else "غير معروف"

        if before.name != after.name:
            embed = discord.Embed(title="📝 تعديل اسم الروم", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            embed.add_field(name="المنفذ", value=executor_mention, inline=True)
            embed.add_field(name="الروم", value=after.mention, inline=True)
            embed.add_field(name="الاسم القديم", value=before.name, inline=False)
            embed.add_field(name="الاسم الجديد", value=after.name, inline=False)
            await log_channel.send(embed=embed)
        
        elif before.overwrites != after.overwrites:
            embed = discord.Embed(title="🔒 تعديل صلاحيات الروم", color=discord.Color.dark_orange(), timestamp=discord.utils.utcnow())
            embed.add_field(name="المنفذ", value=executor_mention, inline=True)
            embed.add_field(name="الروم", value=after.mention, inline=True)
            await log_channel.send(embed=embed)

    # ==========================================
    # 5. لوق المودريشن (بان، كيك، طرد ودعوات)
    # ==========================================
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        self.invites[invite.guild.id] = await invite.guild.invites()
        log_channel = await self.get_log_channel(invite.guild.id, "invite_log")
        if not log_channel: return

        embed = discord.Embed(title="🔗 إنشاء رابط دعوة", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ (المنشئ)", value=invite.inviter.mention if invite.inviter else "غير معروف", inline=True)
        embed.add_field(name="الرابط", value=invite.url, inline=False)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        log_channel = await self.get_log_channel(member.guild.id, "member_log")
        if not log_channel: return

        inviter = None
        if member.guild.id in self.invites:
            old_invites = self.invites[member.guild.id]
            try:
                new_invites = await member.guild.invites()
                for old_invite in old_invites:
                    for new_invite in new_invites:
                        if old_invite.code == new_invite.code and old_invite.uses < new_invite.uses:
                            inviter = new_invite.inviter
                            break
                self.invites[member.guild.id] = new_invites
            except:
                pass

        embed = discord.Embed(title="📥 دخول عضو جديد", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو", value=member.mention, inline=True)
        embed.add_field(name="بواسطة دعوة", value=inviter.mention if inviter else "رابط مباشر أو غير معروف", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # التحقق الفوري لمعرفة هل خرج بنفسه أم تم طرده (Kick)
        kick_executor = await self.get_executor(member.guild, discord.AuditLogAction.kick, member.id)
        
        if kick_executor:
            mod_channel = await self.get_log_channel(member.guild.id, "mod_log")
            if mod_channel:
                embed = discord.Embed(title="🥾 طرد عضو (Kick)", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="المنفذ", value=kick_executor.mention, inline=True)
                embed.add_field(name="المطرود", value=f"{member.name} ({member.mention})", inline=True)
                await mod_channel.send(embed=embed)
        else:
            member_channel = await self.get_log_channel(member.guild.id, "member_log")
            if member_channel:
                embed = discord.Embed(title="📤 خروج عضو", color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow())
                embed.add_field(name="العضو", value=f"{member.name} ({member.mention})", inline=True)
                await member_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        log_channel = await self.get_log_channel(guild.id, "mod_log")
        if not log_channel: return
        executor = await self.get_executor(guild, discord.AuditLogAction.ban, user.id)

        embed = discord.Embed(title="🔨 حظر عضو (Ban)", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="المنفذ", value=executor.mention if executor else "غير معروف", inline=True)
        embed.add_field(name="المحظور", value=user.mention, inline=True)
        await log_channel.send(embed=embed)

    # ==========================================
    # 6. لوق الرياكشن (إضافة وحذف)
    # ==========================================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member and payload.member.bot: return
        log_channel = await self.get_log_channel(payload.guild_id, "reaction_log")
        if not log_channel: return
        
        channel = self.bot.get_channel(payload.channel_id)
        embed = discord.Embed(title="😀 إضافة رياكشن", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو", value=payload.member.mention, inline=True)
        embed.add_field(name="الإيموجي", value=str(payload.emoji), inline=True)
        embed.add_field(name="الروم", value=channel.mention if channel else "غير معروف", inline=False)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        log_channel = await self.get_log_channel(payload.guild_id, "reaction_log")
        if not log_channel: return
        
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id) if guild else None
        if member and member.bot: return

        channel = self.bot.get_channel(payload.channel_id)
        embed = discord.Embed(title="😶 حذف رياكشن", color=discord.Color.dark_blue(), timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو", value=member.mention if member else "غير معروف", inline=True)
        embed.add_field(name="الإيموجي", value=str(payload.emoji), inline=True)
        embed.add_field(name="الروم", value=channel.mention if channel else "غير معروف", inline=False)
        await log_channel.send(embed=embed)

    # ==========================================
    # 7. لوق الصوت المتطور (دخول، خروج، سحب، طرد صوتي، انتقال)
    # ==========================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return
        log_channel = await self.get_log_channel(member.guild.id, "voice_log")
        if not log_channel: return

        # أ: دخول روم صوتي لأول مرة
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(title="🔊 دخول الروم الصوتي", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=member.mention, inline=True)
            embed.add_field(name="الروم", value=after.channel.mention, inline=True)
            await log_channel.send(embed=embed)

        # ب: خروج نهائي من الصوت أو طرد صوتي من قبل إداري
        elif before.channel is not None and after.channel is None:
            # تحقق من سجل الطرد الصوتي
            disconnect_executor = await self.get_executor(member.guild, discord.AuditLogAction.member_disconnect, member.id)
            
            if disconnect_executor:
                embed = discord.Embed(title="🚫 طرد من الروم الصوتي", color=discord.Color.purple(), timestamp=discord.utils.utcnow())
                embed.add_field(name="المنفذ", value=disconnect_executor.mention, inline=True)
                embed.add_field(name="العضو المطرود", value=member.mention, inline=True)
                embed.add_field(name="من الروم", value=before.channel.mention, inline=False)
            else:
                embed = discord.Embed(title="🔇 خروج من الروم الصوتي", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="العضو", value=member.mention, inline=True)
                embed.add_field(name="الروم المغادر", value=before.channel.mention, inline=True)
            
            await log_channel.send(embed=embed)

        # ج: الانتقال بين الرومات أو السحب من قبل إداري
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            # تحقق من سجل السحب والتحريك الإداري
            move_executor = await self.get_executor(member.guild, discord.AuditLogAction.member_move, member.id)
            
            if move_executor:
                embed = discord.Embed(title="🔄 سحب عضو صوتي", color=discord.Color.dark_magenta(), timestamp=discord.utils.utcnow())
                embed.add_field(name="المنفذ (الذي سحب)", value=move_executor.mention, inline=True)
                embed.add_field(name="العضو المسحوب", value=member.mention, inline=True)
                embed.add_field(name="من روم", value=before.channel.mention, inline=True)
                embed.add_field(name="إلى روم", value=after.channel.mention, inline=True)
            else:
                embed = discord.Embed(title="🔄 انتقال بالصوت (شخصي)", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
                embed.add_field(name="العضو", value=member.mention, inline=False)
                embed.add_field(name="من روم", value=before.channel.mention, inline=True)
                embed.add_field(name="إلى روم", value=after.channel.mention, inline=True)
            
            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LogsCog(bot))