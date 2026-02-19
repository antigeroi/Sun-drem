import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import random
import asyncio
from database import Database
from config import *
from utils.helpers import *

class TravelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="добавить_локацию", description="Добавить новую локацию (админ)")
    @app_commands.describe(
        канал="Канал-локация",
        название="Название локации",
        описание="Описание локации"
    )
    async def add_location(self, interaction: discord.Interaction,
                          канал: discord.TextChannel,
                          название: str,
                          описание: str = ""):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.add_location(канал.id, название, описание)
        
        embed = create_embed(
            "✅ Локация добавлена",
            f"Локация **{название}** ({канал.mention}) добавлена",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="путь", description="Задать время пути между локациями (админ)")
    @app_commands.describe(
        локация1="Первая локация",
        локация2="Вторая локация",
        время_в_минутах="Время в минутах"
    )
    async def set_path(self, interaction: discord.Interaction,
                      локация1: discord.TextChannel,
                      локация2: discord.TextChannel,
                      время_в_минутах: int):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        loc1 = await self.db.get_location(локация1.id)
        loc2 = await self.db.get_location(локация2.id)
        
        if not loc1:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Локация {локация1.mention} не зарегистрирована", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not loc2:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Локация {локация2.mention} не зарегистрирована", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.add_travel_path(локация1.id, локация2.id, время_в_минутах)
        
        embed = create_embed(
            "✅ Путь задан",
            f"Путь от **{loc1['name']}** до **{loc2['name']}** займет {время_в_минутах} минут",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="канал_дороги", description="Установить канал для дороги (админ)")
    @app_commands.describe(
        канал="Канал"
    )
    async def set_road_channel(self, interaction: discord.Interaction, канал: discord.TextChannel):
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.set_road_channel(канал.id)
        
        embed = create_embed(
            "✅ Канал дороги установлен",
            f"Канал {канал.mention} будет использоваться для путешествий",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="добавить_событие", description="Добавить атмосферное событие в путь (админ)")
    @app_commands.describe(
        текст="Текст события"
    )
    async def add_travel_event(self, interaction: discord.Interaction, текст: str):
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.add_travel_event(текст)
        
        embed = create_embed(
            "✅ Событие добавлено",
            f"Добавлено: *{текст}*",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="интервал_событий", description="Установить интервал событий в пути (админ)")
    @app_commands.describe(
        секунды="Интервал в секундах"
    )
    async def set_event_interval(self, interaction: discord.Interaction, секунды: int):
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.set_event_interval(секунды)
        
        embed = create_embed(
            "✅ Интервал установлен",
            f"Атмосферные события будут появляться каждые {секунды} секунд",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="куда_можно", description="Показать доступные направления")
    async def where_can_go(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы уже в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        destinations = await self.db.get_available_destinations(current_loc)
        
        if not destinations:
            return await interaction.response.send_message(
                embed=create_embed("🗺️ Карта", "Из этой локации никуда нельзя уйти", EMBED_COLORS["info"])
            )
        
        embed = create_embed(
            "🗺️ Доступные направления",
            color=EMBED_COLORS["travel"]
        )
        
        for dest in destinations:
            channel = self.bot.get_channel(dest['channel_id'])
            if channel and channel.permissions_for(interaction.user).view_channel:
                embed.add_field(
                    name=dest['name'],
                    value=f"⏱️ {dest['time']} минут\n📌 {channel.mention}",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="идти", description="Отправиться в другую локацию")
    @app_commands.describe(
        локация="Локация назначения"
    )
    async def go_to(self, interaction: discord.Interaction, локация: discord.TextChannel):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы уже в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем, есть ли у пользователя доступ к каналу
        if not локация.permissions_for(interaction.user).view_channel:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет доступа к этой локации", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        current_loc = character['current_location'] or interaction.channel.id
        travel_time = await self.db.get_travel_time(current_loc, локация.id)
        
        if not travel_time:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нет прямого пути в эту локацию", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        dest_loc = await self.db.get_location(локация.id)
        if not dest_loc:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Эта локация не зарегистрирована", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.start_travel(interaction.user.id, локация.id, travel_time)
        
        road_channel_id = await self.db.get_road_channel()
        road_channel = self.bot.get_channel(road_channel_id) if road_channel_id else None
        
        embed = create_embed(
            "🚶 В путь!",
            f"Вы отправляетесь в **{dest_loc['name']}**. В пути: {travel_time} минут",
            EMBED_COLORS["travel"]
        )
        if road_channel:
            embed.add_field(name="Канал дороги", value=road_channel.mention, inline=False)
            embed.add_field(name="Общение", value="Пока вы в пути, вы можете общаться только там", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="где_я", description="Узнать текущее местоположение")
    async def where_am_i(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['travel_start']:
            start = datetime.fromisoformat(character['travel_start'])
            end = datetime.fromisoformat(character['travel_end'])
            now = datetime.now()
            
            total = (end - start).total_seconds() / 60
            passed = (now - start).total_seconds() / 60
            remaining = (end - now).total_seconds() / 60
            
            dest_loc = await self.db.get_location(character['travel_destination'])
            dest_name = dest_loc['name'] if dest_loc else "неизвестно"
            
            embed = create_embed(
                "🚶 Вы в пути",
                f"Направляетесь в **{dest_name}**",
                EMBED_COLORS["travel"]
            )
            embed.add_field(name="Прошло", value=f"{passed:.1f} мин", inline=True)
            embed.add_field(name="Осталось", value=f"{remaining:.1f} мин", inline=True)
            embed.add_field(name="Всего", value=f"{total:.1f} мин", inline=True)
            
        else:
            current_loc = character['current_location'] or interaction.channel.id
            loc = await self.db.get_location(current_loc)
            
            if loc:
                embed = create_embed(
                    "📍 Вы находитесь",
                    f"**{loc['name']}**\n{loc['description'] or ''}",
                    EMBED_COLORS["info"]
                )
                if loc['weather']:
                    embed.add_field(name="Погода", value=loc['weather'], inline=True)
                if loc['smells']:
                    embed.add_field(name="Запахи", value=loc['smells'], inline=True)
                if loc['sounds']:
                    embed.add_field(name="Звуки", value=loc['sounds'], inline=True)
            else:
                embed = create_embed(
                    "📍 Вы находитесь",
                    "Неизвестная локация",
                    EMBED_COLORS["info"]
                )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="привал", description="Сделать привал в пути (3 минуты)")
    async def rest(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Увеличиваем время пути на 3 минуты
        end = datetime.fromisoformat(character['travel_end'])
        new_end = end + timedelta(minutes=TRAVEL_REST_MINUTES)
        
        async with self.db.db.execute(
            'UPDATE characters SET travel_end = ? WHERE user_id = ?',
            (new_end.isoformat(), interaction.user.id)
        ):
            await self.db.db.commit()
        
        await self.db.update_hunger(interaction.user.id, 5)
        
        embed = create_embed(
            "🏕️ Привал",
            f"Вы остановились отдохнуть на {TRAVEL_REST_MINUTES} минут.\n"
            f"Восстановлено 5 голода.\n"
            f"Время в пути увеличено.",
            EMBED_COLORS["travel"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="вернуться", description="Повернуть назад")
    async def go_back(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if not character['travel_start']:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не в пути", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        start = datetime.fromisoformat(character['travel_start'])
        now = datetime.now()
        passed = (now - start).total_seconds() / 60
        
        # Возвращаемся, тратим половину пройденного времени
        return_time = passed / 2
        
        await self.db.start_travel(interaction.user.id, character['current_location'], return_time)
        
        embed = create_embed(
            "↩️ Возвращение",
            f"Вы повернули назад. Вернетесь через {return_time:.1f} минут",
            EMBED_COLORS["travel"]
        )
        
        await interaction.response.send_message(embed=embed)
