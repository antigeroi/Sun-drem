import discord
from discord import app_commands
from discord.ext import commands
import random
from database import Database
from config import *
from utils.helpers import *

class NPCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="создать_npc", description="Создать нового NPC (админ)")
    @app_commands.describe(
        имя="Имя NPC",
        тип="Тип NPC",
        локация="Локация",
        характер="Характер"
    )
    @app_commands.choices(тип=[
        app_commands.Choice(name="горожанин", value="горожанин"),
        app_commands.Choice(name="путник", value="путник"),
        app_commands.Choice(name="житель", value="житель")
    ])
    @app_commands.choices(характер=[
        app_commands.Choice(name="дружелюбный", value="дружелюбный"),
        app_commands.Choice(name="угрюмый", value="угрюмый"),
        app_commands.Choice(name="болтливый", value="болтливый"),
        app_commands.Choice(name="подозрительный", value="подозрительный"),
        app_commands.Choice(name="торгаш", value="торгаш"),
        app_commands.Choice(name="трусливый", value="трусливый"),
        app_commands.Choice(name="агрессивный", value="агрессивный")
    ])
    async def create_npc(self, interaction: discord.Interaction,
                        имя: str,
                        тип: app_commands.Choice[str],
                        локация: discord.TextChannel,
                        характер: app_commands.Choice[str]):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        loc = await self.db.get_location(локация.id)
        if not loc:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Эта локация не зарегистрирована", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_id = await self.db.create_npc(
            имя, тип.value, локация.id, характер.value, interaction.user.id
        )
        
        if not npc_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать NPC", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ NPC создан",
            f"Создан NPC **{имя}** в локации {локация.mention}",
            EMBED_COLORS["success"]
        )
        embed.add_field(name="Тип", value=тип.name, inline=True)
        embed.add_field(name="Характер", value=характер.name, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="фраза_npc", description="Добавить фразу для NPC (админ)")
    @app_commands.describe(
        npc="Имя NPC",
        фраза="Текст фразы"
    )
    async def add_npc_phrase(self, interaction: discord.Interaction,
                            npc: str,
                            фраза: str):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_data = await self.db.get_npc_by_name(npc)
        if not npc_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"NPC '{npc}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.add_npc_phrase(npc_data['id'], фраза)
        
        embed = create_embed(
            "✅ Фраза добавлена",
            f"Для NPC **{npc}** добавлена фраза: *{фраза}*",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="канал_донесений", description="Установить канал для донесений NPC (админ)")
    @app_commands.describe(
        канал="Канал"
    )
    async def set_report_channel(self, interaction: discord.Interaction, канал: discord.TextChannel):
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.set_npc_report_channel(канал.id)
        
        embed = create_embed(
            "✅ Канал донесений установлен",
            f"Канал {канал.mention} будет получать донесения от NPC",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="люди", description="Показать NPC рядом с вами")
    async def people(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы в пути, никого не видно", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        npcs = await self.db.get_npcs_in_location(current_loc)
        
        # Убираем мертвых NPC
        npcs = [n for n in npcs if not n['is_dead']]
        
        if not npcs:
            return await interaction.response.send_message(
                embed=create_embed("👥 Люди", "Рядом никого нет", EMBED_COLORS["info"])
            )
        
        # Показываем случайное количество (от 1 до всех)
        show_count = random.randint(1, len(npcs))
        shown_npcs = random.sample(npcs, show_count)
        
        embed = create_embed(
            "👥 Люди рядом с вами",
            color=EMBED_COLORS["npc"]
        )
        
        for npc in shown_npcs:
            embed.add_field(
                name=npc['name'],
                value=f"*{npc['personality']}*\n"
                      f"Тип: {npc['type']}",
                inline=False
            )
        
        if show_count < len(npcs):
            embed.set_footer(text=f"И еще {len(npcs) - show_count} человек неподалеку")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="поговорить", description="Поговорить с NPC")
    @app_commands.describe(
        npc="Имя NPC"
    )
    async def talk_to(self, interaction: discord.Interaction, npc: str):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы в пути, нельзя разговаривать", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_data = await self.db.get_npc_by_name(npc)
        if not npc_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"NPC '{npc}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if npc_data['is_dead']:
            return await interaction.response.send_message(
                embed=create_embed("💀 NPC мертв", f"{npc} сейчас мертв", EMBED_COLORS["death"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        if npc_data['location_id'] != current_loc:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"{npc} сейчас не здесь", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        phrase = await self.db.get_random_npc_phrase(npc_data['id'])
        
        # Учитываем репутацию
        reputation = await self.db.get_npc_reputation(npc_data['id'], interaction.user.id)
        
        if reputation < -20:
            phrase = f"{phrase} (отворачивается от вас)"
        elif reputation > 20:
            phrase = f"{phrase} (дружелюбно улыбается вам)"
        
        embed = create_embed(
            f"💬 {npc}",
            f"*{phrase}*",
            EMBED_COLORS["npc"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="угостить", description="Угостить NPC едой")
    @app_commands.describe(
        npc="Имя NPC",
        еда="Название еды"
    )
    async def treat(self, interaction: discord.Interaction,
                   npc: str,
                   еда: str):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_data = await self.db.get_npc_by_name(npc)
        if not npc_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"NPC '{npc}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        if npc_data['location_id'] != current_loc:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"{npc} сейчас не здесь", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item = await self.db.get_item_by_name(еда)
        if not item or item['type'] != 'еда':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Это не еда", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        has_item = any(i['id'] == item['id'] and i['quantity'] >= 1 for i in inventory)
        
        if not has_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"У вас нет {item['name']}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.remove_item_from_inventory(interaction.user.id, item['id'], 1)
        await self.db.update_npc_reputation(npc_data['id'], interaction.user.id, 5)
        
        embed = create_embed(
            "🍎 Угощение",
            f"Вы угостили {npc} {item['name']}. Ему понравилось!",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="подарить", description="Подарить предмет NPC")
    @app_commands.describe(
        npc="Имя NPC",
        предмет="Название предмета"
    )
    async def gift(self, interaction: discord.Interaction,
                  npc: str,
                  предмет: str):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_data = await self.db.get_npc_by_name(npc)
        if not npc_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"NPC '{npc}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        if npc_data['location_id'] != current_loc:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"{npc} сейчас не здесь", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        item = await self.db.get_item_by_name(предмет)
        if not item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Предмет '{предмет}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        inventory = await self.db.get_inventory(interaction.user.id)
        has_item = any(i['id'] == item['id'] and i['quantity'] >= 1 for i in inventory)
        
        if not has_item:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"У вас нет {item['name']}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.remove_item_from_inventory(interaction.user.id, item['id'], 1)
        await self.db.update_npc_reputation(npc_data['id'], interaction.user.id, 10)
        
        embed = create_embed(
            "🎁 Подарок",
            f"Вы подарили {npc} {item['name']}. Он очень рад!",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="пригрозить", description="Пригрозить NPC")
    @app_commands.describe(
        npc="Имя NPC"
    )
    async def threaten(self, interaction: discord.Interaction, npc: str):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_data = await self.db.get_npc_by_name(npc)
        if not npc_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"NPC '{npc}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        if npc_data['location_id'] != current_loc:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"{npc} сейчас не здесь", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_npc_reputation(npc_data['id'], interaction.user.id, -10)
        
        if npc_data['personality'] == 'трусливый':
            phrase = "в страхе убегает!"
            # NPC убегает в другой канал
            destinations = await self.db.get_available_destinations(current_loc)
            if destinations:
                dest = random.choice(destinations)
                async with self.db.db.execute(
                    'UPDATE npcs SET location_id = ? WHERE id = ?',
                    (dest['channel_id'], npc_data['id'])
                ):
                    await self.db.db.commit()
        elif npc_data['personality'] == 'агрессивный':
            phrase = "злобно смотрит на вас и вызывает стражу!"
        else:
            phrase = "пугается и отходит подальше"
        
        embed = create_embed(
            "😠 Угроза",
            f"{npc} {phrase}",
            EMBED_COLORS["warning"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="убить_npc", description="Убить NPC")
    @app_commands.describe(
        npc="Имя NPC"
    )
    async def kill_npc(self, interaction: discord.Interaction, npc: str):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_data = await self.db.get_npc_by_name(npc)
        if not npc_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"NPC '{npc}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        if npc_data['location_id'] != current_loc:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"{npc} сейчас не здесь", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем свидетелей
        nearby_npcs = await self.db.get_npcs_in_location(current_loc)
        witnesses = [n for n in nearby_npcs if n['id'] != npc_data['id']]
        
        report_channel_id = await self.db.get_npc_report_channel()
        report_channel = self.bot.get_channel(report_channel_id) if report_channel_id else None
        
        for witness in witnesses:
            if random.random() < NPC_WITNESS_CHANCE:
                if report_channel:
                    await report_channel.send(
                        f"**[ДОНЕСЕНИЕ]** {witness['name']}: Я видел(а), как {character['character_name']} убил(а) {npc} в {interaction.channel.mention}!"
                    )
        
        await self.db.kill_npc(npc_data['id'], interaction.user.id)
        
        embed = create_embed(
            "🗡️ NPC убит",
            f"Вы убили {npc}. Он возродится через некоторое время.",
            EMBED_COLORS["death"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="отношения", description="Узнать отношение NPC к вам")
    @app_commands.describe(
        npc="Имя NPC"
    )
    async def relationship(self, interaction: discord.Interaction, npc: str):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        npc_data = await self.db.get_npc_by_name(npc)
        if not npc_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"NPC '{npc}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        rep = await self.db.get_npc_reputation(npc_data['id'], interaction.user.id)
        
        if rep <= -50:
            status = "🔴 Враг"
        elif rep <= -20:
            status = "🟠 Недоверие"
        elif rep < 20:
            status = "⚪ Нейтрально"
        elif rep < 50:
            status = "🟢 Дружелюбно"
        else:
            status = "💚 Друг"
        
        embed = create_embed(
            f"📊 Отношение {npc} к вам",
            f"{status} ({rep})",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed)
