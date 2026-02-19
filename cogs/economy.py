import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from config import *
from utils.helpers import *

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="баланс", description="Показать баланс")
    async def balance(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "💰 Баланс",
            f"У вас {format_currency(character['balance'])}",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="передать_деньги", description="Передать деньги другому игроку")
    @app_commands.describe(
        кому="Кому передать",
        сумма="Сумма"
    )
    async def transfer_money(self, interaction: discord.Interaction,
                            кому: discord.Member,
                            сумма: int):
        
        sender = await self.db.get_character(interaction.user.id)
        if not sender:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if кому.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нельзя передать деньги самому себе", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if sender['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не можете передавать деньги в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        receiver = await self.db.get_character(кому.id)
        if not receiver:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У получателя нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if сумма <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Сумма должна быть положительной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if sender['balance'] < сумма:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Недостаточно денег. У вас {format_currency(sender['balance'])}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем налоги
        tax_settings = await self.db.get_tax_settings()
        if tax_settings and tax_settings['tax_rate'] > 0:
            tax = int(сумма * tax_settings['tax_rate'] / 100)
            final_amount = сумма - tax
            
            await self.db.update_balance(interaction.user.id, -сумма)
            await self.db.update_balance(кому.id, final_amount)
            
            if tax > 0 and tax_settings['treasury_id']:
                await self.db.deposit_to_treasury(tax_settings['treasury_id'], 0, tax)
                
                embed = create_embed(
                    "✅ Деньги переданы",
                    f"Вы передали {format_currency(final_amount)} игроку {кому.mention}\nНалог: {format_currency(tax)}",
                    EMBED_COLORS["success"]
                )
        else:
            await self.db.update_balance(interaction.user.id, -сумма)
            await self.db.update_balance(кому.id, сумма)
            
            embed = create_embed(
                "✅ Деньги переданы",
                f"Вы передали {format_currency(сумма)} игроку {кому.mention}",
                EMBED_COLORS["success"]
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="передать_предмет", description="Передать предмет другому игроку")
    @app_commands.describe(
        кому="Кому передать",
        предмет="Название предмета",
        количество="Количество"
    )
    async def transfer_item(self, interaction: discord.Interaction,
                           кому: discord.Member,
                           предмет: str,
                           количество: int = 1):
        
        sender = await self.db.get_character(interaction.user.id)
        if not sender:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if кому.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нельзя передать предмет самому себе", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if sender['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не можете передавать предметы в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        receiver = await self.db.get_character(кому.id)
        if not receiver:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У получателя нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if количество <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Количество должно быть положительным", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item = await self.db.get_item_by_name(предмет)
        if not item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{предмет}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not item['transferable']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Этот предмет нельзя передавать", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        has_item = any(i['id'] == item['id'] and i['quantity'] >= количество for i in inventory)
        
        if not has_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"У вас нет {item['name']} в таком количестве", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.remove_item_from_inventory(interaction.user.id, item['id'], количество)
        await self.db.add_item_to_inventory(кому.id, item['id'], количество)
        
        embed = create_embed(
            "✅ Предмет передан",
            f"Вы передали {количество} x **{item['name']}** игроку {кому.mention}",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="использовать", description="Использовать предмет")
    @app_commands.describe(
        предмет="Название предмета",
        количество="Количество"
    )
    async def use_item(self, interaction: discord.Interaction,
                      предмет: str,
                      количество: int = 1):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не можете использовать предметы в пути (кроме еды)", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if количество <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Количество должно быть положительным", EMBED_COLORS["error"]),
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
        
        # Анонимное использование (для ядов и масок)
        anonymous_use = item['type'] in ['яд']
        
        if item['type'] == 'еда':
            hunger_restore = item['hunger_restore'] * количество
            await self.db.update_hunger(interaction.user.id, hunger_restore)
            await self.db.remove_item_from_inventory(interaction.user.id, item['id'], количество)
            
            if character['hunger'] == 0 and hunger_restore > 0:
                await self.db.reset_death_timer(interaction.user.id)
            
            if not anonymous_use:
                embed = create_embed(
                    "✅ Еда использована",
                    f"Вы съели {количество} x **{item['name']}** и восстановили {hunger_restore} голода",
                    EMBED_COLORS["success"]
                )
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("✅ Предмет использован", ephemeral=True)
            
        elif item['type'] == 'лотерея':
            lottery_id = item['lottery_id']
            if not lottery_id:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", "Этот билет не привязан к лотерее", EMBED_COLORS["error"]),
                    ephemeral=True
                )
            
            success, message, prize = await self.db.use_lottery_ticket(interaction.user.id, lottery_id)
            
            if success:
                await self.db.remove_item_from_inventory(interaction.user.id, item['id'], 1)
                embed = create_embed("🎉 Лотерея", message, EMBED_COLORS["lottery"])
                await interaction.response.send_message(embed=embed, ephemeral=anonymous_use)
            else:
                await self.db.remove_item_from_inventory(interaction.user.id, item['id'], 1)
                embed = create_embed("😔 Лотерея", message, EMBED_COLORS["warning"])
                await interaction.response.send_message(embed=embed, ephemeral=anonymous_use)
        
        elif item['type'] == 'книга_крафта':
            if item['craft_book_id']:
                book = await self.db.get_craft_book(item['craft_book_id'])
                if book:
                    learned = await self.db.learn_crafts_from_book(interaction.user.id, book['name'])
                    embed = create_embed(
                        "📚 Книга прочитана",
                        f"Вы изучили {len(learned)} новых рецептов крафта",
                        EMBED_COLORS["success"]
                    )
                    await self.db.remove_item_from_inventory(interaction.user.id, item['id'], 1)
                    await interaction.response.send_message(embed=embed)
                else:
                    embed = create_embed("❌ Ошибка", "Книга повреждена", EMBED_COLORS["error"])
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = create_embed("❌ Ошибка", "Это не книга крафта", EMBED_COLORS["error"])
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif item['type'] == 'яд':
            # Использование яда обрабатывается в другой команде
            embed = create_embed("❌ Ошибка", "Яды используются через команду /отравить", EMBED_COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        else:
            embed = create_embed("❌ Ошибка", "Этот предмет нельзя использовать", EMBED_COLORS["error"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
