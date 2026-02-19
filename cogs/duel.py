import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import Database
from config import *
from utils.helpers import *

class DuelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="вызвать_на_дуэль", description="Вызвать игрока на дуэль")
    @app_commands.describe(
        противник="Противник",
        ставка="Ставка (0 если без ставки)"
    )
    async def challenge(self, interaction: discord.Interaction,
                       противник: discord.Member,
                       ставка: int = 0):
        
        challenger = await self.db.get_character(interaction.user.id)
        if not challenger:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if противник.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нельзя вызвать на дуэль себя", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        opponent = await self.db.get_character(противник.id)
        if not opponent:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У противника нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if ставка < 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Ставка не может быть отрицательной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if ставка > 0:
            if challenger['balance'] < ставка:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", f"У вас недостаточно денег для ставки. Баланс: {format_currency(challenger['balance'])}", EMBED_COLORS["error"]),
                    ephemeral=True
                )
            if opponent['balance'] < ставка:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", f"У противника недостаточно денег для ставки. Баланс: {format_currency(opponent['balance'])}", EMBED_COLORS["error"]),
                    ephemeral=True
                )
        
        duel_id = await self.db.create_duel(
            interaction.user.id, противник.id, ставка, interaction.channel.id
        )
        
        if not duel_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать дуэль", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "⚔️ Вызов на дуэль!",
            f"**{challenger['character_name']}** вызывает **{opponent['character_name']}** на дуэль!",
            EMBED_COLORS["duel"]
        )
        if ставка > 0:
            embed.add_field(name="Ставка", value=format_currency(ставка), inline=True)
        embed.add_field(name="Срок", value="24 часа на ответ", inline=True)
        embed.set_footer(text="Используйте /принять_дуэль или /отказаться_от_дуэли")
        
        await interaction.response.send_message(embed=embed)
        
        try:
            dm_embed = create_embed(
                "⚔️ Вас вызвали на дуэль!",
                f"**{challenger['character_name']}** вызывает вас на дуэль.\n"
                f"Используйте `/принять_дуэль` чтобы принять или `/отказаться_от_дуэли` чтобы отказаться.",
                EMBED_COLORS["duel"]
            )
            if ставка > 0:
                dm_embed.add_field(name="Ставка", value=format_currency(ставка), inline=True)
            await противник.send(embed=dm_embed)
        except:
            pass
    
    @app_commands.command(name="принять_дуэль", description="Принять вызов на дуэль")
    @app_commands.describe(
        противник="Игрок, который вызвал"
    )
    async def accept_duel(self, interaction: discord.Interaction, противник: discord.Member):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM duels 
               WHERE challenger_id = ? AND opponent_id = ? AND status = 'pending' 
               AND created_at > datetime('now', '-1 day')''',
            (противник.id, interaction.user.id)
        ) as cursor:
            duel = await cursor.fetchone()
        
        if not duel:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Активная дуэль не найдена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        duel_id = duel[0]
        stake = duel[3]
        
        if stake > 0:
            challenger_char = await self.db.get_character(противник.id)
            if challenger_char['balance'] < stake:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", "У вызвавшего недостаточно денег для ставки", EMBED_COLORS["error"]),
                    ephemeral=True
                )
            if character['balance'] < stake:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Ошибка", f"У вас недостаточно денег. Нужно: {format_currency(stake)}", EMBED_COLORS["error"]),
                    ephemeral=True
                )
        
        await self.db.accept_duel(duel_id)
        
        embed = create_embed(
            "⚔️ Дуэль принята!",
            f"**{character['character_name']}** принял(а) вызов!",
            EMBED_COLORS["duel"]
        )
        embed.add_field(name="Следующий шаг", value="Пригласите 2 свидетелей командой `/свидетель @игрок`", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="отказаться_от_дуэли", description="Отказаться от дуэли")
    async def decline_duel(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM duels 
               WHERE opponent_id = ? AND status = 'pending' 
               AND created_at > datetime('now', '-1 day')''',
            (interaction.user.id,)
        ) as cursor:
            duel = await cursor.fetchone()
        
        if not duel:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Активная дуэль не найдена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        duel_id = duel[0]
        challenger_id = duel[1]
        challenger = await self.db.get_character(challenger_id)
        
        async with self.db.db.execute('DELETE FROM duels WHERE id = ?', (duel_id,)):
            await self.db.db.commit()
        
        embed = create_embed(
            "❌ Отказ от дуэли",
            f"**{character['character_name']}** отказался от дуэли с **{challenger['character_name']}**.",
            EMBED_COLORS["error"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="свидетель", description="Пригласить свидетеля на дуэль")
    @app_commands.describe(
        игрок="Игрок, который будет свидетелем"
    )
    async def witness(self, interaction: discord.Interaction, игрок: discord.Member):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM duels 
               WHERE (challenger_id = ? OR opponent_id = ?) 
               AND status = 'accepted' 
               AND created_at > datetime('now', '-1 day')''',
            (interaction.user.id, interaction.user.id)
        ) as cursor:
            duel = await cursor.fetchone()
        
        if not duel:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Активная дуэль не найдена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        duel_id = duel[0]
        
        witness_char = await self.db.get_character(игрок.id)
        if not witness_char:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У свидетеля нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.add_witness(duel_id, игрок.id)
        
        async with self.db.db.execute(
            'SELECT COUNT(*) FROM duel_witnesses WHERE duel_id = ?',
            (duel_id,)
        ) as cursor:
            count = await cursor.fetchone()
            witness_count = count[0] if count else 0
        
        embed = create_embed(
            "👀 Свидетель приглашен",
            f"**{witness_char['character_name']}** приглашен как свидетель.\n"
            f"Всего свидетелей: {witness_count}/5",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="завершить_дуэль", description="Завершить дуэль (только для свидетелей)")
    @app_commands.describe(
        победитель="Игрок, который победил",
        побежденный="Игрок, который проиграл"
    )
    async def complete_duel(self, interaction: discord.Interaction,
                           победитель: discord.Member,
                           побежденный: discord.Member):
        
        witness = await self.db.get_character(interaction.user.id)
        if not witness:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM duels 
               WHERE ((challenger_id = ? AND opponent_id = ?) OR (challenger_id = ? AND opponent_id = ?))
               AND status = 'accepted' 
               AND created_at > datetime('now', '-1 day')''',
            (победитель.id, побежденный.id, побежденный.id, победитель.id)
        ) as cursor:
            duel = await cursor.fetchone()
        
        if not duel:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Активная дуэль не найдена", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        duel_id = duel[0]
        
        async with self.db.db.execute(
            'SELECT 1 FROM duel_witnesses WHERE duel_id = ? AND user_id = ?',
            (duel_id, interaction.user.id)
        ) as cursor:
            is_witness = await cursor.fetchone()
        
        if not is_witness:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Только свидетели могут завершить дуэль", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            'SELECT COUNT(*) FROM duel_witnesses WHERE duel_id = ?',
            (duel_id,)
        ) as cursor:
            count = await cursor.fetchone()
            witness_count = count[0] if count else 0
        
        if witness_count < 2:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"Нужно минимум 2 свидетеля (сейчас {witness_count})", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        winner_id = победитель.id
        success = await self.db.complete_duel(duel_id, winner_id)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось завершить дуэль", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        winner_char = await self.db.get_character(победитель.id)
        loser_char = await self.db.get_character(побежденный.id)
        
        embed = create_embed(
            "⚔️ Дуэль завершена!",
            f"Победитель: **{winner_char['character_name']}**\n"
            f"Побежденный: **{loser_char['character_name']}** пал в бою.",
            EMBED_COLORS["duel"]
        )
        
        await interaction.response.send_message(embed=embed)
