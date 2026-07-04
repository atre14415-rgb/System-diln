import discord
from discord.ext import commands
from discord import app_commands

# ⚠️ آيدي السيرفر للظهور السريع للأمر
MY_GUILD = discord.Object(id=1439839910172295303) 

class SaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="يجعل البوت يرسل رسالة نصية بالنيابة عنك")
    @app_commands.describe(
        text="النص الذي تريد من البوت إرساله",
        channel="الروم الذي تريد إرسال الرسالة إليه (اختياري، اتركه فارغاً للإرسال هنا)"
    )
    # حماية: الأمر مخصص فقط لمن لديه صلاحية إدارة الرسائل
    @app_commands.default_permissions(manage_messages=True) 
    @app_commands.guilds(MY_GUILD)
    async def say_command(self, interaction: discord.Interaction, text: str, channel: discord.TextChannel = None):
        # إذا لم يحدد المشرف روماً، سيقوم البوت بالإرسال في الروم الحالي الذي كُتب فيه الأمر
        target_channel = channel or interaction.channel
        
        try:
            # إرسال الرسالة المطلوبة
            await target_channel.send(text)
            
            # إرسال تأكيد مخفي للمشرف فقط عشان ما يظهر الأمر في الشات
            await interaction.response.send_message(f"✅ تم إرسال رسالتك بنجاح في {target_channel.mention}", ephemeral=True)
            
        except discord.Forbidden:
            # في حال تم تحديد روم لا يملك البوت صلاحية الكتابة فيه
            await interaction.response.send_message(f"❌ البوت لا يملك صلاحية للكتابة في {target_channel.mention}.", ephemeral=True)

# دالة التشغيل
async def setup(bot):
    await bot.add_cog(SaySystem(bot))