import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from config import *
from utils.helpers import *

class TitlesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="создать_титул", description="Создать новый титул (админ)")
    @app_commands.describe(
        название="Название титула",
        зарплата="Зарплата (0 если нет)",
        интервал="Интервал выплат (1ч, 3ч, 6ч, 12ч, 24ч)",
        хранилище="Название хранилища для выплат (если нужно)",
        тип_условия="Тип условия",
        значение_условия="Значение условия"
    )
    @app_commands.choices(тип_условия=[
        app_commands.Choice(name="без условия", value="none"),
        app_commands.Choice(name="баланс", value="balance"),
        app_commands.Choice(name="гильдия", value="guild"),
        app_commands.Choice(name="предмет", value="item"),
        app_commands.Choice(name="жилье", value="housing")
    ])
    async def create_title(self, interaction: discord.Interaction,
                          название: str,
                          зарплата: int = 0,
                          интервал: str = "0",
                          хранилище: str = None,
                          тип_условия: app_commands.Choice[str] = None,
                          значение_условия: str = None):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Парсим интервал
        interval_seconds = 0
        if интервал != "0":
            if интервал.endswith('ч'):
                interval_seconds = int(интервал[:-1]) * 3600
            elif интервал.endswith('ч'):
                interval_seconds = int(интервал[:-1]) * 3600
            else:
                try:
                    interval_seconds = int(интервал) * 3600
                except:
                    return await interaction.response.send_message(
                        embed=create_embed("❌ Ошибка", "Неверный формат интервала. Используйте: 1ч, 3ч, 6ч, 12ч, 24ч", EMBED_COLORS["error"]),
                        ephemeral=True
                    )
        
        # Получаем хранилище
        treasury_id = None
        if хранилище:
            treasury = await self.db.get_treasury_by_name(хранилище)
            if not treasury:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", f"Хранилище '{хранилище}' не найдено", EMBED_COLORS["error"]),
                    ephemeral=True
                )
            treasury_id = treasury['id']
        
        # Условия
        condition_type = None
        condition_value = None
        if тип_условия and тип_условия.value != "none":
            condition_type = тип_условия.value
            condition_value = значение_условия
        
        title_id = await self.db.create_title(
            название, зарплата, interval_seconds, treasury_id,
            condition_type, condition_value, interaction.user.id
        )
        
        if not title_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать титул", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Титул создан",
            f"Титул **{название}** успешно создан",
            EMBED_COLORS["success"]
        )
        if зарплата > 0:
            embed.add_field(name="Зарплата", value=f"{format_currency(зарплата)} / {интервал}", inline=True)
        if хранилище:
            embed.add_field(name="Хранилище", value=хранилище, inline=True)
        if condition_type:
            embed.add_field(name="Условие", value=f"{condition_type}: {condition_value}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="разрешить_титулы", description="Разрешить роли выдавать титулы (админ)")
    @app_commands.describe(
        роль="Роль",
        титулы="Названия титулов через запятую"
    )
    async def allow_titles(self, interaction: discord.Interaction,
                          роль: discord.Role,
                          титулы: str):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        title_names = [t.strip() for t in титулы.split(',')]
        allowed = []
        not_found = []
        
        for name in title_names:
            title = await self.db.get_title_by_name(name)
            if title:
                await self.db.add_title_permission(роль.id, title['id'], interaction.user.id)
                allowed.append(name)
            else:
                not_found.append(name)
        
        embed = create_embed(
            "✅ Разрешения настроены",
            f"Роль {роль.mention} может выдавать титулы",
            EMBED_COLORS["success"]
        )
        if allowed:
            embed.add_field(name="Разрешены", value=", ".join(allowed), inline=False)
        if not_found:
            embed.add_field(name="Не найдены", value=", ".join(not_found), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="выдать_титул", description="Выдать титул игроку")
    @app_commands.describe(
        игрок="Игрок",
        титул="Название титула"
    )
    async def grant_title(self, interaction: discord.Interaction,
                         игрок: discord.Member,
                         титул: str):
        
        # Проверяем, может ли пользователь выдавать этот титул
        allowed = False
        
        # Админ может всё
        admin_cog = self.bot.get_cog('AdminCog')
        if admin_cog and await admin_cog.is_admin(interaction):
            allowed = True
        
        # Проверяем по ролям
        if not allowed:
            title = await self.db.get_title_by_name(титул)
            if title:
                for role in interaction.user.roles:
                    allowed_titles = await self.db.get_allowed_titles_for_role(role.id)
                    if any(t['id'] == title['id'] for t in allowed_titles):
                        allowed = True
                        break
        
        if not allowed:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет прав выдавать этот титул", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        character = await self.db.get_character(игрок.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У игрока нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        title = await self.db.get_title_by_name(титул)
        if not title:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Титул '{титул}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.grant_title(игрок.id, title['id'], interaction.user.id)
        
        embed = create_embed(
            "✅ Титул выдан",
            f"Игроку {игрок.mention} выдан титул **{титул}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="снять_титул", description="Снять титул с игрока")
    @app_commands.describe(
        игрок="Игрок",
        титул="Название титула"
    )
    async def remove_title(self, interaction: discord.Interaction,
                          игрок: discord.Member,
                          титул: str):
        
        # Проверяем права (админ или тот, кто выдал)
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            # Проверяем, выдавал ли этот пользователь титул
            async with self.db.db.execute(
                '''SELECT ct.id FROM character_titles ct
                   JOIN titles t ON ct.title_id = t.id
                   WHERE ct.character_id = ? AND t.name = ? AND ct.granted_by = ?''',
                (игрок.id, титул, interaction.user.id)
            ) as cursor:
                granted = await cursor.fetchone()
            
            if not granted:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", "У вас нет прав снимать этот титул", EMBED_COLORS["error"]),
                    ephemeral=True
                )
        
        character = await self.db.get_character(игрок.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У игрока нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        title = await self.db.get_title_by_name(титул)
        if not title:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Титул '{титул}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.remove_title(игрок.id, title['id'])
        
        embed = create_embed(
            "✅ Титул снят",
            f"У игрока {игрок.mention} снят титул **{титул}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="титулы", description="Показать свои титулы")
    async def my_titles(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        titles = await self.db.get_character_titles(interaction.user.id)
        
        if not titles:
            return await interaction.response.send_message(
                embed=create_embed("📜 Титулы", "У вас нет титулов", EMBED_COLORS["info"])
            )
        
        embed = create_embed(
            f"📜 Титулы {character['character_name']}",
            color=EMBED_COLORS["info"]
        )
        
        for title in titles:
            value = ""
            if title['salary'] > 0:
                value += f"💰 {format_currency(title['salary'])} / {title['salary_interval']//3600}ч\n"
            if title['condition_type']:
                value += f"⚖️ Условие: {title['condition_type']}\n"
            if title['heir_id']:
                heir = await self.db.get_character(title['heir_id'])
                if heir:
                    value += f"👑 Наследник: {heir['character_name']}\n"
            
            embed.add_field(name=title['name'], value=value or "Нет доп. информации", inline=False)
        
        if character['active_title']:
            embed.set_footer(text=f"Активный: {character['active_title']}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="титул", description="Установить активный титул")
    @app_commands.describe(
        название="Название титула"
    )
    async def set_active_title(self, interaction: discord.Interaction, название: str):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.set_active_title(interaction.user.id, название)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет такого титула", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Титул установлен",
            f"Активный титул: **{название}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="назначить_наследника", description="Назначить наследника титула")
    @app_commands.describe(
        титул="Название титула",
        наследник="Игрок-наследник"
    )
    async def set_heir(self, interaction: discord.Interaction,
                      титул: str,
                      наследник: discord.Member):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        heir_char = await self.db.get_character(наследник.id)
        if not heir_char:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У наследника нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        title = await self.db.get_title_by_name(титул)
        if not title:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Титул '{титул}' не найден", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем, есть ли у пользователя этот титул
        user_titles = await self.db.get_character_titles(interaction.user.id)
        if not any(t['id'] == title['id'] for t in user_titles):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет этого титула", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.set_title_heir(interaction.user.id, title['id'], наследник.id)
        
        embed = create_embed(
            "✅ Наследник назначен",
            f"Титул **{титул}** будет передан {наследник.mention} после вашей смерти",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
