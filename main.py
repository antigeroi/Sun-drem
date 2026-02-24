import discord
from discord.ext import commands
import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1361604463072247958

if not TOKEN:
    print("❌ Нет токена в .env файле!")
    sys.exit(1)

from database import Database
from utils.timers import TimerManager
from utils.helpers import create_embed, EMBED_COLORS

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
        
        super().__init__(command_prefix='/', intents=intents, help_command=None)
        self.db = Database()
        self.timer_manager = TimerManager(self)

    async def setup_hook(self):
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
        
        # ===== ВАРИАНТ 1: СИНХРОНИЗАЦИЯ ТОЛЬКО ПРИ НЕОБХОДИМОСТИ =====
        print("🔄 Проверка команд...")
        try:
            guild = discord.Object(id=GUILD_ID)
            
            # Проверяем какие команды уже есть
            existing_commands = await self.tree.fetch_commands(guild=guild)
            print(f"Найдено {len(existing_commands)} существующих команд")
            
            # Синхронизируем только если команд нет или их мало
            if len(existing_commands) < 10:  # Если меньше 10 команд (явно первый запуск)
                print("🔄 Первичная синхронизация команд...")
                self.tree.clear_commands(guild=None)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"✅ Команды синхронизированы для сервера {GUILD_ID}")
            else:
                print("✅ Команды уже существуют, пропускаем синхронизацию")
                
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
            print("👉 Бот продолжит работу, но команды могут не обновиться")

    async def on_ready(self):
        print(f'✅ Бот запущен как {self.user.name}')
        print(f'На серверах: {len(self.guilds)}')
        for guild in self.guilds:
            print(f'  - {guild.name} (ID: {guild.id})')
        
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Sunny Dream | /создать_персонажа"
        )
        await self.change_presence(activity=activity)

async def main():
    os.makedirs('data', exist_ok=True)
    bot = SunnyDreamBot()
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
        await bot.close()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
