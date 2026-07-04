import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# اسم الملف الذي ستحفظ فيه إعدادات الرول التلقائي لكل سيرفر
DATA_FILE = "autorole_data.json"

# دالة لجلب البيانات المحفوظة
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# دالة لحفظ البيانات
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class AutoRoleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("AutoRole Cog is Ready.")

    # أمر سلاش مخصص للإدارة لتحديد الرول
    @app_commands.command(name="set_autorole", description="تحديد الرول التلقائي الذي سيأخذه أي عضو جديد")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        # التأكد من أن رتبة البوت أعلى من الرتبة المراد إعطاؤها
        if role.position >= interaction.guild.me.top_role.position:
            return await interaction.response.send_message(
                "❌ لا يمكنني إعطاء هذا الرول لأن رتبتي في السيرفر أقل منه أو تساويه. يرجى رفع رتبة البوت في إعدادات السيرفر.", 
                ephemeral=True
            )

        data = load_data()
        data[str(interaction.guild.id)] = role.id
        save_data(data)

        await interaction.response.send_message(f"✅ تم إعداد الرول التلقائي بنجاح. أي عضو جديد سيحصل على {role.mention}", ephemeral=True)

    # أمر سلاش لإيقاف الرول التلقائي
    @app_commands.command(name="disable_autorole", description="إيقاف نظام الرول التلقائي في السيرفر")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_autorole(self, interaction: discord.Interaction):
        data = load_data()
        guild_id = str(interaction.guild.id)
        
        if guild_id in data:
            del data[guild_id]
            save_data(data)
            await interaction.response.send_message("✅ تم إيقاف نظام الرول التلقائي بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ نظام الرول التلقائي غير مفعل من الأساس.", ephemeral=True)

    # الحدث الذي يشتغل عند دخول أي شخص للسيرفر
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = load_data()
        guild_id = str(member.guild.id)

        # التحقق مما إذا كان السيرفر قد حدد رولاً تلقائياً
        if guild_id in data:
            role_id = data[guild_id]
            role = member.guild.get_role(role_id)

            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    # يتم تجاهل الخطأ بصمت إذا لم يمتلك البوت صلاحية كافية وقت دخول العضو
                    print(f"فشلت عملية إعطاء الرول للعضو {member.name} بسبب نقص الصلاحيات.")
                except discord.HTTPException:
                    print("حدث خطأ في الاتصال بديسكورد أثناء إعطاء الرول.")

async def setup(bot):
    await bot.add_cog(AutoRoleSystem(bot))