import discord
from discord import app_commands
from discord.ext import commands

class AdminTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

   
    # فك الباند
    @app_commands.command(name="unban", description="فك حظر عضو")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        user = await self.bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ تم فك الحظر عن {user.mention}")

   

    # مسح
    @app_commands.command(name="clear", description="مسح عدد من الرسائل")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"🧹 تم مسح {amount} رسالة")

  

    # سحب عضو صوتي
    @app_commands.command(name="move", description="سحب عضو من روم صوتي")
    @app_commands.checks.has_permissions(move_members=True)
    async def move(self, interaction: discord.Interaction, member: discord.Member, target: discord.VoiceChannel):
        if not member.voice or not member.voice.channel:
            return await interaction.response.send_message(f"❌ {member.mention} مو في روم صوتي")
        await member.move_to(target)
        await interaction.response.send_message(f"🎧 تم سحب {member.mention} إلى {target.mention}")

    # سحب كل الأعضاء من روم صوتي
    @app_commands.command(name="moveall", description="سحب كل الأعضاء من روم صوتي")
    @app_commands.checks.has_permissions(move_members=True)
    async def moveall(self, interaction: discord.Interaction, source: discord.VoiceChannel, target: discord.VoiceChannel):
        for mem in source.members:
            await mem.move_to(target)
        await interaction.response.send_message(f"🔄 تم نقل جميع الأعضاء من {source.mention} إلى {target.mention}")

async def setup(bot):
    await bot.add_cog(AdminTools(bot))