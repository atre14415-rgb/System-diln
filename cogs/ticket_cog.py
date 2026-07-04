import discord
from discord.ext import commands
from discord import app_commands
import chat_exporter
import io
import time

# ================= الإعدادات الأساسية =================
MY_GUILD = discord.Object(id=1518871277740228608) 
ADMIN_ROLE_ID = 1517019560690323516  # ⚠️ آيدي رتبة الإدارة (الدعم الفني)
LOG_CHANNEL_ID = 1517015117160513726 # ⚠️ آيدي روم السجلات (اللوق) اللي بتروح له التذاكر بعد الحذف
CATEGORY_ID = 1498637049782210646    # ⚠️ آيدي الكاتيجوري (القسم) اللي بتنفتح داخله التذاكر
# ======================================================

# 1. منيو تحكم الإدارة (داخل التذكرة)
class AdminTicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="استلام التذكرة", emoji="✋", value="claim"),
            discord.SelectOption(label="تذكير العضو", emoji="🔔", value="remind"),
            discord.SelectOption(label="عدم استجابة", emoji="⚠️", value="no_response"),
            discord.SelectOption(label="إغلاق التذكرة", emoji="🔒", value="close"),
            discord.SelectOption(label="حذف التذكرة", emoji="🗑️", value="delete")
        ]
        super().__init__(placeholder="🛠️ لوحة تحكم الإدارة...", min_values=1, max_values=1, options=options, custom_id="admin_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        # التحقق من أن المستخدم من الإدارة
        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role not in interaction.user.roles and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ هذا المنيو مخصص للإدارة فقط!", ephemeral=True)

        channel = interaction.channel
        action = self.values[0]
        
        # استخراج آيدي صاحب التذكرة ووقت الفتح من وصف الروم (Topic)
        try:
            opener_id, open_time = channel.topic.split("-")
            opener_id = int(opener_id)
        except:
            opener_id = None
            open_time = "غير معروف"

        # تفريغ التحديد من المنيو
        await interaction.response.defer()

        if action == "claim":
            embed = discord.Embed(description=f"👨‍💻 **تم استلام التذكرة بواسطة:** {interaction.user.mention}\nسيتم الرد عليك في أقرب وقت ممكن.", color=discord.Color.green())
            await channel.send(embed=embed)

        elif action == "remind":
            embed = discord.Embed(description="🔔 **تذكير:** نرجو منك الرد على التذكرة لتتمكن الإدارة من مساعدتك.", color=discord.Color.blue())
            if opener_id:
                await channel.send(content=f"<@{opener_id}>", embed=embed)
            else:
                await channel.send(embed=embed)

        elif action == "no_response":
            embed = discord.Embed(title="⚠️ تنبيه عدم استجابة", description="نرجو منك الرد على التذكرة بأسرع وقت.\nفي حال عدم الاستجابة لفترة طويلة، سيتم إغلاق التذكرة تلقائياً.", color=discord.Color.orange())
            if opener_id:
                await channel.send(content=f"<@{opener_id}>", embed=embed)
            else:
                await channel.send(embed=embed)

        elif action == "close":
            # سحب صلاحية الكتابة من العضو
            if opener_id:
                member = interaction.guild.get_member(opener_id)
                if member:
                    overwrite = channel.overwrites_for(member)
                    overwrite.send_messages = False
                    await channel.set_permissions(member, overwrite=overwrite)
            
            await channel.edit(name=f"closed-{channel.name}")
            embed = discord.Embed(title="🔒 تم الإغلاق", description=f"تم إغلاق هذه التذكرة بواسطة: {interaction.user.mention}", color=discord.Color.red())
            await channel.send(embed=embed)

        elif action == "delete":
            close_time = int(time.time())
            await channel.send("⏳ جاري إنشاء الترانسكربت (HTML) وحذف التذكرة، الرجاء الانتظار...")
            
            # توليد ملف HTML للمحادثة
            transcript = await chat_exporter.export(channel)
            transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{channel.name}.html")
            
            # إرسال الملف لروم اللوق عشان ناخذ الرابط حقه
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            log_msg = await log_channel.send(file=transcript_file)
            transcript_url = log_msg.attachments[0].url

            # تجهيز إيمبد اللوق
            embed = discord.Embed(title="🗑️ تذكرة محذوفة", color=discord.Color.dark_theme())
            embed.add_field(name="صاحب التذكرة", value=f"<@{opener_id}>" if opener_id else "غير معروف", inline=True)
            embed.add_field(name="حُذفت بواسطة", value=interaction.user.mention, inline=True)
            embed.add_field(name="وقت الفتح", value=f"<t:{open_time}:f>" if open_time != "غير معروف" else "غير معروف", inline=False)
            embed.add_field(name="وقت الإغلاق", value=f"<t:{close_time}:f>", inline=False)
            
            # زر يفتح رابط الـ HTML
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="📄 عرض المحادثة (HTML)", url=transcript_url))

            # إرسال اللوق للروم السري
            await log_channel.send(embed=embed, view=view)

            # محاولة إرسال اللوق لصاحب التذكرة في الخاص
            if opener_id:
                try:
                    member = interaction.guild.get_member(opener_id)
                    if member:
                        await member.send(f"تم إغلاق وحذف تذكرتك في سيرفر **{interaction.guild.name}**.\nإليك تفاصيل وسجل المحادثة:", embed=embed, view=view)
                except discord.Forbidden:
                    pass

            # حذف الروم
            await channel.delete()

class AdminTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AdminTicketSelect())

# 2. منيو فتح التذاكر (للأعضاء)
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="استفسار", description="لديك سؤال أو استفسار عام", emoji="❓", value="inquiry"),
            discord.SelectOption(label="دعم فني", description="مشاكل تقنية أو مساعدة", emoji="🛠️", value="support"),
            discord.SelectOption(label="تواصل مع الإدارة", description="شكوى أو طلب خاص بالإدارة", emoji="👑", value="admin")
        ]
        super().__init__(placeholder="📩 اختر نوع التذكرة لفتحها...", min_values=1, max_values=1, options=options, custom_id="user_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        
        # التأكد من عدم وجود تذكرة مفتوحة لنفس الشخص بنفس النوع
        ticket_type = self.values[0]
        expected_name = f"{ticket_type}-{interaction.user.name.lower()}"
        
        for ch in guild.text_channels:
            if ch.name == expected_name:
                return await interaction.response.send_message(f"❌ لديك تذكرة مفتوحة بالفعل: {ch.mention}", ephemeral=True)

        await interaction.response.send_message("⏳ جاري فتح تذكرتك...", ephemeral=True)

        # إعداد الصلاحيات
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }

        # إنشاء الروم ووضع آيدي العضو ووقت الفتح في الوصف (Topic)
        open_time = int(time.time())
        channel = await guild.create_text_channel(
            name=expected_name, 
            category=category, 
            overwrites=overwrites,
            topic=f"{interaction.user.id}-{open_time}"
        )

        # رسالة الترحيب ومنشن العضو والإدارة
        welcome_embed = discord.Embed(
            title="مرحبا بك ",
            description=f"أهلاً بك {interaction.user.mention} في تذكرتك.\nنرجو منك كتابة تفاصيل مشكلتك بوضوح والانتظار حتى يتم الرد عليك من قِبل {admin_role.mention}.",
            color=discord.Color.blue()
        )
        
        # إرسال الرسالة مع منيو الإدارة تحتها
        await channel.send(content=f"{interaction.user.mention} | {admin_role.mention}", embed=welcome_embed, view=AdminTicketView())
        await interaction.edit_original_response(content=f"✅ تم فتح تذكرتك بنجاح: {channel.mention}")

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# 3. الكوج الأساسي والأوامر
class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # حدث تشغيل البوت لإبقاء الأزرار تعمل بعد إعادة التشغيل
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(AdminTicketView())

    # أمر إرسال اللوحة لأول مرة
    @app_commands.command(name="setup_tickets", description="إرسال لوحة فتح التذاكر (للإدارة فقط)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(MY_GUILD)
    async def setup_tickets(self, interaction: discord.Interaction, image_url: str = None):
        embed = discord.Embed(
            title="Echo",
            description="مرحباً بك في مركز الدعم.\nيرجى اختيار نوع التذكرة التي ترغب بفتحها من القائمة بالأسفل.",
            color=discord.Color.dark_theme()
        )
        if image_url:
            embed.set_image(url=image_url)
            
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("✅ تم إرسال لوحة التذاكر بنجاح.", ephemeral=True)

    # أمر تحديث القائمة بدون إعادة إرسالها (إعادة تشغيلها)
    @app_commands.command(name="refresh_panel", description="تحديث لوحة التذاكر الحالية (في حال توقفت الأزرار)")
    @app_commands.describe(message_id="آيدي (ID) رسالة لوحة التذاكر")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(MY_GUILD)
    async def refresh_panel(self, interaction: discord.Interaction, message_id: str):
        try:
            msg = await interaction.channel.fetch_message(int(message_id))
            # تحديث الـ View الخاص بالرسالة لإعادة تفعيلها
            await msg.edit(view=TicketPanelView())
            await interaction.response.send_message("✅ تم تحديث وإعادة تشغيل القائمة بنجاح دون إرسال رسالة جديدة!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ، تأكد من الآيدي ومن أن الرسالة في هذا الروم.\nالخطأ: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))