import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from config import *
from utils.helpers import *

class GuildsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="создать_гильдию", description="Создать гильдию")
    @app_commands.describe(
        название="Название гильдии",
        описание="Описание гильдии"
    )
    async def create_guild(self, interaction: discord.Interaction,
                          название: str,
                          описание: str = ""):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['guild_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы уже состоите в гильдии", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['balance'] < GUILD_CREATION_COST:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Недостаточно денег. Нужно: {format_currency(GUILD_CREATION_COST)}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        existing = await self.db.get_guild(guild_name=название)
        if existing:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Гильдия с таким названием уже существует", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        guild_id = await self.db.create_guild(название, описание, interaction.user.id)
        
        if not guild_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать гильдию", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_balance(interaction.user.id, -GUILD_CREATION_COST)
        
        embed = create_embed(
            "🏰 Гильдия создана",
            f"Гильдия **{название}** успешно создана!",
            EMBED_COLORS["guild"]
        )
        embed.add_field(name="Лидер", value=character['character_name'], inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="гильдия", description="Информация о вашей гильдии")
    async def guild_info(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not character['guild_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в гильдии", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        guild = await self.db.get_guild(guild_id=character['guild_id'])
        if not guild:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Гильдия не найдена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        members = await self.db.get_guild_members(guild['id'])
        bank_items = await self.db.get_guild_bank(guild['id'])
        
        embed = create_embed(
            f"🏰 Гильдия: {guild['name']}",
            guild['description'] or "Нет описания",
            EMBED_COLORS["guild"]
        )
        
        leader = await self.db.get_character(guild['leader_id'])
        embed.add_field(name="👑 Лидер", value=leader['character_name'] if leader else "Неизвестно", inline=True)
        embed.add_field(name="👥 Участники", value=str(len(members)), inline=True)
        embed.add_field(name="💰 Банк", value=format_currency(guild['bank_balance']), inline=True)
        
        if bank_items:
            items_text = "\n".join([f"• {i['name']} x{i['quantity']}" for i in bank_items[:5]])
            if len(bank_items) > 5:
                items_text += f"\n... и еще {len(bank_items) - 5}"
            embed.add_field(name="📦 Хранилище", value=items_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="вступить", description="Вступить в гильдию")
    @app_commands.describe(
        название="Название гильдии"
    )
    async def join_guild(self, interaction: discord.Interaction, название: str):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['guild_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы уже состоите в гильдии", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        guild = await self.db.get_guild(guild_name=название)
        if not guild:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Гильдия не найдена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.join_guild(guild['id'], interaction.user.id)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось вступить в гильдию", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Вступление",
            f"Вы вступили в гильдию **{guild['name']}**!",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="покинуть", description="Покинуть гильдию")
    async def leave_guild(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character or not character['guild_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в гильдии", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        guild = await self.db.get_guild(guild_id=character['guild_id'])
        
        if guild['leader_id'] == interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Лидер не может покинуть гильдию", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.leave_guild(interaction.user.id)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось покинуть гильдию", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Выход",
            f"Вы покинули гильдию **{guild['name']}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="внести", description="Внести предмет в банк гильдии")
    @app_commands.describe(
        предмет="Название предмета",
        количество="Количество"
    )
    async def deposit(self, interaction: discord.Interaction,
                     предмет: str,
                     количество: int = 1):
        
        character = await self.db.get_character(interaction.user.id)
        if not character or not character['guild_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в гильдии", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item = await self.db.get_item_by_name(предмет)
        if not item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{предмет}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        has_item = any(i['id'] == item['id'] and i['quantity'] >= количество for i in inventory)
        
        if not has_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"У вас нет {item['name']} в таком количестве", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.deposit_to_guild_bank(character['guild_id'], interaction.user.id, item['id'], количество)
        await self.db.remove_item_from_inventory(interaction.user.id, item['id'], количество)
        
        embed = create_embed(
            "✅ Внесено",
            f"Вы внесли {количество} x **{item['name']}** в банк гильдии",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="снять", description="Снять предмет из банка гильдии")
    @app_commands.describe(
        предмет="Название предмета",
        количество="Количество"
    )
    async def withdraw(self, interaction: discord.Interaction,
                      предмет: str,
                      количество: int = 1):
        
        character = await self.db.get_character(interaction.user.id)
        if not character or not character['guild_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в гильдии", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item = await self.db.get_item_by_name(предмет)
        if not item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{предмет}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.withdraw_from_guild_bank(character['guild_id'], interaction.user.id, item['id'], количество)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "В банке недостаточно предметов", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        tax = int(количество * GUILD_BANK_TAX)
        received = количество - tax
        
        embed = create_embed(
            "✅ Снято",
            f"Вы сняли {received} x **{item['name']}** из банка гильдии (налог {tax} шт.)",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="участники", description="Список участников гильдии")
    async def members(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character or not character['guild_id']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в гильдии", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        members = await self.db.get_guild_members(character['guild_id'])
        guild = await self.db.get_guild(guild_id=character['guild_id'])
        
        embed = create_embed(
            f"👥 Участники гильдии {guild['name']}",
            color=EMBED_COLORS["guild"]
        )
        
        leaders = [m for m in members if m['role'] == 'leader']
        officers = [m for m in members if m['role'] == 'officer']
        regulars = [m for m in members if m['role'] == 'member']
        
        if leaders:
            embed.add_field(
                name="👑 Лидеры",
                value="\n".join([f"• {m['character_name']}" for m in leaders]),
                inline=False
            )
        
        if officers:
            embed.add_field(
                name="⭐ Офицеры",
                value="\n".join([f"• {m['character_name']}" for m in officers]),
                inline=False
            )
        
        if regulars:
            embed.add_field(
                name="👤 Участники",
                value="\n".join([f"• {m['character_name']}" for m in regulars[:10]]),
                inline=False
            )
            if len(regulars) > 10:
                embed.set_footer(text=f"И еще {len(regulars) - 10} участников")
        
        await interaction.response.send_message(embed=embed)
