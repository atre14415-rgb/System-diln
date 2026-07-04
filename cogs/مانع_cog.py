import discord
from discord.ext import commands

class ImageModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 🔴 ضع هنا أيدي الروم الذي يمنع فيه إرسال أي صورة تماماً
        self.restricted_channel_id = 1522363080779239454  
        
        # 🔴 ضع هنا أيدي روم اللوق (السجل)
        self.log_channel_id = 1517015117160513726         

    @commands.Cog.listener()
    async def on_message(self, message):
        # تجاهل رسائل البوتات حتى لا يدخل البوت في حلقة لا نهائية
        if message.author.bot:
            return

        # حساب عدد الصور المرفقة في الرسالة
        image_count = sum(1 for att in message.attachments if att.content_type and att.content_type.startswith('image/'))

        # إذا لم يكن هناك أي صور، تجاهل الرسالة وتخطى الكود
        if image_count == 0:
            return

        deleted = False
        reason = ""

        # الشرط الأول: حذف أي صورة في الروم المحدد الممنوع
        if message.channel.id == self.restricted_channel_id:
            try:
                await message.delete()
                deleted = True
                reason = "إرسال صورة في روم يُمنع فيه إرسال الصور نهائياً."
            except discord.Forbidden:
                pass # البوت لا يملك صلاحيات الحذف في هذا الروم
                
        # الشرط الثاني: منع إرسال 3 صور أو أكثر في نفس الوقت (في أي روم آخر)
        elif image_count >= 3:
            try:
                await message.delete()
                deleted = True
                reason = f"إرسال {image_count} صور دفعة واحدة (يُمنع إرسال 3 صور أو أكثر في نفس الوقت)."
            except discord.Forbidden:
                pass

        # إرسال تقرير إلى روم اللوق في حال تم حذف الرسالة
        if deleted:
            log_channel = self.bot.get_channel(self.log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="🗑️ نظام حماية الصور - تم حذف رسالة",
                    color=discord.Color.red()
                )
                embed.add_field(name="👤 المستخدم:", value=message.author.mention, inline=True)
                embed.add_field(name="📍 الروم:", value=message.channel.mention, inline=True)
                embed.add_field(name="📋 السبب:", value=reason, inline=False)
                embed.set_footer(text=f"User ID: {message.author.id}")
                
                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    pass

# دالة أساسية لتفعيل الكوج داخل البوت
async def setup(bot):
    await bot.add_cog(ImageModerationCog(bot))