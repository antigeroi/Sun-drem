import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))

# Роли
ADMIN_ROLE_NAME = "Администратор Sunny Dream"
JUDGE_ROLE_NAME = "Судья"
EXECUTIONER_ROLE_NAME = "Палач"

# Экономика
CURRENCY_NAME = "астрал"
CURRENCY_PLURAL = "астралов"
CURRENCY_SYMBOL = "⍟"

# Гильдии
GUILD_CREATION_COST = 100
GUILD_BANK_TAX = 0.05

# Голод
HUNGER_DECREASE_PER_ACTIVE_MINUTE = 1
HUNGER_ACTIVE_CHECK_INTERVAL = 120
MAX_HUNGER = 100
DEATH_TIMER_MINUTES = 10

# Поиск
SEARCH_COOLDOWN_HOURS = 1
SEARCH_SUCCESS_CHANCE = 0.6
SCROLL_CHANCE = 0.1

# Крафт
CRAFT_FAIL_CHANCE = 0.1
CRAFT_BOOK_DROP_CHANCE = 0.2

# Охота за головами
BOUNTY_COMPLETION_DAYS = 3

# Паспорт
PASSPORT_PICKUP_SECONDS = 20

# Путешествия
TRAVEL_MEET_CHANCE = 0.3
TRAVEL_REST_MINUTES = 3

# NPC
NPC_WITNESS_CHANCE = 0.5

# Цвета для эмбедов
EMBED_COLORS = {
    "success": 0x00FF00,
    "error": 0xFF0000,
    "warning": 0xFFA500,
    "info": 0x3498DB,
    "guild": 0x2ECC71,
    "admin": 0x9B59B6,
    "death": 0x2C3E50,
    "bounty": 0xE67E22,
    "marriage": 0xE91E63,
    "duel": 0x1ABC9C,
    "travel": 0x95A5A6,
    "npc": 0x27AE60
}
