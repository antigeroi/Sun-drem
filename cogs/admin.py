import discord
from discord import app_commands
from discord.ext import commands
import json
from datetime import datetime
from database import Database
from config import *
from utils.helpers import *

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """Проверка прав администратора"""
        if interaction.user.guild_permissions.administrator:
            return True
        
        admin_role = discord.utils.get(interaction.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role and admin_role in interaction.user.roles:
            return True
        
        return False
    
    # ========== УПРАВЛЕНИЕ ПРЕДМЕТАМИ ==========
    
    @app_commands.command(name="создать_предмет", description="Создать новый предмет")
    @app_commands.describe(
        название="Название предмета",
        описание="Описание предмета",
        передаваемый="Можно ли передавать",
        цена="Базовая цена",
        тип="Тип предмета",
        восстанавливает_сытость="Сколько сытости восстанавливает (для еды)",
        эффект_яда="Эффект яда (для ядов)"
    )
    @app_commands.choices(тип=[
        app_commands.Choice(name="оружие", value="оружие"),
        app_commands.Choice(name="материал", value="материал"),
        app_commands.Choice(name="еда", value="еда"),
        app_commands.Choice(name="лотерея", value="лотерея"),
        app_commands.Choice(name="книга_крафта", value="книга_крафта"),
        app_commands.Choice(name="яд", value="яд"),
        app_commands.Choice(name="жилье", value="жилье"),
        app_commands.Choice(name="письмо", value="письмо"),
        app_commands.Choice(name="другое", value="другое")
    ])
    async def create_item(self, interaction: discord.Interaction,
                         название: str,
                         описание: str,
                         передаваемый: bool,
                         цена: int,
                         тип: app_commands.Choice[str],
                         восстанавливает_сытость: int = 0,
                         эффект_яда: str = None):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item_id = await self.db.create_item(
            название, описание, передаваемый, цена,
            тип.value, восстанавливает_сытость, эффект_яда,
            created_by=interaction.user.id
        )
        
        if not item_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать предмет", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Предмет создан",
            f"Предмет **{название}** успешно создан",
            EMBED_COLORS["success"]
        )
        embed.add_field(name="ID", value=str(item_id), inline=True)
        embed.add_field(name="Тип", value=тип.value, inline=True)
        embed.add_field(name="Цена", value=format_currency(цена), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    # ========== УПРАВЛЕНИЕ РОДАМИ ==========
    
    @app_commands.command(name="создать_род", description="Создать новый род")
    @app_commands.describe(
        название="Название рода",
        описание="Описание рода",
        шанс="Шанс выпадения (1-100)"
    )
    async def create_family(self, interaction: discord.Interaction,
                           название: str,
                           описание: str,
                           шанс: int):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if шанс < 1 or шанс > 100:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Шанс должен быть от 1 до 100", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        family_id = await self.db.create_family(название, описание, шанс, interaction.user.id)
        
        if not family_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать род", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Род создан",
            f"Род **{название}** успешно создан",
            EMBED_COLORS["success"]
        )
        embed.add_field(name="ID", value=str(family_id), inline=True)
        embed.add_field(name="Шанс", value=f"{шанс}%", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="роды", description="Список всех родов")
    async def list_families(self, interaction: discord.Interaction):
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        families = await self.db.get_families()
        
        if not families:
            return await interaction.response.send_message(
                embed=create_embed("📜 Роды", "Роды не созданы", EMBED_COLORS["info"])
            )
        
        pages = create_paginated_embeds("📜 Список родов", families, 10)
        
        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
        else:
            view = PaginationView(pages)
            await interaction.response.send_message(embed=pages[0], view=view)
    
    # ========== УПРАВЛЕНИЕ МАГАЗИНАМИ ==========
    
    @app_commands.command(name="создать_магазин", description="Создать новый магазин")
    @app_commands.describe(
        название="Название магазина",
        описание="Описание магазина",
        локация="Где находится",
        канал="Канал, в котором будет виден магазин"
    )
    async def create_shop(self, interaction: discord.Interaction,
                         название: str,
                         описание: str,
                         локация: str,
                         канал: discord.TextChannel):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        shop_id = await self.db.create_shop(
            название, описание, локация, канал.id,
            interaction.user.id, interaction.user.id
        )
        
        if not shop_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать магазин", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Магазин создан",
            f"Магазин **{название}** успешно создан",
            EMBED_COLORS["success"]
        )
        embed.add_field(name="Канал", value=канал.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="передать_магазин", description="Передать магазин другому игроку")
    @app_commands.describe(
        магазин="Название магазина",
        игрок="Новый владелец"
    )
    async def transfer_shop(self, interaction: discord.Interaction,
                           магазин: str,
                           игрок: discord.Member):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        shop = await self.db.get_shop(shop_name=магазин)
        if not shop:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Магазин не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        character = await self.db.get_character(игрок.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У игрока нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.transfer_shop(shop['id'], игрок.id)
        
        embed = create_embed(
            "✅ Магазин передан",
            f"Магазин **{магазин}** передан игроку {игрок.mention}",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    # ========== УПРАВЛЕНИЕ КРАФТОМ ==========
    
    @app_commands.command(name="создать_крафт", description="Создать рецепт крафта")
    @app_commands.describe(
        название="Название крафта",
        описание="Описание",
        результат="Название предмета-результата",
        материал="Название предмета-материала",
        требуется="Сколько материалов нужно",
        получается="Сколько предметов получается",
        цена="Цена крафта",
        книга="Название книги крафта или 'базовый'"
    )
    async def create_craft(self, interaction: discord.Interaction,
                          название: str,
                          описание: str,
                          результат: str,
                          материал: str,
                          требуется: int,
                          получается: int,
                          цена: int,
                          книга: str):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        result_item = await self.db.get_item_by_name(результат)
        if not result_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{результат}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        material_item = await self.db.get_item_by_name(материал)
        if not material_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{материал}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        craft_id = await self.db.create_craft(
            название, описание, result_item['id'], material_item['id'],
            требуется, получается, цена, книга, interaction.user.id
        )
        
        if not craft_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать крафт", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Крафт создан",
            f"Рецепт **{название}** успешно создан",
            EMBED_COLORS["success"]
        )
        embed.add_field(name="Книга", value=книга, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="создать_книгу_крафта", description="Создать книгу крафта")
    @app_commands.describe(
        название="Название книги",
        описание="Описание"
    )
    async def create_craft_book(self, interaction: discord.Interaction,
                               название: str,
                               описание: str):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        book_id = await self.db.create_craft_book(название, описание, interaction.user.id)
        
        if not book_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать книгу", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.create_item(
            f"Книга: {название}",
            описание,
            True,
            0,
            "книга_крафта",
            craft_book_id=book_id,
            created_by=interaction.user.id
        )
        
        embed = create_embed(
            "✅ Книга создана",
            f"Книга крафта **{название}** успешно создана",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    # ========== УПРАВЛЕНИЕ ЛОТЕРЕЯМИ ==========
    
    @app_commands.command(name="создать_лотерею", description="Создать лотерею")
    @app_commands.describe(
        название="Название лотереи",
        описание="Описание",
        цена="Цена билета",
        призы="JSON с призами",
        шанс="Шанс выигрыша (0.1 = 10%)",
        количество="Количество билетов (-1 = безлимит)"
    )
    async def create_lottery(self, interaction: discord.Interaction,
                            название: str,
                            описание: str,
                            цена: int,
                            призы: str,
                            шанс: float,
                            количество: int = -1):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        try:
            prizes = json.loads(призы)
            if not isinstance(prizes, list):
                raise ValueError
        except:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Неверный формат JSON", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        lottery_id = await self.db.create_lottery(
            название, описание, цена, призы, шанс, количество, interaction.user.id
        )
        
        if not lottery_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать лотерею", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Лотерея создана",
            f"Лотерея **{название}** успешно создана",
            EMBED_COLORS["success"]
        )
        embed.add_field(name="Цена билета", value=format_currency(цена), inline=True)
        embed.add_field(name="Шанс", value=f"{шанс*100}%", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    # ========== УПРАВЛЕНИЕ ИГРОКАМИ ==========
    
    @app_commands.command(name="выдать_деньги", description="Выдать деньги игроку")
    @app_commands.describe(
        игрок="Игрок",
        сумма="Сумма"
    )
    async def give_money(self, interaction: discord.Interaction,
                        игрок: discord.Member,
                        сумма: int):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        character = await self.db.get_character(игрок.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У игрока нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_balance(игрок.id, сумма)
        
        embed = create_embed(
            "✅ Деньги выданы",
            f"Игроку {игрок.mention} выдано {format_currency(сумма)}",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="выдать_предмет", description="Выдать предмет игроку")
    @app_commands.describe(
        игрок="Игрок",
        предмет="Название предмета",
        количество="Количество"
    )
    async def give_item(self, interaction: discord.Interaction,
                       игрок: discord.Member,
                       предмет: str,
                       количество: int = 1):
        
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item = await self.db.get_item_by_name(предмет)
        if not item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{предмет}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.add_item_to_inventory(игрок.id, item['id'], количество)
        
        embed = create_embed(
            "✅ Предмет выдан",
            f"Игроку {игрок.mention} выдано {количество} x **{item['name']}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="убить", description="Убить персонажа игрока")
    @app_commands.describe(
        игрок="Игрок"
    )
    async def kill(self, interaction: discord.Interaction, игрок: discord.Member):
        if not await self.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        character = await self.db.get_character(игрок.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У игрока нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        view = ConfirmView()
        embed = create_embed(
            "💀 Подтверждение убийства",
            f"Вы уверены, что хотите убить персонажа **{character['character_name']}**?",
            EMBED_COLORS["warning"]
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            await self.db.kill_character(игрок.id)
            
            embed = create_embed(
                "💀 Персонаж убит",
                f"Персонаж **{character['character_name']}** убит",
                EMBED_COLORS["death"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            embed = create_embed(
                "✅ Отменено",
                "Убийство отменено",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
