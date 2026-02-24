# deploy_commands.py - ЗАПУСКАЙ ТОЛЬКО КОГДА МЕНЯЕШЬ КОМАНДЫ!
import asyncio
import discord
from discord.ext import commands
import os
import sys
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1361604463072247958

if not TOKEN:
    print("❌ Нет токена в .env файле!")
    sys.exit(1)

# Импортируем все коги
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

async def deploy():
    print("🚀 ЗАПУСК ДЕПЛОЯ КОМАНД")
    
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='/', intents=intents)
    
    print("📦 Загрузка модулей...")
    await bot.add_cog(AdminCog(bot))
    await bot.add_cog(CharactersCog(bot))
    await bot.add_cog(EconomyCog(bot))
    await bot.add_cog(CraftingCog(bot))
    await bot.add_cog(ShopsCog(bot))
    await bot.add_cog(GuildsCog(bot))
    await bot.add_cog(BountyCog(bot))
    await bot.add_cog(MarriageCog(bot))
    await bot.add_cog(DuelCog(bot))
    await bot.add_cog(TravelCog(bot))
    await bot.add_cog(TitlesCog(bot))
    await bot.add_cog(LettersCog(bot))
    await bot.add_cog(TreasuryCog(bot))
    await bot.add_cog(NPCCog(bot))
    
    print("🔄 Очистка старых команд...")
    guild = discord.Object(id=GUILD_ID)
    
    # Полностью очищаем все команды
    bot.tree.clear_commands(guild=None)
    bot.tree.clear_commands(guild=guild)
    
    # Копируем команды только для твоего сервера
    bot.tree.copy_global_to(guild=guild)
    
    print("📝 Синхронизация команд...")
    await bot.tree.sync(guild=guild)
    
    print(f"✅ Команды успешно задеплоены для сервера {GUILD_ID}!")
    print(f"📊 Всего команд: {len(bot.tree.get_commands(guild=guild))}")
    
    await bot.close()

if __name__ == "__main__":
    asyncio.run(deploy())
    print("🏁 Деплой завершен, можно запускать main.py")
