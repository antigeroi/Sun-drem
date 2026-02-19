import discord
from discord import app_commands
from discord.ext import commands
import random
from database import Database
from config import *
from utils.helpers import *

class CraftingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="крафт", description="Показать доступные крафты")
    @app_commands.describe(
        материал="Название материала (опционально)"
    )
    async def craft(self, interaction: discord.Interaction, материал: str = None):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if материал:
            item = await self.db.get_item_by_name(материал)
            if not item:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", f"Предмет '{материал}' не найден", EMBED_COLORS["error"]),
                    ephemeral=True
                )
            
            crafts = await self.db.get_crafts_for_material(interaction.user.id, item['id'])
            
            if not crafts:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Крафт", f"Нет доступных крафтов для {материал}", EMBED_COLORS["info"])
                )
            
            embed = create_embed(
                f"⚒️ Крафт из {материал}",
                color=EMBED_COLORS["info"]
            )
            
            for craft in crafts:
                value = f"Результат: {craft['result_name']} x{craft['result_quantity']}\n"
                value += f"Требуется: {craft['required_quantity']} x {материал}\n"
                if craft['craft_price'] > 0:
                    value += f"Цена: {format_currency(craft['craft_price'])}"
                
                embed.add_field(
                    name=craft['name'],
                    value=value,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        else:
            crafts = await self.db.get_learned_crafts(interaction.user.id)
            
            if not crafts:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Крафт", "У вас нет изученных крафтов", EMBED_COLORS["info"])
                )
            
            by_material = {}
            for craft in crafts:
                material = craft['material_name']
                if material not in by_material:
                    by_material[material] = []
                by_material[material].append(craft)
            
            embed = create_embed(
                "⚒️ Ваши крафты",
                color=EMBED_COLORS["info"]
            )
            
            for material, craft_list in by_material.items():
                value = "\n".join([f"• {c['name']} → {c['result_name']} x{c['result_quantity']}" for c in craft_list[:3]])
                if len(craft_list) > 3:
                    value += f"\n... и еще {len(craft_list) - 3}"
                
                embed.add_field(name=material, value=value, inline=False)
            
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="скрафтить", description="Скрафтить предмет")
    @app_commands.describe(
        название="Название крафта",
        количество="Сколько раз скрафтить"
    )
    async def craft_item(self, interaction: discord.Interaction,
                        название: str,
                        количество: int = 1):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не можете крафтить в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if количество <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Количество должно быть положительным", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if количество > 10:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нельзя крафтить больше 10 за раз", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        crafts = await self.db.get_learned_crafts(interaction.user.id)
        craft = next((c for c in crafts if c['name'].lower() == название.lower()), None)
        
        if not craft:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Крафт '{название}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        successes = 0
        fails = 0
        
        for i in range(количество):
            success, message = await self.db.perform_craft(interaction.user.id, craft['id'])
            if success:
                successes += 1
            else:
                fails += 1
        
        embed = create_embed(
            "⚒️ Результат крафта",
            color=EMBED_COLORS["success"] if successes > 0 else EMBED_COLORS["error"]
        )
        embed.add_field(name="Успешно", value=str(successes), inline=True)
        if fails > 0:
            embed.add_field(name="Неудач", value=str(fails), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="книги_крафта", description="Показать ваши книги крафта")
    async def craft_books(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        books = [i for i in inventory if i['type'] == 'книга_крафта']
        
        if not books:
            return await interaction.response.send_message(
                embed=create_embed("📚 Книги крафта", "У вас нет книг крафта", EMBED_COLORS["info"])
            )
        
        embed = create_embed(
            "📚 Ваши книги крафта",
            color=EMBED_COLORS["info"]
        )
        
        for book in books:
            embed.add_field(
                name=book['name'],
                value=f"{book['description']}\nКоличество: {book['quantity']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="рецепты", description="Показать все рецепты из книги")
    @app_commands.describe(
        книга="Название книги"
    )
    async def book_recipes(self, interaction: discord.Interaction, книга: str):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        book_item = next((i for i in inventory if i['name'].lower() == книга.lower()), None)
        
        if not book_item or book_item['type'] != 'книга_крафта':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Книга '{книга}' не найдена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        book = await self.db.get_craft_book(book_item['craft_book_id'])
        if not book:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Книга повреждена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        crafts = await self.db.get_crafts_by_book(book['name'])
        
        if not crafts:
            return await interaction.response.send_message(
                embed=create_embed("📚 Книга", f"В книге '{книга}' нет рецептов", EMBED_COLORS["info"])
            )
        
        embed = create_embed(
            f"📚 Рецепты из книги '{книга}'",
            color=EMBED_COLORS["info"]
        )
        
        for craft in crafts[:10]:
            value = f"{craft['result_name']} x{craft['result_quantity']}\n"
            value += f"Требуется: {craft['required_quantity']} x {craft['material_name']}"
            if craft['craft_price'] > 0:
                value += f"\nЦена: {format_currency(craft['craft_price'])}"
            
            embed.add_field(name=craft['name'], value=value, inline=False)
        
        if len(crafts) > 10:
            embed.set_footer(text=f"И еще {len(crafts) - 10} рецептов")
        
        await interaction.response.send_message(embed=embed)
