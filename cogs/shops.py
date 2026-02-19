import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from config import *
from utils.helpers import *

class ShopsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="магазин", description="Открыть магазины в этом канале")
    async def shop(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не можете посещать магазины в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        shops = await self.db.get_shops_for_channel(interaction.channel.id)
        
        if not shops:
            return await interaction.response.send_message(
                embed=create_embed("🏪 Магазины", "В этом канале нет магазинов", EMBED_COLORS["info"])
            )
        
        options = []
        for shop in shops:
            option = discord.SelectOption(
                label=shop['name'],
                description=shop['location'],
                value=str(shop['id'])
            )
            options.append(option)
        
        class ShopSelect(discord.ui.Select):
            def __init__(self, shops_list):
                super().__init__(
                    placeholder="Выберите магазин...",
                    options=options[:25],
                    min_values=1,
                    max_values=1
                )
                self.shops = {s['id']: s for s in shops_list}
            
            async def callback(self, interaction: discord.Interaction):
                shop_id = int(self.values[0])
                shop = self.shops[shop_id]
                
                items = await self.db.get_shop_items(shop_id)
                
                embed = create_embed(
                    f"🏪 {shop['name']}",
                    shop['description'],
                    EMBED_COLORS["info"]
                )
                embed.add_field(name="📍 Локация", value=shop['location'], inline=True)
                embed.add_field(name="👤 Владелец", value=f"<@{shop['owner_id']}>", inline=True)
                
                if not items:
                    embed.add_field(name="📦 Товары", value="Магазин пуст", inline=False)
                else:
                    items_text = ""
                    for item in items:
                        items_text += f"• **{item['name']}** - {format_currency(item['price'])} (в наличии: {item['quantity']})\n"
                    
                    embed.add_field(name="📦 Товары", value=items_text, inline=False)
                
                class BuyView(discord.ui.View):
                    def __init__(self, shop_id, items_list):
                        super().__init__(timeout=60)
                        self.shop_id = shop_id
                        self.items = items_list
                        
                        if items_list:
                            options = []
                            for item in items_list:
                                option = discord.SelectOption(
                                    label=item['name'],
                                    description=f"{format_currency(item['price'])} | Осталось: {item['quantity']}",
                                    value=str(item['item_id'])
                                )
                                options.append(option)
                            
                            select = discord.ui.Select(
                                placeholder="Выберите товар...",
                                options=options[:25],
                                min_values=1,
                                max_values=1
                            )
                            select.callback = self.buy_select
                            self.add_item(select)
                    
                    async def buy_select(self, interaction: discord.Interaction):
                        item_id = int(interaction.data['values'][0])
                        item = next((i for i in self.items if i['item_id'] == item_id), None)
                        
                        if not item:
                            return await interaction.response.send_message(
                                embed=create_embed("❌ Ошибка", "Товар не найден", EMBED_COLORS["error"]),
                                ephemeral=True
                            )
                        
                        class QuantityModal(discord.ui.Modal, title=f"Покупка {item['name']}"):
                            quantity = discord.ui.TextInput(
                                label="Количество",
                                placeholder=f"Максимум: {item['quantity']}",
                                default="1"
                            )
                            
                            async def on_submit(self, interaction: discord.Interaction):
                                try:
                                    qty = int(self.quantity.value)
                                    if qty <= 0 or qty > item['quantity']:
                                        return await interaction.response.send_message(
                                            embed=create_embed("❌ Ошибка", "Некорректное количество", EMBED_COLORS["error"]),
                                            ephemeral=True
                                        )
                                    
                                    success, message, _ = await self.db.buy_from_shop(
                                        self.shop_id, interaction.user.id, item_id, qty
                                    )
                                    
                                    if success:
                                        embed = create_embed("✅ Успешно", message, EMBED_COLORS["success"])
                                    else:
                                        embed = create_embed("❌ Ошибка", message, EMBED_COLORS["error"])
                                    
                                    await interaction.response.send_message(embed=embed, ephemeral=True)
                                    
                                except ValueError:
                                    await interaction.response.send_message(
                                        embed=create_embed("❌ Ошибка", "Введите число", EMBED_COLORS["error"]),
                                        ephemeral=True
                                    )
                        
                        modal = QuantityModal()
                        modal.db = self.db
                        modal.shop_id = self.shop_id
                        await interaction.response.send_modal(modal)
                
                view = BuyView(shop_id, items)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        class ShopView(discord.ui.View):
            def __init__(self, shops_list):
                super().__init__(timeout=60)
                self.add_item(ShopSelect(shops_list))
        
        embed = create_embed(
            "🏪 Магазины",
            "Выберите магазин для просмотра",
            EMBED_COLORS["info"]
        )
        
        view = ShopView(shops)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="мои_магазины", description="Управление вашими магазинами")
    async def my_shops(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        shops = await self.db.get_user_shops(interaction.user.id)
        
        if not shops:
            return await interaction.response.send_message(
                embed=create_embed("🏪 Ваши магазины", "У вас нет магазинов", EMBED_COLORS["info"])
            )
        
        embed = create_embed(
            "🏪 Ваши магазины",
            color=EMBED_COLORS["info"]
        )
        
        for shop in shops:
            channel = self.bot.get_channel(shop['channel_id'])
            channel_name = channel.mention if channel else "Неизвестный канал"
            
            embed.add_field(
                name=shop['name'],
                value=f"📍 {shop['location']}\n📌 {channel_name}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="добавить_товар", description="Добавить товар в свой магазин")
    @app_commands.describe(
        магазин="Название магазина",
        предмет="Название предмета из инвентаря",
        количество="Количество",
        цена="Цена"
    )
    async def add_item(self, interaction: discord.Interaction,
                      магазин: str,
                      предмет: str,
                      количество: int,
                      цена: int):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        shop = await self.db.get_shop(shop_name=магазин)
        if not shop:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Магазин не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if shop['owner_id'] != interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не владелец этого магазина", EMBED_COLORS["error"]),
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
        
        await self.db.add_item_to_shop(shop['id'], item['id'], количество, цена)
        await self.db.remove_item_from_inventory(interaction.user.id, item['id'], количество)
        
        embed = create_embed(
            "✅ Товар добавлен",
            f"В магазин **{магазин}** добавлено {количество} x **{item['name']}** по цене {format_currency(цена)}",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="изменить_цену", description="Изменить цену товара в магазине")
    @app_commands.describe(
        магазин="Название магазина",
        предмет="Название предмета",
        новая_цена="Новая цена"
    )
    async def change_price(self, interaction: discord.Interaction,
                          магазин: str,
                          предмет: str,
                          новая_цена: int):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        shop = await self.db.get_shop(shop_name=магазин)
        if not shop:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Магазин не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if shop['owner_id'] != interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не владелец этого магазина", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item = await self.db.get_item_by_name(предмет)
        if not item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{предмет}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            'UPDATE shop_stock SET current_price = ? WHERE shop_id = ? AND item_id = ?',
            (новая_цена, shop['id'], item['id'])
        ):
            await self.db.db.commit()
        
        embed = create_embed(
            "✅ Цена изменена",
            f"Цена на **{item['name']}** в магазине **{магазин}** изменена на {format_currency(новая_цена)}",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="передать_магазин_игроку", description="Передать магазин другому игроку")
    @app_commands.describe(
        магазин="Название магазина",
        игрок="Новый владелец"
    )
    async def transfer_shop_player(self, interaction: discord.Interaction,
                                  магазин: str,
                                  игрок: discord.Member):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        shop = await self.db.get_shop(shop_name=магазин)
        if not shop:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Магазин не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if shop['owner_id'] != interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не владелец этого магазина", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        target_char = await self.db.get_character(игрок.id)
        if not target_char:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У получателя нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        view = ConfirmView()
        embed = create_embed(
            "⚠️ Подтверждение передачи",
            f"Вы уверены, что хотите передать магазин **{магазин}** игроку {игрок.mention}?",
            EMBED_COLORS["warning"]
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            await self.db.transfer_shop(shop['id'], игрок.id)
            
            embed = create_embed(
                "✅ Магазин передан",
                f"Магазин **{магазин}** передан игроку {игрок.mention}",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            embed = create_embed(
                "✅ Отменено",
                "Передача отменена",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
