import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from database import Database
from config import *
from utils.helpers import *

class BountyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="назначить_награду", description="Назначить награду за голову")
    @app_commands.describe(
        цель="Игрок, на которого назначается награда",
        сумма="Сумма награды",
        причина="Причина"
    )
    async def set_bounty(self, interaction: discord.Interaction,
                        цель: discord.Member,
                        сумма: int,
                        причина: str):
        
        creator = await self.db.get_character(interaction.user.id)
        if not creator:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        target = await self.db.get_character(цель.id)
        if not target:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У цели нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if цель.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нельзя назначить награду на себя", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if сумма <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Сумма должна быть положительной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if creator['balance'] < сумма:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Недостаточно денег. У вас {format_currency(creator['balance'])}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not await self.db.is_bounty_channel(interaction.channel.id):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "В этом канале нельзя создавать заказы на охоту", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        bounty_id = await self.db.create_bounty(
            target['user_id'], сумма, причина,
            creator['user_id'], interaction.channel.id
        )
        
        if not bounty_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать заказ", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_balance(creator['user_id'], -сумма)
        
        embed = create_embed(
            "🎯 Заказ создан",
            f"Назначена награда за голову **{target['character_name']}**",
            EMBED_COLORS["bounty"]
        )
        embed.add_field(name="Награда", value=format_currency(сумма), inline=True)
        embed.add_field(name="Причина", value=причина, inline=False)
        embed.add_field(name="Срок", value=f"{BOUNTY_COMPLETION_DAYS} дней", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="заказы", description="Показать активные заказы в этом канале")
    async def bounties(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        bounties = await self.db.get_active_bounties(interaction.channel.id)
        
        if not bounties:
            return await interaction.response.send_message(
                embed=create_embed("🎯 Заказы", "В этом канале нет активных заказов", EMBED_COLORS["info"])
            )
        
        embed = create_embed(
            "🎯 Активные заказы",
            color=EMBED_COLORS["bounty"]
        )
        
        for bounty in bounties:
            status = "🆓 Свободен" if not bounty['hunter_id'] else f"⚔️ Взял: {bounty['hunter_name']}"
            expires = datetime.fromisoformat(bounty['expires_at']).strftime("%d.%m.%Y %H:%M")
            
            embed.add_field(
                name=f"Цель: {bounty['target_name']}",
                value=f"💰 {format_currency(bounty['reward'])}\n📝 {bounty['reason']}\n{status}\n⏰ до {expires}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="взяться_за_заказ", description="Взяться за выполнение заказа")
    @app_commands.describe(
        номер="Номер цели из списка"
    )
    async def take_bounty(self, interaction: discord.Interaction, номер: int):
        hunter = await self.db.get_character(interaction.user.id)
        if not hunter:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        bounties = await self.db.get_active_bounties(interaction.channel.id)
        
        if номер < 1 or номер > len(bounties):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Неверный номер", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        bounty = bounties[номер - 1]
        
        if bounty['hunter_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Заказ уже взят", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.take_bounty(bounty['id'], hunter['user_id'])
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось взяться за заказ", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Заказ принят",
            f"Вы взялись за заказ на **{bounty['target_name']}**. У вас есть {BOUNTY_COMPLETION_DAYS} дней.",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="мой_заказ", description="Показать информацию о вашем заказе")
    async def my_bounty(self, interaction: discord.Interaction):
        hunter = await self.db.get_character(interaction.user.id)
        if not hunter:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT b.*, tc.character_name as target_name
               FROM bounties b
               JOIN characters tc ON b.target_id = tc.user_id
               WHERE b.hunter_id = ? AND b.completed = FALSE 
                     AND b.expires_at > datetime('now')''',
            (hunter['user_id'],)
        ) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет активных заказов", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        bounty = {
            'id': row[0],
            'target_name': row[11],
            'reward': row[2],
            'reason': row[3],
            'expires_at': row[7]
        }
        
        expires = datetime.fromisoformat(bounty['expires_at']).strftime("%d.%m.%Y %H:%M")
        time_left = datetime.fromisoformat(bounty['expires_at']) - datetime.now()
        
        embed = create_embed(
            "🎯 Ваш заказ",
            f"Цель: **{bounty['target_name']}**",
            EMBED_COLORS["bounty"]
        )
        embed.add_field(name="Награда", value=format_currency(bounty['reward']), inline=True)
        embed.add_field(name="Причина", value=bounty['reason'], inline=False)
        embed.add_field(name="Срок до", value=expires, inline=True)
        embed.add_field(name="Осталось", value=format_time_delta(time_left), inline=True)
        
        await interaction.response.send_message(embed=embed)
