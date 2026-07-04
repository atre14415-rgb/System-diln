import discord
from discord.ext import commands
from discord import app_commands

class RolesInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roles", description="يعرض جميع رتب السيرفر وعدد الأعضاء في كل رتبة")
    async def server_roles(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        # جلب جميع الرتب باستثناء رتبة @everyone وترتيبها من الأعلى للأسفل
        roles = sorted([role for role in guild.roles if role.name != "@everyone"], 
                       key=lambda r: r.position, 
                       reverse=True)
        
        if not roles:
            await interaction.response.send_message("❌ لا توجد رتب في هذا السيرفر.", ephemeral=True)
            return

        description = ""
        total_roles = len(roles)

        for role in roles:
            member_count = len(role.members)
            line = f"{role.mention} : **{member_count}** عضو\n"
            
            # التأكد من عدم تجاوز الحد الأقصى للأحرف في الإمبد (4096 حرف)
            if len(description) + len(line) > 4000:
                description += "\n**... وهناك رتب أخرى لم يتم عرضها لتجاوز الحد الأقصى**"
                break
            
            description += line

        embed = discord.Embed(
            title=f"📊 إحصائيات الرتب في {guild.name}",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"إجمالي عدد الرتب: {total_roles}")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RolesInfo(bot))   