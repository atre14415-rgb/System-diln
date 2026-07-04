import discord
from discord.ext import commands
from discord import app_commands

# ⚠️ آيدي سيرفرك
MY_GUILD = discord.Object(id=1518871277740228608) 

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # دالة مساعدة لتحويل كود اللون (Hex) إلى لون يفهمه ديسكورد
    def parse_color(self, hex_color: str):
        try:
            hex_color = hex_color.lstrip('#')
            return discord.Color(int(hex_color, 16))
        except ValueError:
            return None

    # ================= 1. أمر إنشاء رتبة =================
    @app_commands.command(name="role-create", description="إنشاء رتبة جديدة في السيرفر")
    @app_commands.describe(
        name="اسم الرتبة الجديدة",
        color_hex="كود اللون (مثال: #ff0000) - اختياري",
        icon="صورة لتكون أيقونة الرتبة (يتطلب بوست لفل 2) - اختياري"
    )
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guilds(MY_GUILD)
    async def role_create(self, interaction: discord.Interaction, name: str, color_hex: str = None, icon: discord.Attachment = None):
        await interaction.response.defer(ephemeral=True)
        
        # تجهيز اللون
        discord_color = discord.Color.default()
        if color_hex:
            parsed = self.parse_color(color_hex)
            if parsed:
                discord_color = parsed
            else:
                return await interaction.followup.send("❌ كود اللون غير صحيح. الرجاء استخدام صيغة Hex (مثل #ff0000).", ephemeral=True)

        try:
            # قراءة الصورة إذا تم إرفاقها
            icon_bytes = await icon.read() if icon else None
            
            # إنشاء الرتبة
            new_role = await interaction.guild.create_role(
                name=name,
                color=discord_color,
                display_icon=icon_bytes,
                reason=f"تم الإنشاء بواسطة {interaction.user.name}"
            )
            
            await interaction.followup.send(f"✅ تم إنشاء الرتبة {new_role.mention} بنجاح!", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ البوت لا يملك صلاحية إدارة الرتب (Manage Roles).", ephemeral=True)
        except discord.HTTPException as e:
            # إذا كان السيرفر لا يدعم الأيقونات
            if "role_icons" in str(e).lower() or icon_bytes:
                await interaction.followup.send("⚠️ تم إنشاء الرتبة لكن **بدون أيقونة** (سيرفرك لم يصل لمستوى البوست المطلوب لدعم الأيقونات).", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ حدث خطأ: {e}", ephemeral=True)

    # ================= 2. أمر حذف رتبة =================
    @app_commands.command(name="role-delete", description="حذف رتبة من السيرفر نهائياً")
    @app_commands.describe(role="الرتبة المراد حذفها")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guilds(MY_GUILD)
    async def role_delete(self, interaction: discord.Interaction, role: discord.Role):
        # حماية: البوت لا يمكنه حذف رتبة أعلى من رتبته
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ لا يمكنني حذف هذه الرتبة لأنها أعلى أو مساوية لرتبتي.", ephemeral=True)
            
        try:
            await role.delete(reason=f"تم الحذف بواسطة {interaction.user.name}")
            await interaction.response.send_message(f"🗑️ تم حذف الرتبة `{role.name}` بنجاح.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ البوت لا يملك صلاحية لحذف هذه الرتبة.", ephemeral=True)

    # ================= 3. أمر تعديل رتبة =================
    @app_commands.command(name="role-edit", description="تعديل اسم، لون، أو أيقونة رتبة موجودة")
    @app_commands.describe(
        role="الرتبة المراد تعديلها",
        new_name="الاسم الجديد للرتبة (اختياري)",
        new_color="كود اللون الجديد (مثال: #00ff00) (اختياري)",
        new_icon="الأيقونة الجديدة (اختياري)"
    )
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guilds(MY_GUILD)
    async def role_edit(self, interaction: discord.Interaction, role: discord.Role, new_name: str = None, new_color: str = None, new_icon: discord.Attachment = None):
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ لا يمكنني تعديل هذه الرتبة لأنها أعلى أو مساوية لرتبتي.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        edit_kwargs = {}
        
        if new_name:
            edit_kwargs['name'] = new_name
            
        if new_color:
            parsed = self.parse_color(new_color)
            if parsed:
                edit_kwargs['color'] = parsed
            else:
                return await interaction.followup.send("❌ كود اللون غير صحيح.", ephemeral=True)
                
        if new_icon:
            edit_kwargs['display_icon'] = await new_icon.read()

        if not edit_kwargs:
            return await interaction.followup.send("⚠️ لم تقم بإدخال أي تعديلات!", ephemeral=True)

        try:
            await role.edit(**edit_kwargs, reason=f"تم التعديل بواسطة {interaction.user.name}")
            await interaction.followup.send(f"✅ تم تعديل الرتبة {role.mention} بنجاح!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ لا أملك صلاحية كافية لتعديل هذه الرتبة.", ephemeral=True)
        except discord.HTTPException as e:
            if "role_icons" in str(e).lower() or new_icon:
                await interaction.followup.send("❌ لا يمكن تعديل الأيقونة (سيرفرك لا يملك مستوى البوست المطلوب).", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ حدث خطأ: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleManager(bot))