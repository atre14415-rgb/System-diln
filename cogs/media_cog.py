import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os
from curl_cffi import requests # مكتبة تيك توك

class LinkModal(discord.ui.Modal, title="إدخال الرابط"):
    url = discord.ui.TextInput(
        label="رابط المقطع",
        style=discord.TextStyle.paragraph,
        placeholder="ضع الرابط هنا...",
        required=True,
    )

    def __init__(self, select_menu):
        super().__init__()
        self.select_menu = select_menu

    async def on_submit(self, interaction: discord.Interaction):
        platform = self.select_menu.values[0]
        await interaction.response.send_message(f"⏳ جاري معالجة رابط {platform}، لحظات...", ephemeral=True)
        
        file_path = await self.select_menu.download_video(self.url.value, platform)

        if file_path == "size_limit":
            await interaction.followup.send("❌ المقطع يتجاوز 25 ميجابايت.", ephemeral=True)
        elif file_path:
            file = discord.File(file_path)
            await interaction.followup.send(file=file, ephemeral=False)
            os.remove(file_path)
        else:
            await interaction.followup.send("❌ فشل التحميل. تأكد من الرابط أو خصوصية الحساب.", ephemeral=True)

class DownloadSelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            # تم حذف يوتيوب من هنا
            discord.SelectOption(label="تيك توك", description="تحميل مقطع بدون علامة مائية", emoji="⬛", value="tiktok"),
            discord.SelectOption(label="انستغرام", description="تحميل Reels", emoji="🟪", value="instagram"),
            discord.SelectOption(label="سناب شات", description="تحميل مقاطع Spotlight", emoji="🟨", value="snapchat")
        ]
        super().__init__(placeholder="📥 اختر المنصة لتحميل المقطع...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LinkModal(self))

    async def download_video(self, url, platform):
        def process_download():
            if not os.path.exists('downloads'):
                os.makedirs('downloads')

            # منطق خاص لتيك توك (بدون علامة مائية)
            if platform == "tiktok":
                # استخدام curl_cffi للتنكر كمتصفح وتجاوز حماية تيك توك
                ydl_opts = {
                    'outtmpl': 'downloads/%(id)s.%(ext)s',
                    'extractor_args': {'tiktok': {'impersonate': 'chrome110'}},
                    'format': 'best',
                }
            else:
                # إعدادات انستغرام وسناب شات
                ydl_opts = {
                    'outtmpl': 'downloads/%(id)s.%(ext)s',
                    'format': 'best',
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    return filename
                except Exception:
                    return None

        return await asyncio.to_thread(process_download)

class DownloadView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(DownloadSelect(bot))

class MediaDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="media", aliases=["dl", "تحميل"])
    async def media_menu(self, ctx):
        embed = discord.Embed(
            title="🎥 محطة تحميل المقاطع",
            description="اختر المنصة (تمت إزالة يوتيوب):",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=DownloadView(self.bot))

async def setup(bot):
    await bot.add_cog(LogsCog(bot))