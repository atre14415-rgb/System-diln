import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import datetime

# ⚠️ آيدي سيرفرك للظهور السريع للأوامر
MY_GUILD = discord.Object(id=1518871277740228608) 

class GiveawaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="giveaway", description="إنشاء سحب/قرعة على جائزة في السيرفر")
    @app_commands.describe(
        prize="اسم الجائزة (مثل: نيترو، 100 ألف كريدت)",
        minutes="مدة السحب بالدقائق",
        winners_count="عدد الفائزين (الافتراضي فائز واحد)"
    )
    @app_commands.default_permissions(manage_events=True) # الصلاحية المطلوبة (إدارة الأحداث/السيرفر)
    @app_commands.guilds(MY_GUILD)
    async def giveaway(self, interaction: discord.Interaction, prize: str, minutes: int, winners_count: int = 1):
        # التأكد من أن الوقت المدخل منطقي
        if minutes < 1:
            return await interaction.response.send_message("❌ الوقت يجب أن يكون دقيقة واحدة على الأقل.", ephemeral=True)

        # حساب وقت الانتهاء بدقة
        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
        end_timestamp = int(end_time.timestamp())

        # تجهيز رسالة السحب (الإيمبد)
        embed = discord.Embed(
            title="🎉 سحب جديـــد! 🎉",
            description=(
                f"**🎁 الجائزة:** {prize}\n\n"
                f"اضغط على التفاعل 🎉 بالأسفل للمشاركة!\n\n"
                f"⏳ **ينتهي:** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)\n"
                f"🏆 **عدد الفائزين:** `{winners_count}`"
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"بواسطة: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        # الرد المخفي للمشرف لتأكيد العملية
        await interaction.response.send_message("✅ تم إطلاق السحب بنجاح في هذا الروم!", ephemeral=True)
        
        # إرسال السحب الفعلي في الروم وإضافة الرياكشن
        giveaway_msg = await interaction.channel.send(embed=embed)
        await giveaway_msg.add_reaction("🎉")

        # ⏳ جعل البوت ينتظر في الخلفية حتى ينتهي الوقت
        await asyncio.sleep(minutes * 60)

        # 🔄 جلب الرسالة المحدثة من ديسكورد للتأكد من عدد الرياكشنات الفعلي
        try:
            fetched_msg = await interaction.channel.fetch_message(giveaway_msg.id)
        except discord.NotFound:
            # إذا قام شخص بمسح رسالة السحب قبل أن ينتهي الوقت
            return

        # البحث عن تفاعل 🎉 وتخزين المشاركين
        reaction = discord.utils.get(fetched_msg.reactions, emoji="🎉")
        if not reaction:
            return

        # جلب قائمة المشاركين (مع استبعاد البوت نفسه من السحب)
        users = [user async for user in reaction.users() if not user.bot]

        # التحقق إذا لم يشارك أحد
        if len(users) == 0:
            failed_embed = discord.Embed(
                title="🛑 تم إلغاء السحب!",
                description=f"**🎁 الجائزة:** {prize}\nلم يقم أي شخص بالمشاركة في هذا السحب.",
                color=discord.Color.red()
            )
            await fetched_msg.edit(embed=failed_embed)
            return await interaction.channel.send(f"⚠️ انتهى السحب على **{prize}** ولم يشارك أحد!")

        # اختيار الفائزين عشوائياً (بحيث لا يتجاوز العدد الفعلي للمشاركين)
        actual_winners_count = min(winners_count, len(users))
        winners = random.sample(users, actual_winners_count)
        
        # تجهيز منشن الفائزين
        winners_mentions = ", ".join(w.mention for w in winners)

        # تعديل رسالة السحب الأساسية لإظهار أنها انتهت
        ended_embed = discord.Embed(
            title="🎊 انتهى السحب! 🎊",
            description=f"**🎁 الجائزة:** {prize}\n🏆 **الفائزين:** {winners_mentions}",
            color=discord.Color.dark_grey()
        )
        await fetched_msg.edit(embed=ended_embed)

        # إعلان الفائزين وإرسال رابط ينقلهم لرسالة السحب الأصلية
        await interaction.channel.send(
            f"🎉 مبروووك {winners_mentions}! لقد فزت بـ **{prize}**! \n[🔗 اضغط هنا للانتقال لرسالة السحب]({fetched_msg.jump_url})"
        )

async def setup(bot):
    await bot.add_cog(GiveawaySystem(bot))