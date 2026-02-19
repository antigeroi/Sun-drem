import discord
from discord import app_commands
from discord.ext import commands
import random
from database import Database
from config import *
from utils.helpers import *

class LettersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="написать", description="Написать письмо")
    @app_commands.describe(
        кому="Кому написать",
        текст="Текст письма"
    )
    async def write_letter(self, interaction: discord.Interaction,
                          кому: discord.Member,
                          текст: str):
        
        author = await self.db.get_character(interaction.user.id)
        if not author:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        recipient = await self.db.get_character(кому.id)
        if not recipient:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У получателя нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if len(текст) > 1000:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо слишком длинное (макс 1000 символов)", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        letter_id = await self.db.create_letter(interaction.user.id, кому.id, текст)
        
        if not letter_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать письмо", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.add_item_to_inventory(interaction.user.id, letter_id, 1)
        
        embed = create_embed(
            "✉️ Письмо написано",
            f"Письмо для **{recipient['character_name']}** готово к отправке",
            EMBED_COLORS["info"]
        )
        embed.add_field(name="Команда", value=f"`/отправить {кому.mention} {letter_id}`", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="отправить", description="Отправить письмо")
    @app_commands.describe(
        кому="Кому отправить",
        письмо="ID письма из инвентаря"
    )
    async def send_letter(self, interaction: discord.Interaction,
                         кому: discord.Member,
                         письмо: int):
        
        author = await self.db.get_character(interaction.user.id)
        if not author:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        recipient = await self.db.get_character(кому.id)
        if not recipient:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У получателя нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем, есть ли письмо в инвентаре
        inventory = await self.db.get_inventory(interaction.user.id)
        letter_item = next((i for i in inventory if i['id'] == письмо and i['type'] == 'письмо'), None)
        
        if not letter_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не найдено в инвентаре", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверка на перехват
        road_channel_id = await self.db.get_road_channel()
        road_channel = self.bot.get_channel(road_channel_id) if road_channel_id else None
        
        if road_channel:
            # Смотрим, есть ли в канале дороги другие игроки
            travelers = await self.db.get_travelers_on_road()
            
            for traveler in travelers:
                if traveler['user_id'] != interaction.user.id and traveler['user_id'] != кому.id:
                    # Шанс перехвата 30%
                    if random.random() < 0.3:
                        user = self.bot.get_user(traveler['user_id'])
                        if user:
                            await self.db.intercept_letter(письмо, traveler['user_id'], кому.id)
                            
                            embed = create_embed(
                                "📨 Письмо перехвачено!",
                                f"Вы перехватили письмо от **{author['character_name']}** для **{recipient['character_name']}**",
                                EMBED_COLORS["warning"]
                            )
                            await user.send(embed=embed)
                            
                            return await interaction.response.send_message(
                                embed=create_embed("❌ Письмо перехвачено", "Ваше письмо было перехвачено в пути", EMBED_COLORS["error"]),
                                ephemeral=True
                            )
        
        # Отправляем
        await self.db.send_letter(письмо, interaction.user.id, кому.id)
        
        embed = create_embed(
            "✅ Письмо отправлено",
            f"Письмо для **{recipient['character_name']}** отправлено",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Уведомляем получателя
        try:
            notify_embed = create_embed(
                "📨 Новое письмо!",
                f"Вам пришло письмо от **{author['character_name']}**.\n"
                f"Используйте `/письма` чтобы прочитать.",
                EMBED_COLORS["info"]
            )
            await кому.send(embed=notify_embed)
        except:
            pass
    
    @app_commands.command(name="письма", description="Показать все письма")
    async def list_letters(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        letters = [i for i in inventory if i['type'] == 'письмо']
        
        if not letters:
            return await interaction.response.send_message(
                embed=create_embed("📭 Письма", "У вас нет писем", EMBED_COLORS["info"])
            )
        
        embed = create_embed(
            f"📬 Письма {character['character_name']}",
            color=EMBED_COLORS["info"]
        )
        
        for letter in letters:
            status = ""
            if letter['letter_sealed']:
                status += "🔒 Запечатано "
            if letter['letter_encrypted']:
                status += "🔐 Зашифровано "
            
            embed.add_field(
                name=f"{letter['name']} {status}",
                value=f"ID: {letter['id']}\n{truncate_text(letter['description'], 50)}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="прочитать", description="Прочитать письмо")
    @app_commands.describe(
        письмо="ID письма"
    )
    async def read_letter(self, interaction: discord.Interaction, письмо: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        letter_item = next((i for i in inventory if i['id'] == письмо and i['type'] == 'письмо'), None)
        
        if not letter_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if letter_item['letter_sealed']:
            return await interaction.response.send_message(
                embed=create_embed("🔒 Письмо запечатано", "Сначала вскройте его командой `/вскрыть`", EMBED_COLORS["warning"]),
                ephemeral=True
            )
        
        if letter_item['letter_encrypted']:
            return await interaction.response.send_message(
                embed=create_embed("🔐 Письмо зашифровано", "Сначала расшифруйте его командой `/расшифровать`", EMBED_COLORS["warning"]),
                ephemeral=True
            )
        
        author = await self.db.get_character(letter_item['letter_author'])
        author_name = author['character_name'] if author else "Неизвестно"
        
        embed = create_embed(
            f"📩 Письмо от {author_name}",
            letter_item['letter_content'] or "Пустое письмо",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="уничтожить", description="Уничтожить письмо")
    @app_commands.describe(
        письмо="ID письма"
    )
    async def destroy_letter(self, interaction: discord.Interaction, письмо: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        letter_item = next((i for i in inventory if i['id'] == письмо and i['type'] == 'письмо'), None)
        
        if not letter_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        view = ConfirmView()
        embed = create_embed(
            "⚠️ Подтверждение",
            "Вы уверены, что хотите уничтожить это письмо?",
            EMBED_COLORS["warning"]
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            await self.db.remove_item_from_inventory(interaction.user.id, письмо, 1)
            
            embed = create_embed(
                "✅ Письмо уничтожено",
                "Письмо сожжено",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            embed = create_embed(
                "✅ Отменено",
                "Письмо сохранено",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
    @app_commands.command(name="запечатать", description="Запечатать письмо")
    @app_commands.describe(
        письмо="ID письма"
    )
    async def seal_letter(self, interaction: discord.Interaction, письмо: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        letter_item = next((i for i in inventory if i['id'] == письмо and i['type'] == 'письмо'), None)
        
        if not letter_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.seal_letter(письмо)
        
        embed = create_embed(
            "🔒 Письмо запечатано",
            "Теперь письмо нельзя прочитать без вскрытия",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="вскрыть", description="Вскрыть запечатанное письмо")
    @app_commands.describe(
        письмо="ID письма"
    )
    async def unseal_letter(self, interaction: discord.Interaction, письмо: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        letter_item = next((i for i in inventory if i['id'] == письмо and i['type'] == 'письмо'), None)
        
        if not letter_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not letter_item['letter_sealed']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не запечатано", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.unseal_letter(письмо)
        
        embed = create_embed(
            "✂️ Письмо вскрыто",
            "Теперь письмо можно прочитать",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="зашифровать", description="Зашифровать письмо")
    @app_commands.describe(
        письмо="ID письма",
        ключ="Ключ для шифрования"
    )
    async def encrypt_letter(self, interaction: discord.Interaction,
                            письмо: int,
                            ключ: str):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        letter_item = next((i for i in inventory if i['id'] == письмо and i['type'] == 'письмо'), None)
        
        if not letter_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.encrypt_letter(письмо, ключ)
        
        embed = create_embed(
            "🔐 Письмо зашифровано",
            f"Для расшифровки нужен ключ",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="расшифровать", description="Расшифровать письмо")
    @app_commands.describe(
        письмо="ID письма",
        ключ="Ключ для расшифровки"
    )
    async def decrypt_letter(self, interaction: discord.Interaction,
                            письмо: int,
                            ключ: str):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        letter_item = next((i for i in inventory if i['id'] == письмо and i['type'] == 'письмо'), None)
        
        if not letter_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not letter_item['letter_encrypted']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Письмо не зашифровано", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success, content = await self.db.decrypt_letter(письмо, ключ)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Неверный ключ", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        author = await self.db.get_character(letter_item['letter_author'])
        author_name = author['character_name'] if author else "Неизвестно"
        
        embed = create_embed(
            f"🔓 Расшифрованное письмо от {author_name}",
            content,
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
