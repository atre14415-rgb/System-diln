import discord
from discord.ext import commands
import re
import asyncio

class SecuritySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # نمط ذكي لاكتشاف الروابط (يكتشف http, https, www, discord.gg وغيرها)
        self.link_regex = re.compile(r'(https?://\S+)|(discord\.gg/\S+)|(www\.\S+)')
        
        # صيغ الملفات الخطيرة والملغمة اللي يستخدمونها الهكر (يمنعها البوت فوراً)
        self.bad_extensions = ['.exe', '.scr', '.bat', '.cmd', '.vbs', '.js', '.zip', '.rar']

    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. تجاهل رسائل البوتات (عشان ما يمسح رسائل البوت نفسه) وتجاهل رسائل الخاص
        if message.author.bot or not message.guild:
            return

        # 2. حصانة الإدارة: إذا الشخص عنده صلاحية "أدمن" البوت ما راح يتدخل في رسائله
        if message.author.guild_permissions.administrator:
            return

        is_violating = False
        reason = ""

        # 3. فحص الرسالة هل تحتوي على رابط؟
        if self.link_regex.search(message.content):
            is_violating = True
            reason = "إرسال الروابط ممنوع"

        # 4. فحص المرفقات (الصور والملفات)
        if message.attachments:
            for attachment in message.attachments:
                # إذا كانت صيغة الملف خطيرة وملغمة
                if any(attachment.filename.lower().endswith(ext) for ext in self.bad_extensions):
                    is_violating = True
                    reason = "إرسال ملفات مشبوهة أو ملغمة"
                    break

        # 5. تنفيذ العقوبة (مسح الرسالة والتحذير)
        if is_violating:
            try:
                # مسح رسالة الهكر أو المخالف
                await message.delete()
                
                # إرسال تحذير في الشات
                warning_msg = await message.channel.send(f"⚠️ {message.author.mention} تم مسح رسالتك! **السبب:** {reason}.")
                
                # مسح التحذير بعد 5 ثواني عشان ما يتلوث الشات
                await asyncio.sleep(5)
                await warning_msg.delete()
                
            except discord.Forbidden:
                # يتجاهل الخطأ إذا البوت ما عنده صلاحية في هذا الروم
                pass

# دالة التشغيل
async def setup(bot):
    await bot.add_cog(SecuritySystem(bot))