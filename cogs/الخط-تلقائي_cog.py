import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class AutoLine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "auto_line_config.json"
        self.data = self.load_data()

    def load_data(self):
        """تحميل إعدادات الرومات والصور المحفوظة"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_data(self):
        """حفظ التعديلات في الملف لضمان عدم ضياعها عند إعادة التشغيل"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    # 1. أمر تسطيب الخط التلقائي
    @app_commands.command(name="تسطيب_الخط", description="تحديد روم وصورة ليقوم البوت بإرسالها كفاصل تلقائي بعد كل رسالة")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_line(self, interaction: discord.Interaction, channel: discord.TextChannel, image: discord.Attachment):
        # التأكد من أن المرفق عبارة عن صورة
        if not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message("❌ الرجاء إرفاق ملف صورة صالح وليس ملفاً من نوع آخر.", ephemeral=True)
            return

        # حفظ أيدي الروم ورابط الصورة
        self.data[str(channel.id)] = image.url
        self.save_data()
        
        await interaction.response.send_message(f"✅ تم تفعيل الخط التلقائي في روم {channel.mention} بنجاح.", ephemeral=True)

    # 2. أمر حذف الخط من روم معين
    @app_commands.command(name="إلغاء_الخط", description="إزالة الخط التلقائي من روم معين")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_line(self, interaction: discord.Interaction, channel: discord.TextChannel):
        channel_id = str(channel.id)
        
        if channel_id in self.data:
            del self.data[channel_id]
            self.save_data()
            await interaction.response.send_message(f"✅ تم إلغاء الخط التلقائي من روم {channel.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ هذا الروم لا يحتوي على خط تلقائي حالياً.", ephemeral=True)

    # 3. حدث مراقبة الرسائل لإرسال الخط
    @commands.Cog.listener()
    async def on_message(self, message):
        # تجاهل رسائل البوتات حتى لا يرد البوت على نفسه ويدخل في حلقة لا نهائية (Spam)
        if message.author.bot:
            return

        channel_id = str(message.channel.id)
        
        # إذا كان الروم مسجلاً في قاعدة البيانات
        if channel_id in self.data:
            image_url = self.data[channel_id]
            
            # إرسال الصورة كـ رابط (الديسكورد سيقوم بعرضها تلقائياً كصورة في الروم)
            try:
                await message.channel.send(image_url)
            except discord.Forbidden:
                pass # في حال لم يكن للبوت صلاحية إرسال رسائل في الروم

async def setup(bot):
    await bot.add_cog(AutoLine(bot))