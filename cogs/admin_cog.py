import discord
from discord.ext import commands
import sys
import time
import datetime
import asyncio

# 1. كلاس المنيو (القائمة المنسدلة)
class AdminSelect(discord.ui.Select):
    def __init__(self, bot, start_time):
        self.bot = bot
        self.start_time = start_time
        
        # الخيارات التي ستظهر في المنيو
        options = [
            discord.SelectOption(label="إحصائيات البوت", description="عرض حالة النظام والكوجات وسرعة الاستجابة", emoji="📊", value="stats"),
            discord.SelectOption(label="تغيير الأفتار", description="رفع صورة جديدة كأفتار للبوت", emoji="🖼️", value="avatar"),
            discord.SelectOption(label="تغيير البنر", description="رفع صورة جديدة كخلفية للبوت", emoji="🌌", value="banner"),
            discord.SelectOption(label="إعادة التشغيل", description="إطفاء البوت لإعادة تشغيله عبر الاستضافة", emoji="🔄", value="restart")
        ]
        super().__init__(placeholder="⚙️ اختر الإجراء الذي تريده...", min_values=1, max_values=1, options=options)

    # الحدث الذي يحصل عند اختيار شيء من المنيو
    async def callback(self, interaction: discord.Interaction):
        # حماية إضافية: التأكد أن من ضغط الزر يملك صلاحية Administrator في السيرفر
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ هذه اللوحة مخصصة للإداريين (Administrator) فقط!", ephemeral=True)

        choice = self.values[0]

        # خيار: الإحصائيات
        if choice == "stats":
            uptime_seconds = int(round(time.time() - self.start_time))
            uptime_str = str(datetime.timedelta(seconds=uptime_seconds))
            loaded_cogs = list(self.bot.cogs.keys())
            
            embed = discord.Embed(title="📊 إحصائيات نظام البوت", color=discord.Color.dark_theme())
            embed.add_field(name="⏱️ مدة التشغيل", value=f"`{uptime_str}`", inline=False)
            embed.add_field(name="🏓 سرعة الاستجابة", value=f"`{round(self.bot.latency * 1000)}ms`", inline=False)
            embed.add_field(name="📦 الكوجات المحملة", value=f"`{len(loaded_cogs)} Cogs`\n{', '.join(loaded_cogs)}", inline=False)
            embed.add_field(name="⌨️ الأوامر", value=f"`{len(self.bot.commands)}`", inline=True)
            embed.add_field(name="⚡ أوامر السلاش", value=f"`{len(self.bot.tree.get_commands())}`", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        # خيار: إعادة التشغيل
        elif choice == "restart":
            await interaction.response.send_message("🔄 جاري إطفاء البوت لإعادة التشغيل...", ephemeral=True)
            sys.exit(0)

        # خيار: الأفتار أو البنر
        elif choice in ["avatar", "banner"]:
            action_name = "الأفتار" if choice == "avatar" else "البنر"
            await interaction.response.send_message(f"📥 يرجى إرسال الصورة هنا في الشات لتغيير **{action_name}**.\n*(لديك 60 ثانية...)*", ephemeral=True)

            # دالة للتحقق أن الرسالة القادمة من نفس الإداري وفي نفس الروم وتحتوي على مرفق
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel and m.attachments

            try:
                # انتظار رسالة الإداري التي تحتوي على الصورة
                msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                image_bytes = await msg.attachments[0].read()
                
                # تنفيذ التغيير
                if choice == "avatar":
                    await self.bot.user.edit(avatar=image_bytes)
                else:
                    await self.bot.user.edit(banner=image_bytes)
                    
                await msg.reply(f"✅ تم تغيير {action_name} بنجاح!")
            
            except asyncio.TimeoutError:
                # إذا انتهت الـ 60 ثانية ولم يرسل شيء
                await interaction.followup.send("⏳ انتهى الوقت! لم تقم بإرسال الصورة. يرجى المحاولة من جديد.", ephemeral=True)
            except discord.HTTPException as e:
                await interaction.followup.send(f"⚠️ حدث خطأ من ديسكورد (تأكد من صيغة وحجم الصورة):\n{e}", ephemeral=True)

# 2. كلاس الـ View لاحتواء المنيو
class AdminView(discord.ui.View):
    def __init__(self, bot, start_time):
        super().__init__(timeout=None) # المنيو لن ينتهي وقته
        self.add_item(AdminSelect(bot, start_time))

# 3. الكوج الأساسي
class AdminSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    # أمر إظهار لوحة التحكم (المنيو)
    @commands.command(name="panel", aliases=["admin"])
    @commands.has_permissions(administrator=True) # التحقق من أن منفذ الأمر لديه صلاحية إداري
    async def admin_panel(self, ctx):
        embed = discord.Embed(
            title="🛠️ لوحة تحكم الإدارة",
            description="مرحباً بك في لوحة التحكم المركزية.\nاستخدم القائمة المنسدلة بالأسفل لاختيار الإجراء الذي تريده.",
            color=discord.Color.red()
        )
        # إرسال الرسالة مع إرفاق المنيو بداخلها
        await ctx.send(embed=embed, view=AdminView(self.bot, self.start_time))

async def setup(bot):
    await bot.add_cog(AdminSettings(bot))