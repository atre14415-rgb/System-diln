import discord
from discord.ext import commands
import hashlib
import json
import os

class ImageProtection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ضع أيدي روم اللوق هنا
        self.log_channel_id = 1522756375283892245 
        
        # ملفات قاعدة البيانات (JSON)
        self.banned_images_file = "banned_images.json"
        self.blacklist_file = "blacklist.json"

        # تحميل البيانات عند تشغيل الكوج
        self.banned_hashes = self.load_data(self.banned_images_file, [])
        self.blacklisted_users = self.load_data(self.blacklist_file, [])

    def load_data(self, filename, default_data):
        """دالة مساعدة لتحميل البيانات من ملفات JSON"""
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default_data

    def save_data(self, filename, data):
        """دالة مساعدة لحفظ البيانات في ملفات JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        # تجاهل رسائل البوتات
        if message.author.bot:
            return

        # التحقق مما إذا كانت الرسالة تحتوي على مرفقات (صور)
        if message.attachments:
            for attachment in message.attachments:
                # التأكد أن المرفق عبارة عن صورة
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    # قراءة بيانات الصورة وتحويلها إلى Hash
                    image_bytes = await attachment.read()
                    image_hash = hashlib.sha256(image_bytes).hexdigest()

                    # إذا كان الهاش الخاص بالصورة موجوداً في قائمة المنع
                    if image_hash in self.banned_hashes:
                        
                        # 1. مسح الرسالة (يمنعها)
                        try:
                            await message.delete()
                        except discord.Forbidden:
                            pass # البوت لا يملك صلاحية الحذف

                        # 2. تسجيل المستخدم في البلاك لست
                        if message.author.id not in self.blacklisted_users:
                            self.blacklisted_users.append(message.author.id)
                            self.save_data(self.blacklist_file, self.blacklisted_users)

                        # 3. إرسال تنبيه في روم اللوق
                        log_channel = self.bot.get_channel(self.log_channel_id)
                        if log_channel:
                            embed = discord.Embed(
                                title="🚨 تم اكتشاف صورة ممنوعة!",
                                description=f"**المستخدم:** {message.author.mention}\n**الروم:** {message.channel.mention}",
                                color=discord.Color.red()
                            )
                            embed.set_thumbnail(url=message.author.display_avatar.url)
                            embed.set_footer(text=f"User ID: {message.author.id} | أضيف للبلاك لست")
                            await log_channel.send(embed=embed)
                        
                        # التوقف عن فحص باقي المرفقات في نفس الرسالة (تجنباً للتكرار)
                        return 

    @commands.command(name="منع_صورة")
    @commands.has_permissions(administrator=True)
    async def block_image(self, ctx):
        """أمر مخصص للإدارة لإضافة صورة جديدة إلى قائمة المنع"""
        if not ctx.message.attachments:
            await ctx.send("⚠️ الرجاء إرفاق الصورة المراد حظرها مع هذا الأمر.")
            return

        added_count = 0
        for attachment in ctx.message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_bytes = await attachment.read()
                image_hash = hashlib.sha256(image_bytes).hexdigest()

                if image_hash not in self.banned_hashes:
                    self.banned_hashes.append(image_hash)
                    added_count += 1

        if added_count > 0:
            self.save_data(self.banned_images_file, self.banned_hashes)
            await ctx.send(f"✅ تم إضافة {added_count} صورة إلى قائمة المنع بنجاح.")
        else:
            await ctx.send("ℹ️ هذه الصورة موجودة بالفعل في قائمة المنع.")

async def setup(bot):
    await bot.add_cog(ImageProtection(bot))