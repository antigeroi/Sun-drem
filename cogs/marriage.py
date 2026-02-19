import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from database import Database
from config import *
from utils.helpers import *

class MarriageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="предложение", description="Сделать предложение брака")
    @app_commands.describe(
        игрок="Игрок, которому делаете предложение"
    )
    async def propose(self, interaction: discord.Interaction, игрок: discord.Member):
        proposer = await self.db.get_character(interaction.user.id)
        if not proposer:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if игрок.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нельзя жениться на себе", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        target = await self.db.get_character(игрок.id)
        if not target:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У цели нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        existing = await self.db.get_active_marriage(interaction.user.id)
        if existing:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы уже состоите в браке или имеете активное предложение", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        existing = await self.db.get_active_marriage(игрок.id)
        if existing:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Цель уже состоит в браке или имеет активное предложение", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = await self.db.propose_marriage(interaction.user.id, игрок.id)
        
        if not marriage_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать предложение", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "💍 Предложение брака",
            f"{proposer['character_name']} делает предложение {target['character_name']}!",
            EMBED_COLORS["marriage"]
        )
        embed.add_field(name="Срок", value="24 часа на ответ", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        try:
            dm_embed = create_embed(
                "💍 Вам сделали предложение!",
                f"**{proposer['character_name']}** предлагает вам вступить в брак.\n"
                f"Используйте `/принять` чтобы согласиться или `/отказать` чтобы отказаться.",
                EMBED_COLORS["marriage"]
            )
            await игрок.send(embed=dm_embed)
        except:
            pass
    
    @app_commands.command(name="принять", description="Принять предложение брака")
    async def accept(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM marriages 
               WHERE spouse2_id = ? AND status = 'pending' 
               AND proposed_at > datetime('now', '-1 day')''',
            (interaction.user.id,)
        ) as cursor:
            marriage = await cursor.fetchone()
        
        if not marriage:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет активных предложений", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = marriage[0]
        proposer_id = marriage[1]
        
        proposer = await self.db.get_character(proposer_id)
        
        await self.db.accept_marriage(marriage_id)
        
        embed = create_embed(
            "💍 Предложение принято!",
            f"**{character['character_name']}** принял(а) предложение **{proposer['character_name']}**!\n"
            f"Теперь вы можете провести свадебную церемонию.",
            EMBED_COLORS["marriage"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="отказать", description="Отказать в предложении брака")
    async def decline(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM marriages 
               WHERE spouse2_id = ? AND status = 'pending' 
               AND proposed_at > datetime('now', '-1 day')''',
            (interaction.user.id,)
        ) as cursor:
            marriage = await cursor.fetchone()
        
        if not marriage:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет активных предложений", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = marriage[0]
        proposer_id = marriage[1]
        
        proposer = await self.db.get_character(proposer_id)
        
        async with self.db.db.execute('DELETE FROM marriages WHERE id = ?', (marriage_id,)):
            await self.db.db.commit()
        
        embed = create_embed(
            "💔 Отказ",
            f"**{character['character_name']}** отказал(а) **{proposer['character_name']}**.",
            EMBED_COLORS["error"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="свадьба", description="Провести свадебную церемонию")
    async def marry(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM marriages 
               WHERE (spouse1_id = ? OR spouse2_id = ?) 
               AND status = 'accepted' 
               AND accepted_at > datetime('now', '-3 day')''',
            (interaction.user.id, interaction.user.id)
        ) as cursor:
            marriage = await cursor.fetchone()
        
        if not marriage:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет принятых предложений", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = marriage[0]
        spouse1_id = marriage[1]
        spouse2_id = marriage[2]
        
        spouse1 = await self.db.get_character(spouse1_id)
        spouse2 = await self.db.get_character(spouse2_id)
        
        await self.db.marry(marriage_id)
        
        embed = create_embed(
            "💒 Свадьба состоялась!",
            f"**{spouse1['character_name']}** и **{spouse2['character_name']}** теперь муж и жена!",
            EMBED_COLORS["marriage"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="развод", description="Подать на развод")
    async def divorce(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        spouse_id = marriage['spouse1_id'] if marriage['spouse2_id'] == interaction.user.id else marriage['spouse2_id']
        spouse = await self.db.get_character(spouse_id)
        
        view = ConfirmView()
        embed = create_embed(
            "⚠️ Подтверждение развода",
            f"Вы уверены, что хотите развестись с **{spouse['character_name']}**?",
            EMBED_COLORS["warning"]
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            await self.db.divorce(marriage['id'])
            
            embed = create_embed(
                "💔 Развод оформлен",
                f"Брак между **{character['character_name']}** и **{spouse['character_name']}** расторгнут.",
                EMBED_COLORS["error"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            embed = create_embed(
                "✅ Отменено",
                "Развод отменен",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
    @app_commands.command(name="семейный_банк", description="Управление семейным банком")
    async def family_bank(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        balance = await self.db.get_marriage_bank(marriage['id'])
        
        embed = create_embed(
            "💰 Семейный банк",
            f"Баланс: {format_currency(balance)}",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="положить_в_банк", description="Положить деньги в семейный банк")
    @app_commands.describe(
        сумма="Сумма"
    )
    async def deposit_to_family(self, interaction: discord.Interaction, сумма: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if сумма <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Сумма должна быть положительной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['balance'] < сумма:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Недостаточно денег. У вас {format_currency(character['balance'])}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_balance(interaction.user.id, -сумма)
        await self.db.add_to_marriage_bank(marriage['id'], сумма)
        
        embed = create_embed(
            "✅ Деньги положены",
            f"Вы положили {format_currency(сумма)} в семейный банк",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="снять_с_банка", description="Снять деньги из семейного банка")
    @app_commands.describe(
        сумма="Сумма"
    )
    async def withdraw_from_family(self, interaction: discord.Interaction, сумма: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if сумма <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Сумма должна быть положительной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        balance = await self.db.get_marriage_bank(marriage['id'])
        
        if balance < сумма:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"В банке недостаточно денег. Баланс: {format_currency(balance)}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.remove_from_marriage_bank(marriage['id'], сумма)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось снять деньги", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_balance(interaction.user.id, сумма)
        
        embed = create_embed(
            "✅ Деньги сняты",
            f"Вы сняли {format_currency(сумма)} из семейного банка",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
