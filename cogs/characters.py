import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
from database import Database
from config import *
from utils.helpers import *

class CharactersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="создать_персонажа", description="Создать нового персонажа")
    @app_commands.describe(
        имя="Имя персонажа",
        префикс="Префикс для ролевых сообщений (мин 2 символа)",
        пол="Пол персонажа",
        биография="Биография (минимум 500 символов)"
    )
    @app_commands.choices(пол=[
        app_commands.Choice(name="Мужской", value="male"),
        app_commands.Choice(name="Женский", value="female"),
        app_commands.Choice(name="Небинарный", value="nonbinary")
    ])
    async def create_character(self, interaction: discord.Interaction,
                              имя: str,
                              префикс: str,
                              пол: app_commands.Choice[str],
                              биография: str):
        
        if len(префикс) < 2:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Префикс должен быть минимум 2 символа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if len(биография) < 500:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Биография должна быть минимум 500 символов (сейчас {len(биография)})", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if len(биография) > 10000:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Биография должна быть максимум 10000 символов (сейчас {len(биография)})", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        existing = await self.db.get_character(interaction.user.id)
        if existing:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас уже есть персонаж", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.create_character(
            interaction.user.id, имя, префикс, пол.value, биография
        )
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        family_id = (await self.db.get_character(interaction.user.id))['family_id']
        family = await self.db.get_family(family_id) if family_id else None
        
        embed = create_embed(
            "✅ Персонаж создан",
            f"Добро пожаловать в мир Sunny Dream, **{имя}**!",
            EMBED_COLORS["success"]
        )
        embed.add_field(name="Имя", value=имя, inline=True)
        embed.add_field(name="Префикс", value=f"`{префикс}`", inline=True)
        embed.add_field(name="Пол", value=пол.name, inline=True)
        if family:
            embed.add_field(name="Род", value=family['name'], inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="анкета", description="Показать анкету персонажа")
    @app_commands.describe(
        игрок="Игрок (если не указан, покажет вашу)"
    )
    async def profile(self, interaction: discord.Interaction, игрок: discord.Member = None):
        target = игрок or interaction.user
        character = await self.db.get_character(target.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У этого игрока нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        family = await self.db.get_family(character['family_id']) if character['family_id'] else None
        titles = await self.db.get_character_titles(target.id)
        
        embed = create_embed(
            f"📋 Анкета: {character['character_name']}",
            character['biography'],
            EMBED_COLORS["info"]
        )
        embed.add_field(name="Пол", value=character['gender'], inline=True)
        embed.add_field(name="Род", value=family['name'] if family else "Нет", inline=True)
        embed.add_field(name="Создан", value=datetime.fromisoformat(character['created_at']).strftime("%d.%m.%Y"), inline=True)
        
        if titles:
            embed.add_field(
                name="Титулы",
                value=", ".join([t['name'] for t in titles]),
                inline=False
            )
        
        if character['active_title']:
            embed.add_field(name="Активный титул", value=character['active_title'], inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="паспорт", description="Показать свой паспорт")
    async def passport(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        passport_info = await self.db.get_passport_info(interaction.user.id)
        
        embed = create_embed(
            f"🪪 Паспорт: {passport_info['name']}",
            color=EMBED_COLORS["info"]
        )
        embed.add_field(name="Титулы", value=", ".join(passport_info['titles']) or "Нет", inline=False)
        embed.add_field(name="Баланс", value=format_currency(passport_info['balance']), inline=True)
        if passport_info['family']:
            embed.add_field(name="Род", value=passport_info['family'], inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="показать_паспорт", description="Показать паспорт другому игроку")
    @app_commands.describe(
        кому="Кому показать паспорт"
    )
    async def show_passport(self, interaction: discord.Interaction, кому: discord.Member):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        passport_info = await self.db.get_passport_info(interaction.user.id)
        
        embed = create_embed(
            f"🪪 Паспорт: {passport_info['name']}",
            f"Показан игроку {кому.mention}",
            EMBED_COLORS["info"]
        )
        embed.add_field(name="Титулы", value=", ".join(passport_info['titles']) or "Нет", inline=False)
        embed.add_field(name="Баланс", value=format_currency(passport_info['balance']), inline=True)
        
        await interaction.response.send_message(embed=embed)
        
        try:
            dm_embed = create_embed(
                f"🪪 Паспорт: {passport_info['name']}",
                f"Вам показал паспорт **{passport_info['name']}**",
                EMBED_COLORS["info"]
            )
            dm_embed.add_field(name="Титулы", value=", ".join(passport_info['titles']) or "Нет", inline=False)
            dm_embed.add_field(name="Баланс", value=format_currency(passport_info['balance']), inline=True)
            
            await кому.send(embed=dm_embed)
        except:
            pass
    
    @app_commands.command(name="статус", description="Показать статус персонажа")
    async def status(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        hunger_bar = create_hunger_bar(character['hunger'])
        
        embed = create_embed(
            f"📊 Статус: {character['character_name']}",
            color=EMBED_COLORS["info"]
        )
        embed.add_field(name="🍖 Голод", value=hunger_bar, inline=False)
        embed.add_field(name="💰 Баланс", value=format_currency(character['balance']), inline=True)
        embed.add_field(name="🔤 Префикс", value=f"`{character['prefix']}`", inline=True)
        
        if character['travel_start']:
            embed.add_field(name="🚶 В пути", value="Да", inline=True)
        
        if character['death_timer_start'] and character['hunger'] == 0:
            time_left = time_until_death(character['death_timer_start'])
            embed.add_field(name="⏰ До смерти", value=time_left, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="инвентарь", description="Показать инвентарь")
    async def inventory(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        items = await self.db.get_inventory(interaction.user.id)
        
        if not items:
            return await interaction.response.send_message(
                embed=create_embed("🎒 Инвентарь", "Ваш инвентарь пуст", EMBED_COLORS["info"])
            )
        
        pages = create_paginated_embeds(
            f"🎒 Инвентарь {character['character_name']}",
            items,
            8,
            EMBED_COLORS["info"]
        )
        
        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginationView(pages)
            await interaction.response.send_message(embed=pages[0], view=view)
    
    @app_commands.command(name="мысль", description="Показать мысль персонажа")
    @app_commands.describe(
        текст="Текст мысли"
    )
    async def thought(self, interaction: discord.Interaction, текст: str):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await interaction.response.send_message(
            f"*{character['character_name']} думает: \"{текст}\"*"
        )
    
    @app_commands.command(name="эмоция", description="Показать действие персонажа")
    @app_commands.describe(
        текст="Описание действия"
    )
    async def emotion(self, interaction: discord.Interaction, текст: str):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await interaction.response.send_message(
            f"*{character['character_name']} {текст}*"
        )
    
    @app_commands.command(name="шепот", description="Шепнуть другому игроку")
    @app_commands.describe(
        кому="Кому шепнуть",
        текст="Текст шепота"
    )
    async def whisper(self, interaction: discord.Interaction, кому: discord.Member, текст: str):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        target_char = await self.db.get_character(кому.id)
        if not target_char:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У этого игрока нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        try:
            await interaction.delete_original_response()
        except:
            pass
        
        await interaction.channel.send(
            f"👤 {character['character_name']} → {target_char['character_name']} (шепот)"
        )
        
        try:
            embed = create_embed(
                f"🤫 Шепот от {character['character_name']}",
                текст,
                EMBED_COLORS["info"]
            )
            await кому.send(embed=embed)
        except:
            pass
    
    @app_commands.command(name="умереть", description="Добровольная смерть персонажа")
    async def die(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не можете умереть во время путешествия", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        view = ConfirmView()
        embed = create_embed(
            "💀 Подтверждение смерти",
            f"Вы уверены? Персонаж **{character['character_name']}** умрет навсегда.",
            EMBED_COLORS["warning"]
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            await self.db.kill_character(interaction.user.id)
            
            embed = create_embed(
                "💀 Персонаж умер",
                f"**{character['character_name']}** больше нет...",
                EMBED_COLORS["death"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            embed = create_embed(
                "✅ Отменено",
                "Смерть отменена",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
