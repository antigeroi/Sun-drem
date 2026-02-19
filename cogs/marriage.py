# ========== 19. cogs/marriage.py ==========
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from database import Database
from config import *
from utils.helpers import *

class MarriageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="предложение", description="Сделать предложение брака")
    @app_commands.describe(
        игрок="Игрок, которому делаете предложение"
    )
    async def propose(self, interaction: discord.Interaction, игрок: discord.Member):
        proposer = await self.db.get_character(interaction.user.id)
        if not proposer:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if игрок.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Нельзя жениться на себе", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        target = await self.db.get_character(игрок.id)
        if not target:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У цели нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        existing = await self.db.get_active_marriage(interaction.user.id)
        if existing:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы уже состоите в браке или имеете активное предложение", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        existing = await self.db.get_active_marriage(игрок.id)
        if existing:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Цель уже состоит в браке или имеет активное предложение", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = await self.db.propose_marriage(interaction.user.id, игрок.id)
        
        if not marriage_id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось создать предложение", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        embed = create_embed(
            "💍 Предложение брака",
            f"{proposer['character_name']} делает предложение {target['character_name']}!",
            EMBED_COLORS["marriage"]
        )
        embed.add_field(name="Срок", value="24 часа на ответ", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        try:
            dm_embed = create_embed(
                "💍 Вам сделали предложение!",
                f"**{proposer['character_name']}** предлагает вам вступить в брак.\n"
                f"Используйте `/принять` чтобы согласиться или `/отказать` чтобы отказаться.",
                EMBED_COLORS["marriage"]
            )
            await игрок.send(embed=dm_embed)
        except:
            pass
    
    @app_commands.command(name="принять", description="Принять предложение брака")
    async def accept(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM marriages 
               WHERE spouse2_id = ? AND status = 'pending' 
               AND proposed_at > datetime('now', '-1 day')''',
            (interaction.user.id,)
        ) as cursor:
            marriage = await cursor.fetchone()
        
        if not marriage:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет активных предложений", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = marriage[0]
        proposer_id = marriage[1]
        
        proposer = await self.db.get_character(proposer_id)
        
        await self.db.accept_marriage(marriage_id)
        
        embed = create_embed(
            "💍 Предложение принято!",
            f"**{character['character_name']}** принял(а) предложение **{proposer['character_name']}**!\n"
            f"Теперь вы можете провести свадебную церемонию.",
            EMBED_COLORS["marriage"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="отказать", description="Отказать в предложении брака")
    async def decline(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM marriages 
               WHERE spouse2_id = ? AND status = 'pending' 
               AND proposed_at > datetime('now', '-1 day')''',
            (interaction.user.id,)
        ) as cursor:
            marriage = await cursor.fetchone()
        
        if not marriage:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет активных предложений", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = marriage[0]
        proposer_id = marriage[1]
        
        proposer = await self.db.get_character(proposer_id)
        
        async with self.db.db.execute('DELETE FROM marriages WHERE id = ?', (marriage_id,)):
            await self.db.db.commit()
        
        embed = create_embed(
            "💔 Отказ",
            f"**{character['character_name']}** отказал(а) **{proposer['character_name']}**.",
            EMBED_COLORS["error"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="свадьба", description="Провести свадебную церемонию")
    async def marry(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        async with self.db.db.execute(
            '''SELECT * FROM marriages 
               WHERE (spouse1_id = ? OR spouse2_id = ?) 
               AND status = 'accepted' 
               AND accepted_at > datetime('now', '-3 day')''',
            (interaction.user.id, interaction.user.id)
        ) as cursor:
            marriage = await cursor.fetchone()
        
        if not marriage:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет принятых предложений", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage_id = marriage[0]
        spouse1_id = marriage[1]
        spouse2_id = marriage[2]
        
        spouse1 = await self.db.get_character(spouse1_id)
        spouse2 = await self.db.get_character(spouse2_id)
        
        await self.db.marry(marriage_id)
        
        embed = create_embed(
            "💒 Свадьба состоялась!",
            f"**{spouse1['character_name']}** и **{spouse2['character_name']}** теперь муж и жена!",
            EMBED_COLORS["marriage"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="развод", description="Подать на развод")
    async def divorce(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        spouse_id = marriage['spouse1_id'] if marriage['spouse2_id'] == interaction.user.id else marriage['spouse2_id']
        spouse = await self.db.get_character(spouse_id)
        
        view = ConfirmView()
        embed = create_embed(
            "⚠️ Подтверждение развода",
            f"Вы уверены, что хотите развестись с **{spouse['character_name']}**?",
            EMBED_COLORS["warning"]
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        if view.value:
            await self.db.divorce(marriage['id'])
            
            embed = create_embed(
                "💔 Развод оформлен",
                f"Брак между **{character['character_name']}** и **{spouse['character_name']}** расторгнут.",
                EMBED_COLORS["error"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            embed = create_embed(
                "✅ Отменено",
                "Развод отменен",
                EMBED_COLORS["success"]
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
    @app_commands.command(name="семейный_банк", description="Управление семейным банком")
    async def family_bank(self, interaction: discord.Interaction):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        balance = await self.db.get_marriage_bank(marriage['id'])
        
        embed = create_embed(
            "💰 Семейный банк",
            f"Баланс: {format_currency(balance)}",
            EMBED_COLORS["info"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="положить_в_банк", description="Положить деньги в семейный банк")
    @app_commands.describe(
        сумма="Сумма"
    )
    async def deposit_to_family(self, interaction: discord.Interaction, сумма: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
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
        
        await self.db.update_balance(interaction.user.id, -сумма)
        await self.db.add_to_marriage_bank(marriage['id'], сумма)
        
        embed = create_embed(
            "✅ Деньги положены",
            f"Вы положили {format_currency(сумма)} в семейный банк",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="снять_с_банка", description="Снять деньги из семейного банка")
    @app_commands.describe(
        сумма="Сумма"
    )
    async def withdraw_from_family(self, interaction: discord.Interaction, сумма: int):
        character = await self.db.get_character(interaction.user.id)
        if not character:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "У вас нет персонажа", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        marriage = await self.db.get_active_marriage(interaction.user.id)
        
        if not marriage or marriage['status'] != 'married':
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Вы не состоите в браке", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        if сумма <= 0:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Сумма должна быть положительной", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        balance = await self.db.get_marriage_bank(marriage['id'])
        
        if balance < сумма:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", f"В банке недостаточно денег. Баланс: {format_currency(balance)}", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        success = await self.db.remove_from_marriage_bank(marriage['id'], сумма)
        
        if not success:
            return await interaction.response.send_message(
                embed=create_embed("❌ Ошибка", "Не удалось снять деньги", EMBED_COLORS["error"]),
                ephemeral=True
            )
        
        await self.db.update_balance(interaction.user.id, сумма)
        
        embed = create_embed(
            "✅ Деньги сняты",
            f"Вы сняли {format_currency(сумма)} из семейного банка",
            EMBED_COLORS["success"]
        )
        
        await interaction.response.send_message(embed=embed)


# ========== 20. cogs/duel.py ==========
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


# ========== 21. cogs/travel.py ==========
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


# ========== 22. cogs/titles.py ==========
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


# ========== 23. cogs/letters.py ==========
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


# ========== 24. cogs/treasury.py ==========
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


# ========== 25. cogs/npc.py ==========
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
