import discord
from discord.ext import commands
import time

class AntiSpamSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ذاكرة البوت المؤقتة لحفظ رسائل الأعضاء
        # الشكل: {(آيدي العضو, آيدي الروم): [(رسالة, وقت), (رسالة, وقت)]}
        self.user_messages = {}
        
        # ⚠️ الإعدادات:
        self.time_window = 4.0  # الوقت بالثواني (إذا أرسل خلال 4 ثواني)
        self.max_messages = 3   # عدد الرسائل اللي تعتبر سبام

    @commands.Cog.listener()
    async def on_message(self, message):
        # تجاهل البوتات ورسائل الخاص
        if message.author.bot or not message.guild:
            return
            
        # حصانة الإدارة: البوت يتجاهل أي شخص عنده صلاحية "إدارة الرسائل"
        if message.author.guild_permissions.manage_messages:
            return

        user_id = message.author.id
        channel_id = message.channel.id
        current_time = time.time()
        
        # مفتاح خاص لكل عضو في كل روم
        key = (user_id, channel_id)

        # إنشاء سجل للعضو إذا لم يكن موجوداً
        if key not in self.user_messages:
            self.user_messages[key] = []

        # إضافة الرسالة الحالية ووقت إرسالها للسجل
        self.user_messages[key].append((message, current_time))

        # تنظيف السجل من الرسائل القديمة (اللي مر عليها أكثر من 4 ثواني)
        self.user_messages[key] = [
            (msg, msg_time) for msg, msg_time in self.user_messages[key] 
            if current_time - msg_time <= self.time_window
        ]

        # 🚨 التحقق: هل وصل العضو لـ 3 رسائل في هذا الوقت القصير؟
        if len(self.user_messages[key]) >= self.max_messages:
            # استخراج الرسائل لمسحها
            messages_to_delete = [msg for msg, msg_time in self.user_messages[key]]
            
            try:
                # مسح الرسائل دفعة واحدة (Bulk Delete) وهي أسرع طريقة في ديسكورد
                await message.channel.delete_messages(messages_to_delete)
                
                # تصفير سجل العضو عشان يقدر يكتب من جديد بشكل طبيعي
                self.user_messages[key] = []
                
                # رسالة تنبيه سريعة تظهر وتنحذف بعد 3 ثواني (اختياري، تقدر تحذفها لو تبي صمت تام)
                warning = await message.channel.send(f"⚠️ {message.author.mention} الرجاء عدم إرسال رسائل متكررة بسرعة (سبام).", delete_after=3.0)
                
            except discord.Forbidden:
                pass # البوت لا يملك صلاحية المسح في هذا الروم
            except discord.HTTPException:
                pass # خطأ عام في ديسكورد

async def setup(bot):
    await bot.add_cog(AntiSpamSystem(bot))