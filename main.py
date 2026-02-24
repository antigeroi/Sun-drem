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
    print("❌ Нет токена")
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
        
        print("🔄 Синхронизация команд...")
        try:
            guild = discord.Object(id=GUILD_ID)
            
            # ЖЕСТКО: удаляем все глобальные команды
            self.tree.clear_commands(guild=None)
            
            # Добавляем все команды только для твоего сервера
            for cog_name, cog in self.cogs.items():
                for cmd in cog.get_app_commands():
                    self.tree.add_command(cmd, guild=guild)
            
            # Синхронизируем
            await self.tree.sync(guild=guild)
            print(f"✅ Команды синхронизированы для сервера {GUILD_ID}")
            
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")

    async def on_ready(self):
        print(f'✅ Бот запущен как {self.user.name}')
        print(f'На серверах: {len(self.guilds)}')

async def main():
    os.makedirs('data', exist_ok=True)
    bot = SunnyDreamBot()
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
