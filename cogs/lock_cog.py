import discord
from discord.ext import commands
from discord import app_commands

# ⚠️ آيدي سيرفرك (نفس اللي استخدمناه سابقاً)
MY_GUILD = discord.Object(id=1518871277740228608) 

class LockSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. أمر إغلاق جميع الرومات (Lock All)
    @app_commands.command(name="lockall", description="إغلاق جميع الرومات النصية في السيرفر")
    @app_commands.default_permissions(manage_channels=True) # مخصص لمن يملك صلاحية إدارة الرومات
    @app_commands.guilds(MY_GUILD)
    async def lockall(self, interaction: discord.Interaction):
        # نستخدم defer لأن العملية قد تستغرق بضع ثوانٍ ولا نريد أن ينهار الأمر
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        locked_count = 0
        
        # حلقة تكرار تمر على جميع الرومات النصية
        for channel in guild.text_channels:
            # نجلب الصلاحيات الحالية لرتبة @everyone
            overwrite = channel.overwrites_for(guild.default_role)
            
            # إذا لم يكن الروم مغلقاً بالفعل، قم بإغلاقه
            if overwrite.send_messages != False:
                overwrite.send_messages = False
                try:
                    await channel.set_permissions(guild.default_role, overwrite=overwrite)
                    locked_count += 1
                except discord.Forbidden:
                    # يتجاهل الرومات التي لا يملك البوت صلاحية لتعديلها
                    pass 
                    
        await interaction.followup.send(f"🔒 **حالة طوارئ:** تم إغلاق `{locked_count}` روم بنجاح ومنع الأعضاء من الكتابة.")

    # 2. أمر فتح جميع الرومات (Unlock All)
    @app_commands.command(name="unlockall", description="فتح جميع الرومات النصية في السيرفر")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guilds(MY_GUILD)
    async def unlockall(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        unlocked_count = 0
        
        for channel in guild.text_channels:
            overwrite = channel.overwrites_for(guild.default_role)
            
            # إذا كان الروم مغلقاً، قم بفتحه (إعادة الصلاحية للوضع الافتراضي None)
            if overwrite.send_messages == False:
                overwrite.send_messages = None 
                try:
                    await channel.set_permissions(guild.default_role, overwrite=overwrite)
                    unlocked_count += 1
                except discord.Forbidden:
                    pass
                    
        await interaction.followup.send(f"🔓 **تم إنهاء حالة الطوارئ:** تم فتح `{unlocked_count}` روم بنجاح وعادت الصلاحيات لطبيعتها.")

# دالة التشغيل
async def setup(bot):
    await bot.add_cog(LockSystem(bot))