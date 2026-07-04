import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class WordFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "filter_data.json"
        self.data = self.load_data()

    def load_data(self):
        """تحميل الإعدادات وقائمة الكلمات الممنوعة من ملف JSON"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        # إذا لم يكن الملف موجوداً، يتم إنشاء هيكل بيانات افتراضي
        return {"log_channel": None, "bad_words": []}

    def save_data(self):
        """حفظ التعديلات في ملف JSON"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    # 1. أمر تسطيب روم اللوق
    @app_commands.command(name="تسطيب_المنع", description="تحديد الروم الذي سترسل إليه تنبيهات الكلمات الممنوعة")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_log(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.data["log_channel"] = channel.id
        self.save_data()
        await interaction.response.send_message(f"✅ تم تعيين روم اللوق بنجاح إلى {channel.mention}", ephemeral=True)

    # 2. أمر إضافة كلمة ممنوعة
    @app_commands.command(name="منع_كلمة", description="إضافة كلمة جديدة لقائمة الممنوعات")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_word(self, interaction: discord.Interaction, word: str):
        if word in self.data["bad_words"]:
            await interaction.response.send_message("⚠️ هذه الكلمة موجودة مسبقاً في القائمة.", ephemeral=True)
            return
        
        self.data["bad_words"].append(word)
        self.save_data()
        await interaction.response.send_message(f"✅ تم إضافة `{word}` إلى قائمة الممنوعات.", ephemeral=True)

    # 3. أمر حذف كلمة ممنوعة
    @app_commands.command(name="حذف_ممنوع", description="إزالة كلمة من قائمة الممنوعات")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_word(self, interaction: discord.Interaction, word: str):
        if word not in self.data["bad_words"]:
            await interaction.response.send_message("⚠️ هذه الكلمة غير موجودة في القائمة أساساً.", ephemeral=True)
            return
        
        self.data["bad_words"].remove(word)
        self.save_data()
        await interaction.response.send_message(f"✅ تم حذف `{word}` من قائمة الممنوعات.", ephemeral=True)

    # 4. أمر عرض الكلمات الممنوعة
    @app_commands.command(name="عرض_الممنوعات", description="عرض جميع الكلمات المحظورة حالياً")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_words(self, interaction: discord.Interaction):
        words = self.data["bad_words"]
        if not words:
            await interaction.response.send_message("📄 قائمة الممنوعات فارغة حالياً.", ephemeral=True)
            return
        
        # تنسيق الكلمات في قائمة
        words_str = "\n".join([f"- {w}" for w in words])
        embed = discord.Embed(
            title="🚫 قائمة الكلمات الممنوعة", 
            description=words_str, 
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 5. مستمع الرسائل لاكتشاف الكلمات وحذفها
    @commands.Cog.listener()
    async def on_message(self, message):
        # تجاهل رسائل البوتات
        if message.author.bot:
            return

        bad_words = self.data.get("bad_words", [])
        detected_word = None

        # التحقق مما إذا كانت أي كلمة ممنوعة موجودة داخل الرسالة
        for word in bad_words:
            if word in message.content:
                detected_word = word
                break

        if detected_word:
            # 1. مسح الرسالة
            try:
                await message.delete()
            except discord.Forbidden:
                pass # البوت لا يملك صلاحية الحذف

            # 2. إرسال تنبيه في روم اللوق
            log_channel_id = self.data.get("log_channel")
            if log_channel_id:
                log_channel = self.bot.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="🚨 تم اكتشاف كلمة ممنوعة!",
                        description=f"**المستخدم:** {message.author.mention}\n**الروم:** {message.channel.mention}\n**الرسالة الأصلية:**\n{message.content}",
                        color=discord.Color.orange()
                    )
                    embed.set_footer(text=f"User ID: {message.author.id} | الكلمة المكتشفة: {detected_word}")
                    await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(WordFilter(bot))