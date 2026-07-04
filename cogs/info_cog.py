import discord
from discord.ext import commands
from discord import app_commands

# ⚠️ آيدي سيرفرك للظهور السريع للأوامر
MY_GUILD = discord.Object(id=1518871277740228608) 

class InformationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. أمر معلومات العضو (User Info)
    @app_commands.command(name="userinfo", description="عرض معلومات مفصلة عن عضو معين وتاريخ حسابه")
    @app_commands.describe(member="العضو المراد الاستعلام عنه (إذا تركته فارغاً سيعرض معلوماتك)")
    @app_commands.guilds(MY_GUILD)
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        # إذا لم يحدد المستخدم عضواً، اعرض معلومات المستخدم نفسه
        member = member or interaction.user
        
        # تحويل تواريخ ديسكورد إلى صيغة الوقت الذكي
        created_time = int(member.created_at.timestamp())
        joined_time = int(member.joined_at.timestamp())
        
        embed = discord.Embed(title=f"👤 معلومات العضو: {member.name}", color=member.color or discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="المنشن:", value=member.mention, inline=True)
        embed.add_field(name="الآيدي (ID):", value=f"`{member.id}`", inline=True)
        embed.add_field(name="أعلى رتبة:", value=member.top_role.mention, inline=True)
        
        # استخدام <t:time:R> ليعرض الوقت بصيغة "منذ يومين" أو "منذ سنة"
        embed.add_field(name="📅 تاريخ إنشاء الحساب:", value=f"<t:{created_time}:F>\n(<t:{created_time}:R>)", inline=False)
        embed.add_field(name="📥 تاريخ دخول السيرفر:", value=f"<t:{joined_time}:F>\n(<t:{joined_time}:R>)", inline=False)
        
        await interaction.response.send_message(embed=embed)

    # 2. أمر معلومات السيرفر (Server Info)
    @app_commands.command(name="serverinfo", description="عرض إحصائيات ومعلومات السيرفر الشاملة")
    @app_commands.guilds(MY_GUILD)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        # حساب عدد البشر مقابل البوتات
        bots_count = sum(1 for member in guild.members if member.bot)
        humans_count = guild.member_count - bots_count
        
        created_time = int(guild.created_at.timestamp())
        
        embed = discord.Embed(title=f"📊 إحصائيات سيرفر: {guild.name}", color=discord.Color.gold())
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="👑 المالك:", value=guild.owner.mention, inline=True)
        embed.add_field(name="🆔 آيدي السيرفر:", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 تاريخ الإنشاء:", value=f"<t:{created_time}:R>", inline=True)
        
        embed.add_field(name="👥 الأعضاء:", value=f"الكل: `{guild.member_count}`\nبشر: `{humans_count}`\nبوتات: `{bots_count}`", inline=True)
        embed.add_field(name="📁 الرومات:", value=f"نصية: `{len(guild.text_channels)}`\nصوتية: `{len(guild.voice_channels)}`", inline=True)
        embed.add_field(name="💎 مستوى البوست:", value=f"المستوى `{guild.premium_tier}`\n(`{guild.premium_subscription_count}` بوستات)", inline=True)
        
        await interaction.response.send_message(embed=embed)

    # 3. أمر سحب الصورة (Avatar)
    @app_commands.command(name="avatar", description="سحب وعرض صورة العضو بجودة عالية")
    @app_commands.describe(member="العضو المراد سحب صورته")
    @app_commands.guilds(MY_GUILD)
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        
        embed = discord.Embed(title=f"🖼️ صورة العضو: {member.display_name}", color=discord.Color.dark_theme())
        # وضع الصورة بحجمها الكامل داخل الإيمبد
        embed.set_image(url=member.display_avatar.url)
        # رابط مباشر لمن يريد تحميلها بجودتها الأصلية
        embed.description = f"[🔗 اضغط هنا لتحميل الصورة بجودة عالية]({member.display_avatar.url})"
        
        await interaction.response.send_message(embed=embed)

# دالة التشغيل
async def setup(bot):
    await bot.add_cog(InformationSystem(bot))