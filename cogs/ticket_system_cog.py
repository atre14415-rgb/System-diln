import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime
import chat_exporter
import io

# مسارات ملفات حفظ البيانات
CONFIG_FILE = "ticket_configs.json"
DATA_FILE = "ticket_data.json"

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ----------------- قوائم التفاعل (UI Views) ----------------- #

class ManageTicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="استلام التذكرة", description="استلام التذكرة وتعيينك كمستلم", value="claim", emoji="✋"),
            discord.SelectOption(label="تذكير بعدم الاستجابة", description="إرسال تذكير لصاحب التذكرة", value="no_response", emoji="⏳"),
            discord.SelectOption(label="إغلاق التذكرة", description="إغلاق التذكرة ومنع العضو من الكتابة", value="close", emoji="🔒"),
            discord.SelectOption(label="حذف وحفظ التذكرة", description="إرسال اللوق وحذف الروم", value="delete", emoji="🗑️")
        ]
        super().__init__(placeholder="إدارة التذكرة (للدعم الفني)...", min_values=1, max_values=1, options=options, custom_id="ticket_manage_select")

    async def callback(self, interaction: discord.Interaction):
        active_tickets = load_json(DATA_FILE)
        channel_id = str(interaction.channel.id)

        if channel_id not in active_tickets:
            return await interaction.response.send_message("❌ هذه التذكرة غير مسجلة في قاعدة البيانات.", ephemeral=True)

        ticket_data = active_tickets[channel_id]
        configs = load_json(CONFIG_FILE)
        ticket_type = ticket_data.get("type")
        config = configs.get(ticket_type, {})
        
        support_role_id = config.get("support_role_id")
        support_role = interaction.guild.get_role(support_role_id) if support_role_id else None

        # التحقق من الصلاحيات (يجب أن يكون لديه رول الدعم أو إداري)
        if support_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لاستخدام هذه الأوامر.", ephemeral=True)

        action = self.values[0]

        if action == "claim":
            if ticket_data.get("claimer_id"):
                return await interaction.response.send_message("⚠️ هذه التذكرة مستلمة بالفعل.", ephemeral=True)
            
            ticket_data["claimer_id"] = interaction.user.id
            save_json(DATA_FILE, active_tickets)
            
            embed = discord.Embed(title="✅ تم استلام التذكرة", description=f"تم استلام هذه التذكرة بواسطة {interaction.user.mention}", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)

        elif action == "no_response":
            opener_id = ticket_data.get("opener_id")
            opener = interaction.guild.get_member(opener_id)
            if opener:
                # إرسال رسالة في الخاص
                dm_embed = discord.Embed(
                    title="⏳ تذكير تذكرة",
                    description=f"مرحباً {opener.mention}، نرجو الرد على تذكرتك المفتوحة في سيرفر **{interaction.guild.name}** وإلا سيتم إغلاقها قريباً.",
                    color=discord.Color.orange()
                )
                try:
                    await opener.send(embed=dm_embed)
                except discord.Forbidden:
                    pass # إذا كان الخاص مغلقاً
                
                # إرسال رسالة في التذكرة
                ticket_embed = discord.Embed(title="تنبيه عدم استجابة", description=f"يرجى الرد يا {opener.mention} لتجنب إغلاق التذكرة.", color=discord.Color.orange())
                await interaction.response.send_message(content=opener.mention, embed=ticket_embed)
            else:
                await interaction.response.send_message("❌ لم يتم العثور على صاحب التذكرة.", ephemeral=True)

        elif action == "close":
            opener_id = ticket_data.get("opener_id")
            opener = interaction.guild.get_member(opener_id)
            claimer_id = ticket_data.get("claimer_id")
            claimer_name = interaction.guild.get_member(claimer_id).display_name if claimer_id else interaction.user.display_name
            
            ticket_data["close_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ticket_data["closer_id"] = interaction.user.id
            save_json(DATA_FILE, active_tickets)

            new_name = f"مغلق-{claimer_name}"
            await interaction.channel.edit(name=new_name)

            if opener:
                await interaction.channel.set_permissions(opener, view_channel=True, send_messages=False)

            close_embed = discord.Embed(title="🔒 تم الإغلاق", description=f"تم إغلاق التذكرة بواسطة {interaction.user.mention}", color=discord.Color.red())
            await interaction.response.send_message(embed=close_embed)

        elif action == "delete":
            await interaction.response.defer()
            log_channel_id = config.get("log_channel_id")
            log_channel = interaction.guild.get_channel(log_channel_id)
            
            # إنشاء ترانسكربت (HTML)
            transcript = await chat_exporter.export(interaction.channel)
            transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{interaction.channel.name}.html")

            if log_channel:
                opener_id = ticket_data.get("opener_id")
                opener = interaction.guild.get_member(opener_id)
                claimer_id = ticket_data.get("claimer_id")
                closer_id = ticket_data.get("closer_id") or interaction.user.id
                
                opener_text = opener.mention if opener else f"<@{opener_id}>"
                claimer_text = f"<@{claimer_id}>" if claimer_id else "لم يتم الاستلام"
                closer_text = f"<@{closer_id}>"
                
                log_embed = discord.Embed(title="📑 سجل تذكرة محذوفة", color=discord.Color.dark_grey())
                log_embed.add_field(name="صاحب التذكرة", value=opener_text, inline=True)
                log_embed.add_field(name="المستلم", value=claimer_text, inline=True)
                log_embed.add_field(name="مغلق/حاذف التذكرة", value=closer_text, inline=True)
                log_embed.add_field(name="وقت الفتح", value=ticket_data.get("open_time", "غير معروف"), inline=True)
                log_embed.add_field(name="وقت الإغلاق/الحذف", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
                
                await log_channel.send(embed=log_embed, file=transcript_file)
            
            if channel_id in active_tickets:
                del active_tickets[channel_id]
                save_json(DATA_FILE, active_tickets)

            await interaction.channel.delete()

class TicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ManageTicketSelect())

class TicketPanelSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="اختر نوع التذكرة الذي تريده...", min_values=1, max_values=1, options=options, custom_id="ticket_panel_select")

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        configs = load_json(CONFIG_FILE)
        config = configs.get(ticket_type)

        if not config:
            return await interaction.response.send_message("❌ حدث خطأ: إعدادات هذه التذكرة غير موجودة.", ephemeral=True)

        category = interaction.guild.get_channel(config["category_id"])
        support_role = interaction.guild.get_role(config["support_role_id"])
        
        if not category:
            return await interaction.response.send_message("❌ لم يتم العثور على الكاتيجوري المخصص لهذه التذكرة.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # استبدال {user} باسم المستخدم في اسم الروم
        channel_name = config["ticket_name_format"].replace("{user}", interaction.user.name)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        # حفظ بيانات التذكرة الجديدة
        active_tickets = load_json(DATA_FILE)
        active_tickets[str(ticket_channel.id)] = {
            "opener_id": interaction.user.id,
            "claimer_id": None,
            "closer_id": None,
            "open_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": ticket_type
        }
        save_json(DATA_FILE, active_tickets)

        # تجهيز رسالة الترحيب
        welcome_embed = discord.Embed(
            title=f"تذكرة {ticket_type}",
            description=config["welcome_message"],
            color=discord.Color.blue()
        )
        if config.get("image_url"):
            welcome_embed.set_image(url=config["image_url"])

        # منشن الرول المحدد (و الدعم إذا لزم الأمر)
        mention_role_id = config.get("mention_role_id")
        mention_text = f"<@&{mention_role_id}>" if mention_role_id else ""

        await ticket_channel.send(content=f"{interaction.user.mention} {mention_text}", embed=welcome_embed, view=TicketManageView())
        await interaction.followup.send(f"✅ تم فتح تذكرتك بنجاح: {ticket_channel.mention}", ephemeral=True)

class TicketPanelView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=None)
        self.add_item(TicketPanelSelect(options))

# ----------------- الكوج (Cog) ----------------- #

class TicketSystemm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # تفعيل الأزرار الثابتة عند إعادة تشغيل البوت
        self.bot.add_view(TicketManageView())
        
        configs = load_json(CONFIG_FILE)
        if configs:
            options = [discord.SelectOption(label=t_name, value=t_name) for t_name in configs.keys()][:25]
            if options:
                self.bot.add_view(TicketPanelView(options))
        print("TicketSystem Cog is Ready.")

    @app_commands.command(name="setup_ticket", description="إعداد نوع تذكرة جديد وحفظه")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_ticket(
        self, 
        interaction: discord.Interaction, 
        type_name: str, 
        category: discord.CategoryChannel, 
        support_role: discord.Role,
        log_channel: discord.TextChannel,
        ticket_name_format: str = "تذكرة-{user}",
        welcome_message: str = "مرحباً بك في التذكرة، يرجى كتابة مشكلتك.",
        image_url: str = None,
        mention_role: discord.Role = None
    ):
        configs = load_json(CONFIG_FILE)
        
        configs[type_name] = {
            "category_id": category.id,
            "support_role_id": support_role.id,
            "log_channel_id": log_channel.id,
            "ticket_name_format": ticket_name_format,
            "welcome_message": welcome_message,
            "image_url": image_url,
            "mention_role_id": mention_role.id if mention_role else None
        }
        
        save_json(CONFIG_FILE, configs)
        await interaction.response.send_message(f"✅ تم حفظ إعدادات التذكرة من نوع **{type_name}** بنجاح.", ephemeral=True)

    @app_commands.command(name="send_panel", description="إرسال لوحة فتح التذاكر للأعضاء")
    @app_commands.checks.has_permissions(administrator=True)
    async def send_panel(self, interaction: discord.Interaction, title: str, description: str):
        configs = load_json(CONFIG_FILE)
        
        if not configs:
            return await interaction.response.send_message("❌ لا توجد أي أنواع تذاكر محفوظة. يرجى استخدام أمر `/setup_ticket` أولاً.", ephemeral=True)

        options = []
        for t_name in configs.keys():
            options.append(discord.SelectOption(label=t_name, value=t_name))
            if len(options) == 25: # أقصى حد للخيارات في Select Menu هو 25
                break

        embed = discord.Embed(title=title, description=description, color=discord.Color.dark_theme())
        view = TicketPanelView(options)

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ تم إرسال لوحة التذاكر بنجاح.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSystemm(bot))