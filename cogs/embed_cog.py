import discord
from discord.ext import commands
from discord import app_commands

# ⚠️ آيدي سيرفرك للظهور السريع للأمر
MY_GUILD = discord.Object(id=1518871277740228608) 

class EmbedBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # أمر السلاش لصناعة الإيمبد
    @app_commands.command(name="embed", description="إنشاء وإرسال رسالة إيمبد (Embed) مخصصة")
    @app_commands.describe(
        title="عنوان الإيمبد",
        description="النص الأساسي للإيمبد (الرسالة)",
        color="اختر لون الخط الجانبي",
        image="ارفع صورة لتظهر داخل الإيمبد (اختياري)"
    )
    # تحديد خيارات الألوان لتظهر كقائمة منسدلة أنيقة
    @app_commands.choices(color=[
        app_commands.Choice(name="🔴 أحمر", value="red"),
        app_commands.Choice(name="🟢 أخضر", value="green"),
        app_commands.Choice(name="🔵 أزرق", value="blue"),
        app_commands.Choice(name="🟡 أصفر", value="yellow"),
        app_commands.Choice(name="⚫ أسود", value="black"),
        app_commands.Choice(name="⚪ أبيض", value="white"),
        app_commands.Choice(name="🟣 بنفسجي", value="purple")
    ])
    @app_commands.default_permissions(manage_messages=True) # حماية: الأمر للإدارة فقط
    @app_commands.guilds(MY_GUILD)
    async def create_embed(
        self, 
        interaction: discord.Interaction, 
        title: str, 
        description: str, 
        color: app_commands.Choice[str], 
        image: discord.Attachment = None
    ):
        # قاموس لتحويل اختيار المستخدم إلى لون حقيقي في ديسكورد
        colors_map = {
            "red": discord.Color.red(),
            "green": discord.Color.green(),
            "blue": discord.Color.blue(),
            "yellow": discord.Color.gold(),
            "black": discord.Color.default(),
            "white": discord.Color.light_embed(),
            "purple": discord.Color.purple()
        }
        
        # جلب اللون المختار
        embed_color = colors_map.get(color.value, discord.Color.blue())

        # بناء الإيمبد
        embed = discord.Embed(title=title, description=description, color=embed_color)

        # التحقق من وجود صورة وإضافتها للإيمبد
        if image:
            # التأكد من أن الملف المرفق هو صورة فعلية
            if image.content_type and image.content_type.startswith("image/"):
                embed.set_image(url=image.url)
            else:
                return await interaction.response.send_message("❌ الملف المرفق ليس صورة صالحة! يرجى رفع صورة بصيغة (PNG, JPG, JPEG).", ephemeral=True)

        # إرسال الإيمبد في نفس الروم الذي كُتب فيه الأمر
        await interaction.channel.send(embed=embed)
        
        # إرسال رسالة تأكيد مخفية للمشرف عشان ما يزعج الشات
        await interaction.response.send_message("✅ تم إرسال الإيمبد بنجاح!", ephemeral=True)

# دالة التشغيل
async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))