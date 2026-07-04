import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# تحميل المتغيرات البيئية من ملف .env (لإخفاء التوكن)
load_dotenv()

# إعداد الصلاحيات (Intents) للتحكم الكامل
intents = discord.Intents.all()

# إنشاء كائن البوت
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'🔥 تم تشغيل البوت بنجاح باسم: {bot.user.name}')
    print(f'🆔 معرف البوت: {bot.user.id}')
    print('-----------------------------------------')
    
    # 🎧 إعداد حالة البوت (Listening)
    # إذا أردتها مشاهدة بدلاً من استماع، قم بتغيير .listening إلى .watching
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Diln"))
    print("🎧 تم تعيين حالة البوت إلى: Listening to Diln")
    print('-----------------------------------------')

    # تحديث أوامر السلاش (Slash Commands)
    try:
        # 1. تحديث الأوامر العامة (تأخذ وقت لتظهر في كل السيرفرات)
        synced_global = await bot.tree.sync()
        print(f"🌍 تم عمل Sync لـ {len(synced_global)} أمر عام بنجاح!")

        # 2. تحديث أوامر السيرفر المخصص (تظهر فوراً)
        # ⚠️ استبدل الرقم بآيدي سيرفرك (نفس اللي حطيته في كوج الإدارة)
        MY_GUILD = discord.Object(id=1518871277740228608)
        synced_guild = await bot.tree.sync(guild=MY_GUILD)
        print(f"🚀 تم عمل Sync لـ {len(synced_guild)} أمر مخصص للسيرفر بنجاح!")

    except Exception as e:
        print(f"❌ خطأ أثناء الـ Sync: {e}")

# دالة لتحميل الكوجات تلقائياً
async def load_extensions():
    # التحقق من وجود المجلد، وإذا مو موجود يقوم البوت بإنشائه تلقائياً
    if not os.path.exists('./cogs'):
        os.makedirs('./cogs')
        print("📁 تم إنشاء مجلد 'cogs' تلقائياً لأنك نسيته!")
        return # نوقف الدالة هنا لأن المجلد توه جديد وأكيد بيكون فارغ

    # يبحث داخل مجلد cogs
    for filename in os.listdir('./cogs'):
        # الشرط: يحمل فقط الملفات التي تنتهي بـ _cog.py
        if filename.endswith('_cog.py'):
            # يزيل آخر 3 أحرف (.py) لاستيراد الوحدة البرمجية بشكل صحيح
            extension_name = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(extension_name)
                print(f'📦 تم تحميل الكوج: {filename}')
            except Exception as e:
                print(f'⚠️ فشل تحميل {filename}:\n{e}')

async def main():
    async with bot:
        # تحميل جميع الأوامر والملفات قبل تشغيل البوت
        await load_extensions()
        
        # استدعاء التوكن من ملف .env بأمان
        token = os.getenv("BOT_TOKEN")
        if token is None:
            print("❌ لم يتم العثور على التوكن! تأكد من إضافته في ملف .env")
            return
            
        await bot.start(token)

if __name__ == "__main__":
    # تشغيل النظام الأساسي
    asyncio.run(main())