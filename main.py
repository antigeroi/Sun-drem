import discord
from discord.ext import commands
import asyncio
import os
import sys
from datetime import datetime
from config import TOKEN, GUILD_ID
from database import Database
from utils.timers import TimerManager
from utils.helpers import create_embed, EMBED_COLORS

# Импорт когов
from cogs.admin import AdminCog
from cogs.characters import CharactersCog
from cogs.economy import EconomyCog
from cogs.crafting import CraftingCog
from cogs.shops import ShopsCog
from cogs.guilds import GuildsCog
from cogs.bounty import BountyCog
from cogs.marriage import MarriageCog
from cogs.duel import DuelCog
from cogs.travel import TravelCog
from cogs.titles import TitlesCog
from cogs.letters import LettersCog
from cogs.treasury import TreasuryCog
from cogs.npc import NPCCog

class SunnyDreamBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None
        )
        
        self.db = Database()
        self.timer_manager = TimerManager(self)
        self.start_time = datetime.now()
    
    async def get_prefix(self, message):
        """Получение префикса персонажа"""
        if message.guild is None:
            return '/'
        
        character = await self.db.get_character(message.author.id)
        if character and character['prefix']:
            return character['prefix']
        
        return '/'
    
    async def setup_hook(self):
        """Настройка бота"""
        print("⚙️ Инициализация базы данных...")
        await self.db.init_db()
        
        print("📦 Загрузка модулей...")
        await self.add_cog(AdminCog(self))
        await self.add_cog(CharactersCog(self))
        await self.add_cog(EconomyCog(self))
        await self.add_cog(CraftingCog(self))
        await self.add_cog(ShopsCog(self))
        await self.add_cog(GuildsCog(self))
        await self.add_cog(BountyCog(self))
        await self.add_cog(MarriageCog(self))
        await self.add_cog(DuelCog(self))
        await self.add_cog(TravelCog(self))
        await self.add_cog(TitlesCog(self))
        await self.add_cog(LettersCog(self))
        await self.add_cog(TreasuryCog(self))
        await self.add_cog(NPCCog(self))
        
        print("🔄 Синхронизация команд...")
        try:
            if GUILD_ID:
                guild = discord.Object(id=GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"✅ Команды синхронизированы для сервера {GUILD_ID}")
            else:
                await self.tree.sync()
                print("✅ Команды синхронизированы глобально")
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
        
        print("🚀 Запуск таймеров...")
        await self.timer_manager.start()
    
    async def on_ready(self):
        """Событие готовности бота"""
        print(f'✅ Бот вошел как {self.user.name}')
        print(f'🆔 ID: {self.user.id}')
        
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Sunny Dream | /создать_персонажа"
        )
        await self.change_presence(activity=activity)
    
    async def on_message(self, message):
        """Обработка сообщений"""
        if message.author.bot:
            return
        
        character = await self.db.get_character(message.author.id)
        if character:
            await self.db.update_activity(message.author.id)
            
            if character['prefix'] and message.content.startswith(character['prefix']):
                content = message.content[len(character['prefix']):].strip()
                if content:
                    await self.send_roleplay_message(message, character, content)
                return
        
        await self.process_commands(message)
    
    async def send_roleplay_message(self, original_message, character, content):
        """Отправка ролевого сообщения"""
        try:
            await original_message.delete()
            
            webhook = await original_message.channel.create_webhook(name=character['character_name'])
            
            await webhook.send(
                content=content,
                username=character['character_name'],
                avatar_url=original_message.author.avatar.url if original_message.author.avatar else None
            )
            
            await webhook.delete()
            
        except Exception as e:
            print(f"Ошибка при отправке ролевого сообщения: {e}")
    
    async def on_command_error(self, ctx, error):
        """Обработка ошибок команд"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        embed = create_embed(
            "❌ Ошибка",
            str(error),
            EMBED_COLORS["error"]
        )
        await ctx.send(embed=embed, ephemeral=True)

async def main():
    """Запуск бота"""
    if not TOKEN:
        print("❌ Токен не найден! Создайте файл .env с DISCORD_TOKEN")
        sys.exit(1)
    
    os.makedirs('data', exist_ok=True)
    
    bot = SunnyDreamBot()
    
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
