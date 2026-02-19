import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from database import Database
from config import *
from utils.helpers import *

class TreasuryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="создать_хранилище", description="Создать новое хранилище (админ)")
    @app_commands.describe(
        название="Название хранилища",
        описание="Описание"
    )
    async def create_treasury(self, interaction: discord.Interaction,
                              название: str,
                              описание: str = ""):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        treasury_id = await self.db.create_treasury(название, описание, interaction.user.id)
        
        if not treasury_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать хранилище", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "✅ Хранилище создано",
            f"Хранилище **{название}** успешно создано",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="доступ_к_хранилищу", description="Настроить доступ к хранилищу (админ)")
    @app_commands.describe(
        хранилище="Название хранилища",
        роль="Роль",
        действие="Что разрешить"
    )
    @app_commands.choices(действие=[
        app_commands.Choice(name="класть", value="deposit"),
        app_commands.Choice(name="брать", value="withdraw"),
        app_commands.Choice(name="оба", value="both")
    ])
    async def treasury_access(self, interaction: discord.Interaction,
                             хранилище: str,
                             роль: discord.Role,
                             действие: app_commands.Choice[str]):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        treasury = await self.db.get_treasury_by_name(хранилище)
        if not treasury:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Хранилище '{хранилище}' не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        can_deposit = действие.value in ['deposit', 'both']
        can_withdraw = действие.value in ['withdraw', 'both']
        
        await self.db.add_treasury_access(treasury['id'], роль.id, can_deposit, can_withdraw)
        
        embed = create_embed(
            "✅ Доступ настроен",
            f"Роль {роль.mention} может {действие.name} в хранилище **{хранилище}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="баланс_хранилища", description="Показать баланс хранилища")
    @app_commands.describe(
        хранилище="Название хранилища"
    )
    async def treasury_balance(self, interaction: discord.Interaction, хранилище: str):
        treasury = await self.db.get_treasury_by_name(хранилище)
        if not treasury:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Хранилище '{хранилище}' не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            f"💰 Баланс: {хранилище}",
            f"В хранилище {format_currency(treasury['balance'])}",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="положить_в_хранилище", description="Положить деньги в хранилище")
    @app_commands.describe(
        хранилище="Название хранилища",
        сумма="Сумма"
    )
    async def deposit_to_treasury(self, interaction: discord.Interaction,
                                  хранилище: str,
                                  сумма: int):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        treasury = await self.db.get_treasury_by_name(хранилище)
        if not treasury:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Хранилище '{хранилище}' не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if сумма <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Сумма должна быть положительной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if character['balance'] < сумма:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Недостаточно денег. У вас {format_currency(character['balance'])}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем доступ
        has_access = await self.db.check_treasury_access(treasury['id'], interaction.user.id, 'deposit')
        if not has_access:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет прав класть деньги в это хранилище", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_balance(interaction.user.id, -сумма)
        await self.db.deposit_to_treasury(treasury['id'], interaction.user.id, сумма)
        
        embed = create_embed(
            "✅ Деньги положены",
            f"Вы положили {format_currency(сумма)} в хранилище **{хранилище}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="взять_из_хранилища", description="Взять деньги из хранилища")
    @app_commands.describe(
        хранилище="Название хранилища",
        сумма="Сумма"
    )
    async def withdraw_from_treasury(self, interaction: discord.Interaction,
                                     хранилище: str,
                                     сумма: int):
        
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        treasury = await self.db.get_treasury_by_name(хранилище)
        if not treasury:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Хранилище '{хранилище}' не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if сумма <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Сумма должна быть положительной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if treasury['balance'] < сумма:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"В хранилище недостаточно денег. Баланс: {format_currency(treasury['balance'])}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем доступ
        has_access = await self.db.check_treasury_access(treasury['id'], interaction.user.id, 'withdraw')
        if not has_access:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет прав брать деньги из этого хранилища", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.withdraw_from_treasury(treasury['id'], interaction.user.id, сумма)
        await self.db.update_balance(interaction.user.id, сумма)
        
        embed = create_embed(
            "✅ Деньги взяты",
            f"Вы взяли {format_currency(сумма)} из хранилища **{хранилище}**",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="настройка_налогов", description="Настроить налоги (админ)")
    @app_commands.describe(
        хранилище="Хранилище для сбора налогов",
        ставка="Ставка налога в процентах (0-20)",
        роль_налоговика="Роль, которая может менять ставку"
    )
    async def tax_settings(self, interaction: discord.Interaction,
                          хранилище: str,
                          ставка: int,
                          роль_налоговика: discord.Role):
        
        admin_cog = self.bot.get_cog('AdminCog')
        if not admin_cog or not await admin_cog.is_admin(interaction):
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Недостаточно прав", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if ставка < 0 or ставка > 20:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Ставка должна быть от 0 до 20", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        treasury = await self.db.get_treasury_by_name(хранилище)
        if not treasury:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Хранилище '{хранилище}' не найдено", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.set_tax_settings(treasury['id'], ставка, роль_налоговика.id)
        
        embed = create_embed(
            "💰 Налоги настроены",
            f"Ставка налога: {ставка}%\n"
            f"Хранилище: **{хранилище}**\n"
            f"Налоговик: {роль_налоговика.mention}",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="установить_налог", description="Изменить ставку налога")
    @app_commands.describe(
        ставка="Новая ставка (0-20)"
    )
    async def set_tax_rate(self, interaction: discord.Interaction, ставка: int):
        if ставка < 0 or ставка > 20:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Ставка должна быть от 0 до 20", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        tax_settings = await self.db.get_tax_settings()
        if not tax_settings:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Налоги не настроены", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        # Проверяем, есть ли у пользователя роль налоговика
        if tax_settings['tax_manager_role_id'] not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет прав менять налоги", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.set_tax_settings(
            tax_settings['treasury_id'],
            ставка,
            tax_settings['tax_manager_role_id']
        )
        
        embed = create_embed(
            "💰 Ставка налога изменена",
            f"Новая ставка: {ставка}%",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="налоговая_ставка", description="Показать текущую ставку налога")
    async def tax_rate(self, interaction: discord.Interaction):
        tax_settings = await self.db.get_tax_settings()
        
        if not tax_settings:
            return await interaction.response.send_message(
                embed=create_embed("💰 Налоги", "Налоги не настроены", EMBED_COLORS["info"])
            )
        
        treasury = await self.db.get_treasury(tax_settings['treasury_id'])
        treasury_name = treasury['name'] if treasury else "Неизвестно"
        
        embed = create_embed(
            "💰 Текущая налоговая ставка",
            f"Ставка: {tax_settings['tax_rate']}%\n"
            f"Хранилище: **{treasury_name}**",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="налоговая_статистика", description="Показать статистику налогов за последние 3 часа")
    async def tax_stats(self, interaction: discord.Interaction):
        stats = await self.db.get_tax_stats()
        
        if not stats:
            return await interaction.response.send_message(
                embed=create_embed("📊 Налоговая статистика", "За последние 3 часа налогов не было", EMBED_COLORS["info"])
            )
        
        total = sum(s['amount'] for s in stats)
        
        embed = create_embed(
            "📊 Налоговая статистика (за 3 часа)",
            f"Всего собрано: {format_currency(total)}",
            EMBED_COLORS["info"]
        )
        
        top_payers = {}
        for stat in stats:
            top_payers[stat['payer_name']] = top_payers.get(stat['payer_name'], 0) + stat['amount']
        
        top_list = sorted(top_payers.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if top_list:
            embed.add_field(
                name="🏆 Топ плательщиков",
                value="\n".join([f"{name}: {format_currency(amount)}" for name, amount in top_list]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
