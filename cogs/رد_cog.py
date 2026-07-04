import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# اسم الملف الذي ستحفظ فيه الردود
DATA_FILE = "auto_replies.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class AutoReplyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # 1. أمر إضافة رد تلقائي
    # ==========================================
    @app_commands.command(name="add_reply", description="إضافة رد تلقائي لكلمة معينة")
    @app_commands.describe(word="الكلمة التي سيكتبها العضو", reply="الرد الذي سيرسله البوت")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_reply(self, interaction: discord.Interaction, word: str, reply: str):
        data = load_data()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in data:
            data[guild_id] = {}
            
        data[guild_id][word] = reply
        save_data(data)
        
        embed = discord.Embed(title="✅ تم إضافة الرد بنجاح", color=discord.Color.green())
        embed.add_field(name="الكلمة (المفتاح)", value=f"`{word}`", inline=True)
        embed.add_field(name="الرد التلقائي", value=reply, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # 2. أمر حذف رد تلقائي
    # ==========================================
    @app_commands.command(name="remove_reply", description="حذف رد تلقائي موجود مسبقاً")
    @app_commands.describe(word="الكلمة المراد حذف ردها")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_reply(self, interaction: discord.Interaction, word: str):
        data = load_data()
        guild_id = str(interaction.guild.id)
        
        if guild_id in data and word in data[guild_id]:
            del data[guild_id][word]
            save_data(data)
            
            embed = discord.Embed(
                title="🗑️ تم الحذف بنجاح", 
                description=f"تم إيقاف الرد التلقائي للكلمة: `{word}`", 
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ خطأ", 
                description="هذه الكلمة غير موجودة في قائمة الردود التلقائية.", 
                color=discord.Color.dark_red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # 3. أمر عرض جميع الردود التلقائية
    # ==========================================
    @app_commands.command(name="list_replies", description="عرض جميع الردود التلقائية المضافة في السيرفر")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_replies(self, interaction: discord.Interaction):
        data = load_data()
        guild_id = str(interaction.guild.id)
        
        # التأكد إذا كان السيرفر لا يملك أي ردود
        if guild_id not in data or not data[guild_id]:
            embed = discord.Embed(
                title="📭 لا يوجد ردود", 
                description="لم يتم إضافة أي ردود تلقائية في هذا السيرفر حتى الآن.", 
                color=discord.Color.greyple()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="📋 قائمة الردود التلقائية", color=discord.Color.blue())
        
        description_text = ""
        for index, (word, reply) in enumerate(data[guild_id].items(), 1):
            line = f"**{index}.** **الكلمة:** `{word}` ➔ **الرد:** {reply}\n"
            # حماية للإيمبد من تجاوز الحد الأقصى للأحرف (4096 حرف)
            if len(description_text) + len(line) > 4000:
                description_text += "\n... (يوجد المزيد من الردود لم يتم عرضها)"
                break
            description_text += line
            
        embed.description = description_text
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # 4. مستمع الرسائل (للرد على الأعضاء)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        data = load_data()
        guild_id = str(message.guild.id)
        
        if guild_id in data:
            message_words = message.content.split()
            
            for word, reply in data[guild_id].items():
                if word in message_words:
                    await message.channel.send(reply)
                    break 

async def setup(bot):
    await bot.add_cog(AutoReplyCog(bot))