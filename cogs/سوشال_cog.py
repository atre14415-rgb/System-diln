import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import aiohttp
import asyncio

# ---------------------------------------------------------
# واجهة الأزرار (View) لزر "شاهد الآن"
# ---------------------------------------------------------
class WatchView(discord.ui.View):
    def __init__(self, url: str):
        super().__init__()
        # إضافة زر برابط يوجه المستخدم مباشرة للمقطع أو البث
        self.add_item(discord.ui.Button(label="شاهد الآن", url=url, style=discord.ButtonStyle.link))

# ---------------------------------------------------------
# كلاس الـ Cog الأساسي
# ---------------------------------------------------------
class SocialTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_conn = sqlite3.connect("social_accounts.db")
        self.cursor = self.db_conn.cursor()
        self.setup_database()
        
        # تشغيل حلقة التتبع (Task Loop)
        self.check_socials.start()

    def setup_database(self):
        """إنشاء الجداول إذا لم تكن موجودة"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trackers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                platform TEXT,
                account_id TEXT,
                last_post_id TEXT
            )
        ''')
        self.db_conn.commit()

    def cog_unload(self):
        """إيقاف المهام وإغلاق قاعدة البيانات عند إيقاف الـ Cog"""
        self.check_socials.cancel()
        self.db_conn.close()

    # ---------------------------------------------------------
    # أمر السلاش (Slash Command) لإضافة حساب للتتبع
    # ---------------------------------------------------------
    @app_commands.command(name="track", description="تفعيل تتبع بثوث ومقاطع تيك توك، تويتش، ويوتيوب")
    @app_commands.describe(platform="اختر المنصة", account_id="ايدي الحساب أو اسم المستخدم", channel="القناة التي سيتم إرسال الإشعار فيها")
    @app_commands.choices(platform=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Twitch", value="twitch"),
        app_commands.Choice(name="TikTok", value="tiktok")
    ])
    @app_commands.default_permissions(manage_channels=True)
    async def track_account(self, interaction: discord.Interaction, platform: app_commands.Choice[str], account_id: str, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        
        # حفظ البيانات في قاعدة البيانات
        self.cursor.execute('''
            INSERT INTO trackers (guild_id, channel_id, platform, account_id, last_post_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (interaction.guild.id, target_channel.id, platform.value, account_id, "NONE"))
        self.db_conn.commit()

        embed = discord.Embed(
            title="✅ تم تفعيل التتبع بنجاح",
            description=f"**المنصة:** {platform.name}\n**الحساب:** `{account_id}`\n**القناة:** {target_channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------------------------------------------------------
    # حلقة التتبع (تعمل كل 3 دقائق للتحقق من الجديد)
    # ---------------------------------------------------------
    @tasks.loop(minutes=3)
    async def check_socials(self):
        """فحص جميع الحسابات في قاعدة البيانات بكفاءة"""
        self.cursor.execute('SELECT id, guild_id, channel_id, platform, account_id, last_post_id FROM trackers')
        trackers = self.cursor.fetchall()

        async with aiohttp.ClientSession() as session:
            for row in trackers:
                db_id, guild_id, channel_id, platform, account_id, last_post_id = row
                
                try:
                    # بناءً على المنصة، يتم استدعاء الـ API الخاص بها
                    if platform == "youtube":
                        await self.check_youtube(session, db_id, channel_id, account_id, last_post_id)
                    elif platform == "twitch":
                        await self.check_twitch(session, db_id, channel_id, account_id, last_post_id)
                    elif platform == "tiktok":
                        await self.check_tiktok(session, db_id, channel_id, account_id, last_post_id)
                        
                except Exception as e:
                    print(f"[Error] Failed to check {platform} for {account_id}: {e}")
                    
                # وضع انتظار بسيط جداً لتجنب الـ Rate Limit الخاص بـ APIs
                await asyncio.sleep(0.5)

    @check_socials.before_loop
    async def before_check_socials(self):
        await self.bot.wait_until_ready()

    # ---------------------------------------------------------
    # دوال التحقق الخاصة بكل منصة والتنبيه (API Handlers)
    # ---------------------------------------------------------
    async def send_notification(self, channel_id: int, title: str, description: str, image_url: str, post_url: str, platform_color: discord.Color):
        """دالة موحدة لإرسال الإيمبد بالصيغة المطلوبة"""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=platform_color
        )
        # وضع الصورة/الخلفية في أسفل الإيمبد
        embed.set_image(url=image_url)

        # إضافة زر "شاهد الآن" أسفل الإيمبد
        view = WatchView(url=post_url)

        await channel.send(embed=embed, view=view)

    async def update_last_post(self, db_id: int, new_post_id: str):
        """تحديث آخر مقطع/بث في قاعدة البيانات لعدم تكرار الإرسال"""
        self.cursor.execute('UPDATE trackers SET last_post_id = ? WHERE id = ?', (new_post_id, db_id))
        self.db_conn.commit()

    # -- [ دوال الـ APIs ] --
    # ملاحظة: قم بوضع مفاتيح الـ API الخاصة بك (API Keys) في الروابط أدناه
    
    async def check_youtube(self, session, db_id, channel_id, account_id, last_post_id):
        # YOUTUBE_API_KEY = "ضع_مفتاحك_هنا"
        # مثال لطلب API (يجب تعديله ليتناسب مع مفتاحك البرمجي):
        # url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={account_id}&part=snippet,id&order=date&maxResults=1"
        
        # محاكاة لبيانات راجعة:
        latest_video_id = "DummyVideoID" 
        if latest_video_id != last_post_id and last_post_id != "NONE":
            await self.send_notification(
                channel_id=channel_id,
                title="🔴 فيديو جديد على يوتيوب!", # عنوان المقطع
                description="شرح الفيديو يكتب هنا...", # وصف المقطع
                image_url="https://dummyimage.com/1280x720/000/fff&text=Youtube+Thumbnail", # الصورة المصغرة
                post_url=f"https://www.youtube.com/watch?v={latest_video_id}",
                platform_color=discord.Color.red()
            )
        await self.update_last_post(db_id, latest_video_id)

    async def get_twitch_token(self, session, client_id, client_secret):
        """دالة مساعدة لجلب التوكن الخاص بتويتش"""
        url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
        async with session.post(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("access_token")
            return None

    async def check_twitch(self, session, db_id, channel_id, account_id, last_post_id):
        # 1. ضع معلومات تطبيق تويتش الخاص بك هنا
        client_id = "ضع_Client_ID_هنا"
        client_secret = "ضع_Client_Secret_هنا"

        # 2. جلب التوكن (ملاحظة: في المشاريع المتقدمة يفضل حفظ التوكن لتقليل الطلبات)
        token = await self.get_twitch_token(session, client_id, client_secret)
        if not token:
            print("[Twitch Error] فشل في جلب التوكن.")
            return

        headers = {
            "Client-Id": client_id,
            "Authorization": f"Bearer {token}"
        }

        # 3. رابط فحص حالة البث للحساب المطلوب
        url = f"https://api.twitch.tv/helix/streams?user_login={account_id}"

        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 4. إذا كانت المصفوفة "data" تحتوي على بيانات، فهذا يعني أن البث شغال الآن (Live)
                    if data and "data" in data and len(data["data"]) > 0:
                        stream_data = data["data"][0]
                        stream_id = str(stream_data["id"])
                        
                        # 5. إذا كان ايدي البث جديداً ولم يتم إرساله مسبقاً
                        if stream_id != last_post_id and last_post_id != "NONE":
                            title = stream_data.get("title", "بث جديد!")
                            game_name = stream_data.get("game_name", "غير معروف")
                            
                            # تعديل دقة الصورة المصغرة لتكون واضحة في الإيمبد
                            thumbnail_url = stream_data["thumbnail_url"].replace("{width}", "1280").replace("{height}", "720")
                            stream_url = f"https://www.twitch.tv/{account_id}"
                            
                            await self.send_notification(
                                channel_id=channel_id,
                                title="🟣 بث تويتش مباشر الآن!",
                                description=f"**العنوان:** {title}\n**يلعب الآن:** {game_name}",
                                image_url=thumbnail_url,
                                post_url=stream_url,
                                platform_color=discord.Color.purple()
                            )
                        
                        # تحديث قاعدة البيانات بايدي البث الحالي
                        await self.update_last_post(db_id, stream_id)
        except Exception as e:
            print(f"[Twitch Check Error] {e}")

    async def check_tiktok(self, session, db_id, channel_id, account_id, last_post_id):
    # مثال باستخدام أحد الـ APIs المتوفرة في RapidAPI
    url = "https://tiktok-scraper7.p.rapidapi.com/user/posts"
    querystring = {"user_id": account_id, "count": "1"} # جلب أحدث مقطع
    
    headers = {
        "X-RapidAPI-Key": "ضع_مفتاح_الـ_API_هنا",
        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
    }

    try:
        async with session.get(url, headers=headers, params=querystring) as response:
            if response.status == 200:
                data = await response.json()
                
                # التحقق من وجود مقاطع
                if data and "data" in data and len(data["data"]["videos"]) > 0:
                    latest_video = data["data"]["videos"][0]
                    latest_video_id = str(latest_video["video_id"])
                    
                    # إذا كان المقطع جديداً ولم يتم إرساله من قبل
                    if latest_video_id != last_post_id and last_post_id != "NONE":
                        video_url = f"https://www.tiktok.com/@{account_id}/video/{latest_video_id}"
                        thumbnail = latest_video.get("cover", "https://dummyimage.com/1280x720/000/fff&text=TikTok")
                        title = latest_video.get("title", "مقطع تيك توك جديد!")
                        
                        await self.send_notification(
                            channel_id=channel_id,
                            title="🎵 مقطع تيك توك جديد!",
                            description=title,
                            image_url=thumbnail,
                            post_url=video_url,
                            platform_color=discord.Color.dark_theme()
                        )
                    
                    # تحديث قاعدة البيانات بآخر مقطع
                    await self.update_last_post(db_id, latest_video_id)
            else:
                print(f"[TikTok API Error] Status Code: {response.status}")
    except Exception as e:
        print(f"[TikTok Check Error] {e}")
# ---------------------------------------------------------
# دالة التحميل الأساسية للـ Cog
# ---------------------------------------------------------
async def setup(bot):
    await bot.add_cog(SocialTracker(bot))