import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class AdvancedApplications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.apply_channel = None
        self.log_channel = None
        self.questions = []

    # ------------------------------------
    # ⚙️ إعداد نموذج التقديم
    # ------------------------------------
    @app_commands.command(
        name="apply_setup",
        description="🔧 إعداد نموذج التقديم (حدد روم التقديم + روم لوق + عدد أسئلة)"
    )
    @app_commands.describe(
        apply_channel="القناة التي تظهر فيها زر التقديم",
        log_channel="القناة التي ترسل فيها طلبات الإدارة (اللوق)",
        q1="السؤال الأول",
        q2="السؤال الثاني",
        q3="السؤال الثالث",
        q4="السؤال الرابع",
        q5="السؤال الخامس"
    )
    async def apply_setup(
        self,
        interaction: discord.Interaction,
        apply_channel: discord.TextChannel,
        log_channel: discord.TextChannel,
        q1: str,
        q2: str,
        q3: Optional[str],
        q4: Optional[str] = None,
        q5: Optional[str] = None
    ):
        self.apply_channel = apply_channel
        self.log_channel = log_channel
        # حفظ الأسئلة في قائمة
        self.questions = [q1, q2]
        if q3: self.questions.append(q3)
        if q4: self.questions.append(q4)
        if q5: self.questions.append(q5)

        # إنشاء الزر
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(label="📄 قدم الآن", style=discord.ButtonStyle.primary)

        async def button_callback(btn_inter: discord.Interaction):
            await btn_inter.response.send_modal(ApplicationForm(self.questions))

        button.callback = button_callback
        view.add_item(button)

        # إرسال Embed في قناة التقديم
        await apply_channel.send(
            embed=discord.Embed(
                title="📢 نموذج تقديم جديد",
                description="اضغط الزر لبدء التقديم",
                color=discord.Color.blue()
            ),
            view=view
        )

        await interaction.response.send_message(
            f"✅ تم إعداد نموذج التقديم في {apply_channel.mention} و اللوق في {log_channel.mention}",
            ephemeral=True
        )

    # ------------------------------------
    # التعامل مع الطلب بعد الإرسال
    # ------------------------------------
    async def send_to_log(self, user: discord.Member, answers: list[str]):
        # إنشاء Embed للادارة
        embed = discord.Embed(
            title="📨 طلب تقديم جديد",
            description=f"🧑‍💻 من: {user.mention}",
            color=discord.Color.gold()
        )
        # إضافة كل سؤال وإجابته
        for q, a in zip(self.questions, answers):
            embed.add_field(name=q, value=a, inline=False)

        # إضافة View مع أزرار قبول/رفض
        view = discord.ui.View(timeout=None)

        btn_accept = discord.ui.Button(label="✔ قبول", style=discord.ButtonStyle.success)
        async def accept_cb(i: discord.Interaction):
            # إرسال DM للعضو بالقبول
            dm_embed = discord.Embed(
                title="✅ تم قبول طلبك!",
                description="🎉 تهانينا، تم قبول طلبك بنجاح!",
                color=discord.Color.green()
            )
            await user.send(embed=dm_embed)
            await i.response.edit_message(content="✔ تم قبول الطلب", embed=embed, view=None)

        btn_accept.callback = accept_cb
        view.add_item(btn_accept)

        btn_reject = discord.ui.Button(label="❌ رفض", style=discord.ButtonStyle.danger)
        async def reject_cb(i: discord.Interaction):
            dm_embed = discord.Embed(
                title="❌ تم رفض طلبك",
                description="نأسف، لكن طلبك قوبل بالرفض.",
                color=discord.Color.red()
            )
            await user.send(embed=dm_embed)
            await i.response.edit_message(content="❌ تم رفض الطلب", embed=embed, view=None)

        btn_reject.callback = reject_cb
        view.add_item(btn_reject)

        # إرسال Embed + الأزرار إلى قناة اللوق
        await self.log_channel.send(embed=embed, view=view)


class ApplicationForm(discord.ui.Modal):
    def __init__(self, questions: list[str]):
        super().__init__(title="📄 نموذج التقديم")

        self.questions = questions
        for q in questions:
            self.add_item(discord.ui.TextInput(label=q))

    async def on_submit(self, interaction: discord.Interaction):
        answers = [item.value for item in self.children]
        cog: AdvancedApplications = interaction.client.get_cog("AdvancedApplications")
        await cog.send_to_log(interaction.user, answers)
        await interaction.response.send_message(
            "📬 تم إرسال طلبك بنجاح!", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(AdvancedApplications(bot))