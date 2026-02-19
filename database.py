import aiosqlite
import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from config import *

class Database:
    def __init__(self, db_path='data/database.db'):
        self.db_path = db_path
        
    async def init_db(self):
        """Инициализация базы данных"""
        import os
        os.makedirs('data', exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Персонажи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    user_id INTEGER PRIMARY KEY,
                    character_name TEXT NOT NULL,
                    prefix TEXT NOT NULL CHECK(length(prefix) >= 2),
                    gender TEXT NOT NULL,
                    biography TEXT NOT NULL CHECK(length(biography) >= 500),
                    hunger INTEGER DEFAULT 100 CHECK(hunger >= 0 AND hunger <= 100),
                    balance INTEGER DEFAULT 0,
                    guild_id INTEGER,
                    family_id INTEGER,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    death_timer_start TIMESTAMP,
                    is_alive BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_search TIMESTAMP,
                    active_title TEXT,
                    passport_holder_id INTEGER,
                    current_location TEXT,
                    travel_start TIMESTAMP,
                    travel_end TIMESTAMP,
                    travel_destination TEXT,
                    FOREIGN KEY (guild_id) REFERENCES guilds(id) ON DELETE SET NULL,
                    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET NULL
                )
            ''')
            
            # Роды
            await db.execute('''
                CREATE TABLE IF NOT EXISTS families (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    drop_chance INTEGER DEFAULT 10,
                    created_by INTEGER
                )
            ''')
            
            # Связь персонажа с родом
            await db.execute('''
                CREATE TABLE IF NOT EXISTS character_family (
                    character_id INTEGER,
                    family_id INTEGER,
                    PRIMARY KEY (character_id, family_id),
                    FOREIGN KEY (character_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
                )
            ''')
            
            # Титулы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS titles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    salary INTEGER DEFAULT 0,
                    salary_interval INTEGER DEFAULT 0,
                    treasury_id INTEGER,
                    condition_type TEXT,
                    condition_value TEXT,
                    created_by INTEGER
                )
            ''')
            
            # Выданные титулы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS character_titles (
                    character_id INTEGER,
                    title_id INTEGER,
                    granted_by INTEGER,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    heir_id INTEGER,
                    PRIMARY KEY (character_id, title_id),
                    FOREIGN KEY (character_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (title_id) REFERENCES titles(id) ON DELETE CASCADE,
                    FOREIGN KEY (heir_id) REFERENCES characters(user_id) ON DELETE SET NULL
                )
            ''')
            
            # Разрешения на выдачу титулов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS title_permissions (
                    role_id INTEGER,
                    title_id INTEGER,
                    granted_by INTEGER,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (role_id, title_id)
                )
            ''')
            
            # Предметы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    transferable BOOLEAN DEFAULT TRUE,
                    price INTEGER DEFAULT 0,
                    type TEXT CHECK(type IN ('оружие', 'материал', 'еда', 'лотерея', 'книга_крафта', 'яд', 'жилье', 'письмо', 'другое')),
                    hunger_restore INTEGER DEFAULT 0,
                    poison_effect TEXT,
                    craft_book_id INTEGER,
                    lottery_id INTEGER,
                    housing_locations TEXT,
                    letter_content TEXT,
                    letter_author INTEGER,
                    letter_recipient INTEGER,
                    letter_sealed BOOLEAN DEFAULT FALSE,
                    letter_encrypted BOOLEAN DEFAULT FALSE,
                    letter_key TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Инвентарь
            await db.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER,
                    item_id INTEGER,
                    quantity INTEGER DEFAULT 1 CHECK(quantity >= 0),
                    PRIMARY KEY (user_id, item_id),
                    FOREIGN KEY (user_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                )
            ''')
            
            # Магазины
            await db.execute('''
                CREATE TABLE IF NOT EXISTS shops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    location TEXT,
                    channel_id INTEGER,
                    owner_id INTEGER,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES characters(user_id) ON DELETE SET NULL
                )
            ''')
            
            # Товары в магазинах
            await db.execute('''
                CREATE TABLE IF NOT EXISTS shop_stock (
                    shop_id INTEGER,
                    item_id INTEGER,
                    quantity INTEGER DEFAULT 0 CHECK(quantity >= 0),
                    current_price INTEGER,
                    PRIMARY KEY (shop_id, item_id),
                    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                )
            ''')
            
            # Крафты
            await db.execute('''
                CREATE TABLE IF NOT EXISTS crafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    result_item_id INTEGER NOT NULL,
                    material_item_id INTEGER NOT NULL,
                    required_quantity INTEGER DEFAULT 1,
                    result_quantity INTEGER DEFAULT 1,
                    craft_price INTEGER DEFAULT 0,
                    book_name TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (result_item_id) REFERENCES items(id) ON DELETE CASCADE,
                    FOREIGN KEY (material_item_id) REFERENCES items(id) ON DELETE CASCADE
                )
            ''')
            
            # Изученные крафты
            await db.execute('''
                CREATE TABLE IF NOT EXISTS learned_crafts (
                    user_id INTEGER,
                    craft_id INTEGER,
                    learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, craft_id),
                    FOREIGN KEY (user_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (craft_id) REFERENCES crafts(id) ON DELETE CASCADE
                )
            ''')
            
            # Книги крафта
            await db.execute('''
                CREATE TABLE IF NOT EXISTS craft_books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_by INTEGER
                )
            ''')
            
            # Свитки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS scrolls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    is_ancient BOOLEAN DEFAULT FALSE,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Лотереи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lotteries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    ticket_item_id INTEGER,
                    price INTEGER DEFAULT 0,
                    prizes_json TEXT NOT NULL,
                    win_chance REAL DEFAULT 0.3,
                    total_tickets INTEGER DEFAULT -1,
                    sold_tickets INTEGER DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (ticket_item_id) REFERENCES items(id) ON DELETE SET NULL
                )
            ''')
            
            # Заказы на охоту
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bounties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_id INTEGER NOT NULL,
                    reward INTEGER NOT NULL,
                    reason TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hunter_id INTEGER,
                    expires_at TIMESTAMP,
                    completed BOOLEAN DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    channel_id INTEGER,
                    FOREIGN KEY (target_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (hunter_id) REFERENCES characters(user_id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by) REFERENCES characters(user_id) ON DELETE SET NULL
                )
            ''')
            
            # Каналы для охоты
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bounty_channels (
                    channel_id INTEGER PRIMARY KEY
                )
            ''')
            
            # Браки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS marriages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spouse1_id INTEGER NOT NULL,
                    spouse2_id INTEGER NOT NULL,
                    proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accepted_at TIMESTAMP,
                    married_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (spouse1_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (spouse2_id) REFERENCES characters(user_id) ON DELETE CASCADE
                )
            ''')
            
            # Семейный банк
            await db.execute('''
                CREATE TABLE IF NOT EXISTS family_bank (
                    marriage_id INTEGER,
                    balance INTEGER DEFAULT 0,
                    PRIMARY KEY (marriage_id),
                    FOREIGN KEY (marriage_id) REFERENCES marriages(id) ON DELETE CASCADE
                )
            ''')
            
            # Дуэли
            await db.execute('''
                CREATE TABLE IF NOT EXISTS duels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenger_id INTEGER NOT NULL,
                    opponent_id INTEGER NOT NULL,
                    stake INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    channel_id INTEGER,
                    winner_id INTEGER,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (challenger_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (opponent_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (winner_id) REFERENCES characters(user_id) ON DELETE SET NULL
                )
            ''')
            
            # Свидетели дуэли
            await db.execute('''
                CREATE TABLE IF NOT EXISTS duel_witnesses (
                    duel_id INTEGER,
                    user_id INTEGER,
                    PRIMARY KEY (duel_id, user_id),
                    FOREIGN KEY (duel_id) REFERENCES duels(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES characters(user_id) ON DELETE CASCADE
                )
            ''')
            
            # Активность
            await db.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    user_id INTEGER,
                    last_message TIMESTAMP,
                    last_voice_join TIMESTAMP,
                    last_voice_leave TIMESTAMP,
                    is_active BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (user_id),
                    FOREIGN KEY (user_id) REFERENCES characters(user_id) ON DELETE CASCADE
                )
            ''')
            
            # Локации
            await db.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    channel_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    weather TEXT,
                    smells TEXT,
                    sounds TEXT
                )
            ''')
            
            # Пути между локациями
            await db.execute('''
                CREATE TABLE IF NOT EXISTS travel_paths (
                    loc1_id INTEGER,
                    loc2_id INTEGER,
                    travel_time INTEGER,
                    PRIMARY KEY (loc1_id, loc2_id)
                )
            ''')
            
            # Атмосферные события в пути
            await db.execute('''
                CREATE TABLE IF NOT EXISTS travel_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_text TEXT NOT NULL
                )
            ''')
            
            # Настройки путешествий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS travel_settings (
                    road_channel_id INTEGER,
                    event_interval INTEGER DEFAULT 60,
                    events_enabled BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Хранилища
            await db.execute('''
                CREATE TABLE IF NOT EXISTS treasuries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    balance INTEGER DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Доступ к хранилищам
            await db.execute('''
                CREATE TABLE IF NOT EXISTS treasury_access (
                    treasury_id INTEGER,
                    role_id INTEGER,
                    can_deposit BOOLEAN DEFAULT FALSE,
                    can_withdraw BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (treasury_id, role_id),
                    FOREIGN KEY (treasury_id) REFERENCES treasuries(id) ON DELETE CASCADE
                )
            ''')
            
            # Настройки налогов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tax_settings (
                    treasury_id INTEGER PRIMARY KEY,
                    tax_rate INTEGER DEFAULT 0,
                    tax_manager_role_id INTEGER,
                    FOREIGN KEY (treasury_id) REFERENCES treasuries(id) ON DELETE CASCADE
                )
            ''')
            
            # Статистика налогов (последние 3 часа)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tax_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payer_id INTEGER,
                    amount INTEGER,
                    treasury_id INTEGER,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (payer_id) REFERENCES characters(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (treasury_id) REFERENCES treasuries(id) ON DELETE CASCADE
                )
            ''')
            
            # NPC
            await db.execute('''
                CREATE TABLE IF NOT EXISTS npcs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT CHECK(type IN ('горожанин', 'путник', 'житель')),
                    location_id INTEGER,
                    personality TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_dead BOOLEAN DEFAULT FALSE,
                    death_time TIMESTAMP,
                    respawn_time TIMESTAMP,
                    FOREIGN KEY (location_id) REFERENCES locations(channel_id) ON DELETE SET NULL
                )
            ''')
            
            # Фразы NPC
            await db.execute('''
                CREATE TABLE IF NOT EXISTS npc_phrases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_id INTEGER,
                    phrase TEXT NOT NULL,
                    FOREIGN KEY (npc_id) REFERENCES npcs(id) ON DELETE CASCADE
                )
            ''')
            
            # Расписание NPC
            await db.execute('''
                CREATE TABLE IF NOT EXISTS npc_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_id INTEGER,
                    hour INTEGER,
                    location_id INTEGER,
                    FOREIGN KEY (npc_id) REFERENCES npcs(id) ON DELETE CASCADE,
                    FOREIGN KEY (location_id) REFERENCES locations(channel_id) ON DELETE CASCADE
                )
            ''')
            
            # Репутация с NPC
            await db.execute('''
                CREATE TABLE IF NOT EXISTS npc_reputation (
                    npc_id INTEGER,
                    user_id INTEGER,
                    reputation INTEGER DEFAULT 0,
                    PRIMARY KEY (npc_id, user_id),
                    FOREIGN KEY (npc_id) REFERENCES npcs(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES characters(user_id) ON DELETE CASCADE
                )
            ''')
            
            # Канал для донесений NPC
            await db.execute('''
                CREATE TABLE IF NOT EXISTS npc_report_channel (
                    channel_id INTEGER PRIMARY KEY
                )
            ''')
            
            await db.commit()
            
            # Индексы
            await db.execute('CREATE INDEX IF NOT EXISTS idx_characters_alive ON characters(is_alive)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_characters_hunger ON characters(hunger, is_alive)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_characters_travel ON characters(travel_start, travel_end)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_bounties_active ON bounties(completed, expires_at)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_marriages_status ON marriages(status)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_npcs_location ON npcs(location_id, is_dead)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_tax_stats_time ON tax_stats(collected_at)')
    
    # ========== ПЕРСОНАЖИ ==========
    
    async def create_character(self, user_id: int, name: str, prefix: str, gender: str, biography: str) -> bool:
        """Создание нового персонажа"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                existing = await self.get_character(user_id)
                if existing:
                    return False
                
                await db.execute(
                    '''INSERT INTO characters (user_id, character_name, prefix, gender, biography)
                       VALUES (?, ?, ?, ?, ?)''',
                    (user_id, name, prefix, gender, biography)
                )
                
                await self.assign_random_family(user_id)
                await db.commit()
                return True
        except Exception as e:
            print(f"Error creating character: {e}")
            return False
    
    async def get_character(self, user_id: int) -> Optional[Dict]:
        """Получение информации о персонаже"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM characters WHERE user_id = ? AND is_alive = TRUE', 
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'user_id': row[0],
                'character_name': row[1],
                'prefix': row[2],
                'gender': row[3],
                'biography': row[4],
                'hunger': row[5],
                'balance': row[6],
                'guild_id': row[7],
                'family_id': row[8],
                'last_active': row[9],
                'death_timer_start': row[10],
                'is_alive': bool(row[11]),
                'created_at': row[12],
                'last_search': row[13],
                'active_title': row[14],
                'passport_holder_id': row[15],
                'current_location': row[16],
                'travel_start': row[17],
                'travel_end': row[18],
                'travel_destination': row[19]
            }
    
    async def get_character_by_name(self, name: str) -> Optional[Dict]:
        """Получение персонажа по имени"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM characters WHERE character_name = ? AND is_alive = TRUE',
                (name,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'user_id': row[0],
                'character_name': row[1],
                'prefix': row[2],
                'gender': row[3],
                'biography': row[4],
                'hunger': row[5],
                'balance': row[6],
                'guild_id': row[7],
                'family_id': row[8],
                'last_active': row[9],
                'death_timer_start': row[10],
                'is_alive': bool(row[11]),
                'created_at': row[12],
                'last_search': row[13],
                'active_title': row[14],
                'passport_holder_id': row[15],
                'current_location': row[16],
                'travel_start': row[17],
                'travel_end': row[18],
                'travel_destination': row[19]
            }
    
    async def update_activity(self, user_id: int):
        """Обновление времени активности"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE characters SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?',
                (user_id,)
            )
            await db.commit()
    
    async def decrease_hunger_for_active(self, amount: int = 1):
        """Уменьшение голода для активных персонажей"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''UPDATE characters 
                   SET hunger = MAX(0, hunger - ?)
                   WHERE is_alive = TRUE 
                   AND last_active > datetime('now', '-2 minutes')''',
                (amount,)
            )
            
            await db.execute(
                '''UPDATE characters 
                   SET death_timer_start = CURRENT_TIMESTAMP
                   WHERE hunger = 0 AND death_timer_start IS NULL AND is_alive = TRUE'''
            )
            
            await db.commit()
    
    async def kill_character(self, user_id: int, killer_id: int = None, keep_items: bool = False):
        """Убийство персонажа"""
        async with aiosqlite.connect(self.db_path) as db:
            if not keep_items and killer_id:
                inventory = await self.get_inventory(user_id)
                for item in inventory:
                    await self.add_item_to_inventory(killer_id, item['id'], item['quantity'])
            
            await db.execute('DELETE FROM characters WHERE user_id = ?', (user_id,))
            await db.commit()
    
    async def update_balance(self, user_id: int, amount: int):
        """Обновление баланса"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE characters SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            await db.commit()
    
    async def get_dying_characters(self) -> List[Dict]:
        """Получение умирающих персонажей"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT user_id, character_name, death_timer_start 
                   FROM characters 
                   WHERE death_timer_start IS NOT NULL AND is_alive = TRUE'''
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'user_id': r[0],
                'character_name': r[1],
                'death_timer_start': r[2]
            } for r in rows]
    
    async def start_death_timer(self, user_id: int):
        """Запуск таймера смерти"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE characters SET death_timer_start = CURRENT_TIMESTAMP WHERE user_id = ?',
                (user_id,)
            )
            await db.commit()
    
    async def reset_death_timer(self, user_id: int):
        """Сброс таймера смерти"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE characters SET death_timer_start = NULL WHERE user_id = ?',
                (user_id,)
            )
            await db.commit()
    
    # ========== ПАСПОРТ ==========
    
    async def set_passport_holder(self, passport_id: int, holder_id: int):
        """Установка владельца паспорта"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE characters SET passport_holder_id = ? WHERE user_id = ?',
                (holder_id, passport_id)
            )
            await db.commit()
    
    async def get_passport_info(self, user_id: int) -> Optional[Dict]:
        """Получение информации для паспорта"""
        character = await self.get_character(user_id)
        if not character:
            return None
        
        titles = await self.get_character_titles(user_id)
        family = await self.get_family(character['family_id']) if character['family_id'] else None
        
        return {
            'name': character['character_name'],
            'titles': [t['name'] for t in titles],
            'balance': character['balance'],
            'family': family['name'] if family else None,
            'created': character['created_at']
        }
    
    # ========== РОДЫ ==========
    
    async def create_family(self, name: str, description: str, drop_chance: int, created_by: int) -> Optional[int]:
        """Создание рода"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'INSERT INTO families (name, description, drop_chance, created_by) VALUES (?, ?, ?, ?)',
                    (name, description, drop_chance, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def get_families(self) -> List[Dict]:
        """Получение всех родов"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM families') as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'drop_chance': r[3],
                'created_by': r[4]
            } for r in rows]
    
    async def assign_random_family(self, user_id: int):
        """Назначение случайного рода персонажу"""
        families = await self.get_families()
        if not families:
            return
        
        total = sum(f['drop_chance'] for f in families)
        rand = random.randint(1, total)
        cumulative = 0
        
        for family in families:
            cumulative += family['drop_chance']
            if rand <= cumulative:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        'UPDATE characters SET family_id = ? WHERE user_id = ?',
                        (family['id'], user_id)
                    )
                    await db.commit()
                break
    
    async def get_family(self, family_id: int) -> Optional[Dict]:
        """Получение информации о роде"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM families WHERE id = ?', (family_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'drop_chance': row[3],
                'created_by': row[4]
            }
    
    # ========== ТИТУЛЫ ==========
    
    async def create_title(self, name: str, salary: int, salary_interval: int, treasury_id: int = None, 
                          condition_type: str = None, condition_value: str = None, created_by: int = None) -> Optional[int]:
        """Создание титула"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO titles (name, salary, salary_interval, treasury_id, condition_type, condition_value, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (name, salary, salary_interval, treasury_id, condition_type, condition_value, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def get_title(self, title_id: int) -> Optional[Dict]:
        """Получение титула по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM titles WHERE id = ?', (title_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'salary': row[2],
                'salary_interval': row[3],
                'treasury_id': row[4],
                'condition_type': row[5],
                'condition_value': row[6],
                'created_by': row[7]
            }
    
    async def get_title_by_name(self, name: str) -> Optional[Dict]:
        """Получение титула по названию"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM titles WHERE name = ?', (name,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'salary': row[2],
                'salary_interval': row[3],
                'treasury_id': row[4],
                'condition_type': row[5],
                'condition_value': row[6],
                'created_by': row[7]
            }
    
    async def grant_title(self, user_id: int, title_id: int, granted_by: int) -> bool:
        """Выдача титула персонажу"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''INSERT OR IGNORE INTO character_titles (character_id, title_id, granted_by)
                       VALUES (?, ?, ?)''',
                    (user_id, title_id, granted_by)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def remove_title(self, user_id: int, title_id: int) -> bool:
        """Снятие титула"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'DELETE FROM character_titles WHERE character_id = ? AND title_id = ?',
                (user_id, title_id)
            )
            await db.commit()
            return True
    
    async def get_character_titles(self, user_id: int) -> List[Dict]:
        """Получение всех титулов персонажа"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT t.id, t.name, t.salary, t.salary_interval, t.treasury_id,
                          t.condition_type, t.condition_value, ct.heir_id
                   FROM character_titles ct
                   JOIN titles t ON ct.title_id = t.id
                   WHERE ct.character_id = ?
                   ORDER BY ct.granted_at''',
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'salary': r[2],
                'salary_interval': r[3],
                'treasury_id': r[4],
                'condition_type': r[5],
                'condition_value': r[6],
                'heir_id': r[7]
            } for r in rows]
    
    async def set_active_title(self, user_id: int, title_name: str) -> bool:
        """Установка активного титула"""
        title = await self.get_title_by_name(title_name)
        if not title:
            return False
        
        titles = await self.get_character_titles(user_id)
        if not any(t['id'] == title['id'] for t in titles):
            return False
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE characters SET active_title = ? WHERE user_id = ?',
                (title_name, user_id)
            )
            await db.commit()
            return True
    
    async def set_title_heir(self, user_id: int, title_id: int, heir_id: int) -> bool:
        """Назначение наследника титула"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE character_titles SET heir_id = ? WHERE character_id = ? AND title_id = ?',
                (heir_id, user_id, title_id)
            )
            await db.commit()
            return True
    
    async def inherit_title(self, user_id: int, title_id: int) -> bool:
        """Наследование титула после смерти владельца"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'DELETE FROM character_titles WHERE character_id = ? AND title_id = ?',
                (user_id, title_id)
            )
            await db.commit()
            return True
    
    async def add_title_permission(self, role_id: int, title_id: int, granted_by: int) -> bool:
        """Добавление разрешения роли на выдачу титула"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO title_permissions (role_id, title_id, granted_by) VALUES (?, ?, ?)',
                    (role_id, title_id, granted_by)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def remove_title_permission(self, role_id: int, title_id: int) -> bool:
        """Удаление разрешения роли"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'DELETE FROM title_permissions WHERE role_id = ? AND title_id = ?',
                (role_id, title_id)
            )
            await db.commit()
            return True
    
    async def get_allowed_titles_for_role(self, role_id: int) -> List[Dict]:
        """Получение титулов, которые может выдавать роль"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT t.id, t.name
                   FROM title_permissions tp
                   JOIN titles t ON tp.title_id = t.id
                   WHERE tp.role_id = ?''',
                (role_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1]
            } for r in rows]
    
    async def check_title_conditions(self, user_id: int, title_id: int) -> bool:
        """Проверка условий титула"""
        title = await self.get_title(title_id)
        if not title or not title['condition_type']:
            return True
        
        character = await self.get_character(user_id)
        if not character:
            return False
        
        if title['condition_type'] == 'balance':
            return character['balance'] >= int(title['condition_value'])
        
        elif title['condition_type'] == 'guild':
            return character['guild_id'] is not None
        
        elif title['condition_type'] == 'item':
            items = await self.get_inventory(user_id)
            return any(i['name'] == title['condition_value'] for i in items)
        
        elif title['condition_type'] == 'housing':
            items = await self.get_inventory(user_id)
            housing = [i for i in items if i['type'] == 'жилье']
            for h in housing:
                item = await self.get_item_by_id(h['id'])
                if item and item['housing_locations']:
                    locations = item['housing_locations'].split(',')
                    if character['current_location'] in locations:
                        return True
            return False
        
        return True
    
    # ========== ПРЕДМЕТЫ ==========
    
    async def create_item(self, name: str, description: str, transferable: bool, price: int,
                         item_type: str, hunger_restore: int = 0, poison_effect: str = None,
                         craft_book_id: int = None, lottery_id: int = None,
                         housing_locations: str = None, letter_content: str = None,
                         letter_author: int = None, letter_recipient: int = None,
                         letter_sealed: bool = False, letter_encrypted: bool = False,
                         letter_key: str = None, created_by: int = None) -> Optional[int]:
        """Создание предмета"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO items (name, description, transferable, price, type, 
                                        hunger_restore, poison_effect, craft_book_id, lottery_id,
                                        housing_locations, letter_content, letter_author,
                                        letter_recipient, letter_sealed, letter_encrypted,
                                        letter_key, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (name, description, transferable, price, item_type, hunger_restore,
                     poison_effect, craft_book_id, lottery_id, housing_locations,
                     letter_content, letter_author, letter_recipient, letter_sealed,
                     letter_encrypted, letter_key, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error creating item: {e}")
            return None
    
    async def get_item_by_name(self, name: str) -> Optional[Dict]:
        """Получение предмета по имени"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM items WHERE name = ?', (name,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'transferable': bool(row[3]),
                'price': row[4],
                'type': row[5],
                'hunger_restore': row[6],
                'poison_effect': row[7],
                'craft_book_id': row[8],
                'lottery_id': row[9],
                'housing_locations': row[10],
                'letter_content': row[11],
                'letter_author': row[12],
                'letter_recipient': row[13],
                'letter_sealed': bool(row[14]),
                'letter_encrypted': bool(row[15]),
                'letter_key': row[16],
                'created_by': row[17],
                'created_at': row[18]
            }
    
    async def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Получение предмета по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM items WHERE id = ?', (item_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'transferable': bool(row[3]),
                'price': row[4],
                'type': row[5],
                'hunger_restore': row[6],
                'poison_effect': row[7],
                'craft_book_id': row[8],
                'lottery_id': row[9],
                'housing_locations': row[10],
                'letter_content': row[11],
                'letter_author': row[12],
                'letter_recipient': row[13],
                'letter_sealed': bool(row[14]),
                'letter_encrypted': bool(row[15]),
                'letter_key': row[16],
                'created_by': row[17],
                'created_at': row[18]
            }
    
    async def add_item_to_inventory(self, user_id: int, item_id: int, quantity: int = 1):
        """Добавление предмета в инвентарь"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?',
                (user_id, item_id)
            ) as cursor:
                existing = await cursor.fetchone()
            
            if existing:
                await db.execute(
                    'UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?',
                    (quantity, user_id, item_id)
                )
            else:
                await db.execute(
                    'INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)',
                    (user_id, item_id, quantity)
                )
            
            await db.commit()
    
    async def remove_item_from_inventory(self, user_id: int, item_id: int, quantity: int = 1) -> bool:
        """Удаление предмета из инвентаря"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?',
                (user_id, item_id)
            ) as cursor:
                existing = await cursor.fetchone()
            
            if not existing or existing[0] < quantity:
                return False
            
            new_quantity = existing[0] - quantity
            if new_quantity <= 0:
                await db.execute(
                    'DELETE FROM inventory WHERE user_id = ? AND item_id = ?',
                    (user_id, item_id)
                )
            else:
                await db.execute(
                    'UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ?',
                    (new_quantity, user_id, item_id)
                )
            
            await db.commit()
            return True
    
    async def get_inventory(self, user_id: int) -> List[Dict]:
        """Получение инвентаря"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT i.id, i.name, i.description, i.type, inv.quantity, 
                          i.transferable, i.hunger_restore, i.poison_effect, 
                          i.craft_book_id, i.lottery_id, i.housing_locations,
                          i.letter_content, i.letter_sealed, i.letter_encrypted
                   FROM inventory inv 
                   JOIN items i ON inv.item_id = i.id 
                   WHERE inv.user_id = ? AND inv.quantity > 0
                   ORDER BY i.name''',
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'type': r[3],
                'quantity': r[4],
                'transferable': bool(r[5]),
                'hunger_restore': r[6],
                'poison_effect': r[7],
                'craft_book_id': r[8],
                'lottery_id': r[9],
                'housing_locations': r[10],
                'letter_content': r[11],
                'letter_sealed': bool(r[12]),
                'letter_encrypted': bool(r[13])
            } for r in rows]
    
    # ========== ПИСЬМА ==========
    
    async def create_letter(self, author_id: int, recipient_id: int, content: str) -> Optional[int]:
        """Создание письма"""
        author = await self.get_character(author_id)
        if not author:
            return None
        
        letter_name = f"Письмо от {author['character_name']}"
        letter_desc = f"Письмо, написанное {author['character_name']}. Нужно прочитать."
        
        item_id = await self.create_item(
            name=letter_name,
            description=letter_desc,
            transferable=True,
            price=0,
            item_type='письмо',
            letter_content=content,
            letter_author=author_id,
            letter_recipient=recipient_id,
            created_by=author_id
        )
        
        return item_id
    
    async def send_letter(self, letter_id: int, sender_id: int, recipient_id: int) -> bool:
        """Отправка письма"""
        await self.remove_item_from_inventory(sender_id, letter_id, 1)
        await self.add_item_to_inventory(recipient_id, letter_id, 1)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE items SET letter_recipient = ? WHERE id = ?',
                (recipient_id, letter_id)
            )
            await db.commit()
        
        return True
    
    async def intercept_letter(self, letter_id: int, interceptor_id: int, original_recipient: int) -> bool:
        """Перехват письма"""
        await self.remove_item_from_inventory(original_recipient, letter_id, 1)
        await self.add_item_to_inventory(interceptor_id, letter_id, 1)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE items SET letter_recipient = ? WHERE id = ?',
                (interceptor_id, letter_id)
            )
            await db.commit()
        
        return True
    
    async def seal_letter(self, letter_id: int) -> bool:
        """Запечатывание письма"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE items SET letter_sealed = TRUE WHERE id = ?',
                (letter_id,)
            )
            await db.commit()
            return True
    
    async def unseal_letter(self, letter_id: int) -> bool:
        """Вскрытие запечатанного письма"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE items SET letter_sealed = FALSE WHERE id = ?',
                (letter_id,)
            )
            await db.commit()
            return True
    
    async def encrypt_letter(self, letter_id: int, key: str) -> bool:
        """Шифрование письма"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE items SET letter_encrypted = TRUE, letter_key = ? WHERE id = ?',
                (key, letter_id)
            )
            await db.commit()
            return True
    
    async def decrypt_letter(self, letter_id: int, key: str) -> Tuple[bool, Optional[str]]:
        """Расшифровка письма"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT letter_content, letter_key FROM items WHERE id = ?',
                (letter_id,)
            ) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return False, None
            
            content, stored_key = row
            
            if stored_key != key:
                return False, None
            
            return True, content
    
    # ========== ЖИЛЬЕ ==========
    
    async def create_housing(self, name: str, description: str, price: int, locations: List[str], created_by: int) -> Optional[int]:
        """Создание жилья"""
        locations_str = ','.join(locations)
        return await self.create_item(
            name=name,
            description=description,
            transferable=True,
            price=price,
            item_type='жилье',
            housing_locations=locations_str,
            created_by=created_by
        )
    
    async def get_housing_in_location(self, location_id: str) -> List[Dict]:
        """Получение жилья в локации"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT i.id, i.name, i.description, i.price, inv.user_id as owner_id,
                          c.character_name as owner_name
                   FROM items i
                   LEFT JOIN inventory inv ON i.id = inv.item_id AND inv.quantity > 0
                   LEFT JOIN characters c ON inv.user_id = c.user_id
                   WHERE i.type = 'жилье' AND i.housing_locations LIKE ?''',
                (f'%{location_id}%',)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'price': r[3],
                'owner_id': r[4],
                'owner_name': r[5]
            } for r in rows]
    
    # ========== МАГАЗИНЫ ==========
    
    async def create_shop(self, name: str, description: str, location: str, channel_id: int,
                         owner_id: int, created_by: int) -> Optional[int]:
        """Создание магазина"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO shops (name, description, location, channel_id, owner_id, created_by)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (name, description, location, channel_id, owner_id, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def transfer_shop(self, shop_id: int, new_owner_id: int) -> bool:
        """Передача магазина новому владельцу"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE shops SET owner_id = ? WHERE id = ?',
                    (new_owner_id, shop_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def get_shop(self, shop_id: int = None, shop_name: str = None) -> Optional[Dict]:
        """Получение информации о магазине"""
        async with aiosqlite.connect(self.db_path) as db:
            if shop_id:
                async with db.execute('SELECT * FROM shops WHERE id = ?', (shop_id,)) as cursor:
                    row = await cursor.fetchone()
            elif shop_name:
                async with db.execute('SELECT * FROM shops WHERE name = ?', (shop_name,)) as cursor:
                    row = await cursor.fetchone()
            else:
                return None
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'location': row[3],
                'channel_id': row[4],
                'owner_id': row[5],
                'created_by': row[6],
                'created_at': row[7]
            }
    
    async def get_shops_for_channel(self, channel_id: int) -> List[Dict]:
        """Получение магазинов для канала"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM shops WHERE channel_id = ?',
                (channel_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'location': r[3],
                'channel_id': r[4],
                'owner_id': r[5],
                'created_by': r[6],
                'created_at': r[7]
            } for r in rows]
    
    async def get_user_shops(self, user_id: int) -> List[Dict]:
        """Получение магазинов пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM shops WHERE owner_id = ?',
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'location': r[3],
                'channel_id': r[4],
                'owner_id': r[5],
                'created_by': r[6],
                'created_at': r[7]
            } for r in rows]
    
    async def add_item_to_shop(self, shop_id: int, item_id: int, quantity: int, price: int):
        """Добавление предмета в магазин"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''INSERT OR REPLACE INTO shop_stock (shop_id, item_id, quantity, current_price)
                   VALUES (?, ?, ?, ?)''',
                (shop_id, item_id, quantity, price)
            )
            await db.commit()
    
    async def remove_item_from_shop(self, shop_id: int, item_id: int, quantity: int = 1) -> bool:
        """Удаление предмета из магазина"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT quantity FROM shop_stock WHERE shop_id = ? AND item_id = ?',
                (shop_id, item_id)
            ) as cursor:
                existing = await cursor.fetchone()
            
            if not existing or existing[0] < quantity:
                return False
            
            new_quantity = existing[0] - quantity
            if new_quantity <= 0:
                await db.execute(
                    'DELETE FROM shop_stock WHERE shop_id = ? AND item_id = ?',
                    (shop_id, item_id)
                )
            else:
                await db.execute(
                    'UPDATE shop_stock SET quantity = ? WHERE shop_id = ? AND item_id = ?',
                    (new_quantity, shop_id, item_id)
                )
            
            await db.commit()
            return True
    
    async def get_shop_items(self, shop_id: int) -> List[Dict]:
        """Получение товаров в магазине"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT ss.item_id, i.name, i.description, ss.quantity, ss.current_price, i.type
                   FROM shop_stock ss 
                   JOIN items i ON ss.item_id = i.id 
                   WHERE ss.shop_id = ? AND ss.quantity > 0
                   ORDER BY i.name''',
                (shop_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'item_id': r[0],
                'name': r[1],
                'description': r[2],
                'quantity': r[3],
                'price': r[4],
                'type': r[5]
            } for r in rows]
    
    async def buy_from_shop(self, shop_id: int, user_id: int, item_id: int, quantity: int) -> Tuple[bool, str, int]:
        """Покупка из магазина"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('BEGIN TRANSACTION')
            
            try:
                async with db.execute(
                    'SELECT quantity, current_price FROM shop_stock WHERE shop_id = ? AND item_id = ?',
                    (shop_id, item_id)
                ) as cursor:
                    item_data = await cursor.fetchone()
                
                if not item_data or item_data[0] < quantity:
                    await db.execute('ROLLBACK')
                    return False, "Недостаточно товара", 0
                
                async with db.execute(
                    'SELECT balance FROM characters WHERE user_id = ?',
                    (user_id,)
                ) as cursor:
                    balance_data = await cursor.fetchone()
                
                if not balance_data:
                    await db.execute('ROLLBACK')
                    return False, "Персонаж не найден", 0
                
                total_cost = item_data[1] * quantity
                
                # Проверяем налоги
                tax_settings = await self.get_tax_settings()
                if tax_settings:
                    tax_amount = int(total_cost * tax_settings['tax_rate'] / 100)
                    final_cost = total_cost
                    
                    if balance_data[0] < total_cost:
                        await db.execute('ROLLBACK')
                        return False, f"Недостаточно денег. Нужно: {total_cost}", 0
                    
                    # Списание денег (налог идет в хранилище)
                    await db.execute(
                        'UPDATE characters SET balance = balance - ? WHERE user_id = ?',
                        (total_cost, user_id)
                    )
                    
                    if tax_amount > 0 and tax_settings['treasury_id']:
                        await db.execute(
                            'UPDATE treasuries SET balance = balance + ? WHERE id = ?',
                            (tax_amount, tax_settings['treasury_id'])
                        )
                        
                        await db.execute(
                            '''INSERT INTO tax_stats (payer_id, amount, treasury_id)
                               VALUES (?, ?, ?)''',
                            (user_id, tax_amount, tax_settings['treasury_id'])
                        )
                else:
                    if balance_data[0] < total_cost:
                        await db.execute('ROLLBACK')
                        return False, f"Недостаточно денег. Нужно: {total_cost}", 0
                    
                    await db.execute(
                        'UPDATE characters SET balance = balance - ? WHERE user_id = ?',
                        (total_cost, user_id)
                    )
                
                new_quantity = item_data[0] - quantity
                if new_quantity <= 0:
                    await db.execute(
                        'DELETE FROM shop_stock WHERE shop_id = ? AND item_id = ?',
                        (shop_id, item_id)
                    )
                else:
                    await db.execute(
                        'UPDATE shop_stock SET quantity = ? WHERE shop_id = ? AND item_id = ?',
                        (new_quantity, shop_id, item_id)
                    )
                
                await self.add_item_to_inventory(user_id, item_id, quantity)
                
                await db.execute('COMMIT')
                return True, f"Куплено {quantity} шт. за {total_cost} {CURRENCY_PLURAL}", total_cost
                
            except Exception as e:
                await db.execute('ROLLBACK')
                print(f"Error buying from shop: {e}")
                return False, "Ошибка при покупке", 0
    
    # ========== КРАФТ ==========
    
    async def create_craft(self, name: str, description: str, result_item_id: int,
                          material_item_id: int, required_quantity: int, result_quantity: int,
                          craft_price: int, book_name: str, created_by: int) -> Optional[int]:
        """Создание рецепта крафта"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO crafts (name, description, result_item_id, material_item_id,
                                          required_quantity, result_quantity, craft_price, book_name, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (name, description, result_item_id, material_item_id, required_quantity,
                     result_quantity, craft_price, book_name, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def create_craft_book(self, name: str, description: str, created_by: int) -> Optional[int]:
        """Создание книги крафта"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'INSERT INTO craft_books (name, description, created_by) VALUES (?, ?, ?)',
                    (name, description, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def get_craft_book(self, book_id: int) -> Optional[Dict]:
        """Получение книги крафта"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM craft_books WHERE id = ?', (book_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'created_by': row[3]
            }
    
    async def get_crafts_by_book(self, book_name: str) -> List[Dict]:
        """Получение крафтов по книге"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT c.*, ri.name as result_name, mi.name as material_name
                   FROM crafts c
                   JOIN items ri ON c.result_item_id = ri.id
                   JOIN items mi ON c.material_item_id = mi.id
                   WHERE c.book_name = ?''',
                (book_name,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'result_item_id': r[3],
                'material_item_id': r[4],
                'required_quantity': r[5],
                'result_quantity': r[6],
                'craft_price': r[7],
                'book_name': r[8],
                'created_by': r[9],
                'created_at': r[10],
                'result_name': r[11],
                'material_name': r[12]
            } for r in rows]
    
    async def get_base_crafts(self) -> List[Dict]:
        """Получение базовых крафтов"""
        return await self.get_crafts_by_book('базовый')
    
    async def learn_craft(self, user_id: int, craft_id: int) -> bool:
        """Изучение крафта"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO learned_crafts (user_id, craft_id) VALUES (?, ?)',
                    (user_id, craft_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def get_learned_crafts(self, user_id: int) -> List[Dict]:
        """Получение изученных крафтов"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT c.*, ri.name as result_name, mi.name as material_name
                   FROM learned_crafts lc
                   JOIN crafts c ON lc.craft_id = c.id
                   JOIN items ri ON c.result_item_id = ri.id
                   JOIN items mi ON c.material_item_id = mi.id
                   WHERE lc.user_id = ?''',
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'description': r[2],
                'result_item_id': r[3],
                'material_item_id': r[4],
                'required_quantity': r[5],
                'result_quantity': r[6],
                'craft_price': r[7],
                'book_name': r[8],
                'created_by': r[9],
                'created_at': r[10],
                'result_name': r[11],
                'material_name': r[12]
            } for r in rows]
    
    async def get_crafts_for_material(self, user_id: int, material_item_id: int) -> List[Dict]:
        """Получение доступных крафтов для материала"""
        learned = await self.get_learned_crafts(user_id)
        return [c for c in learned if c['material_item_id'] == material_item_id]
    
    async def perform_craft(self, user_id: int, craft_id: int) -> Tuple[bool, str]:
        """Выполнение крафта"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('BEGIN TRANSACTION')
            
            try:
                async with db.execute(
                    '''SELECT c.*, ri.name as result_name, mi.name as material_name
                       FROM crafts c
                       JOIN items ri ON c.result_item_id = ri.id
                       JOIN items mi ON c.material_item_id = mi.id
                       WHERE c.id = ?''',
                    (craft_id,)
                ) as cursor:
                    craft_data = await cursor.fetchone()
                
                if not craft_data:
                    await db.execute('ROLLBACK')
                    return False, "Крафт не найден"
                
                craft = {
                    'id': craft_data[0],
                    'result_item_id': craft_data[3],
                    'material_item_id': craft_data[4],
                    'required_quantity': craft_data[5],
                    'result_quantity': craft_data[6],
                    'craft_price': craft_data[7],
                    'result_name': craft_data[11],
                    'material_name': craft_data[12]
                }
                
                async with db.execute(
                    'SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?',
                    (user_id, craft['material_item_id'])
                ) as cursor:
                    material_qty = await cursor.fetchone()
                
                if not material_qty or material_qty[0] < craft['required_quantity']:
                    await db.execute('ROLLBACK')
                    return False, f"Недостаточно {craft['material_name']}"
                
                async with db.execute(
                    'SELECT balance FROM characters WHERE user_id = ?',
                    (user_id,)
                ) as cursor:
                    balance = await cursor.fetchone()
                
                if not balance or balance[0] < craft['craft_price']:
                    await db.execute('ROLLBACK')
                    return False, f"Недостаточно денег. Нужно: {craft['craft_price']}"
                
                if random.random() < CRAFT_FAIL_CHANCE:
                    await self.remove_item_from_inventory(user_id, craft['material_item_id'], craft['required_quantity'])
                    
                    await db.execute(
                        'UPDATE characters SET balance = balance - ? WHERE user_id = ?',
                        (craft['craft_price'], user_id)
                    )
                    
                    await db.execute('COMMIT')
                    return False, f"Крафт не удался! {craft['required_quantity']} {craft['material_name']} потеряны."
                
                await self.remove_item_from_inventory(user_id, craft['material_item_id'], craft['required_quantity'])
                await self.add_item_to_inventory(user_id, craft['result_item_id'], craft['result_quantity'])
                
                if craft['craft_price'] > 0:
                    await db.execute(
                        'UPDATE characters SET balance = balance - ? WHERE user_id = ?',
                        (craft['craft_price'], user_id)
                    )
                
                await db.execute('COMMIT')
                return True, f"Успешно скрафчено {craft['result_quantity']} x {craft['result_name']}"
                
            except Exception as e:
                await db.execute('ROLLBACK')
                print(f"Error in craft: {e}")
                return False, "Ошибка при крафте"
    
    async def learn_crafts_from_book(self, user_id: int, book_name: str) -> List[Dict]:
        """Изучение всех крафтов из книги"""
        crafts = await self.get_crafts_by_book(book_name)
        learned = []
        
        for craft in crafts:
            if await self.learn_craft(user_id, craft['id']):
                learned.append(craft)
        
        return learned
    
    # ========== СВИТКИ ==========
    
    async def create_scroll(self, name: str, content: str, is_ancient: bool, created_by: int) -> Optional[int]:
        """Создание свитка"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'INSERT INTO scrolls (name, content, is_ancient, created_by) VALUES (?, ?, ?, ?)',
                    (name, content, is_ancient, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def get_scroll(self, name: str) -> Optional[Dict]:
        """Получение свитка"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM scrolls WHERE name = ?', (name,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'content': row[2],
                'is_ancient': bool(row[3]),
                'created_by': row[4],
                'created_at': row[5]
            }
    
    # ========== ЛОТЕРЕИ ==========
    
    async def create_lottery(self, name: str, description: str, price: int,
                            prizes_json: str, win_chance: float,
                            total_tickets: int, created_by: int) -> Optional[int]:
        """Создание лотереи"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO lotteries (name, description, price,
                                            prizes_json, win_chance, total_tickets, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (name, description, price, prizes_json, win_chance, total_tickets, created_by)
                )
                
                lottery_id = cursor.lastrowid
                
                ticket_name = f"Билет {name}"
                await self.create_item(
                    ticket_name,
                    f"Билет лотереи {name}",
                    True,
                    price,
                    'лотерея',
                    lottery_id=lottery_id,
                    created_by=created_by
                )
                
                await db.execute(
                    'UPDATE lotteries SET ticket_item_id = ? WHERE id = ?',
                    (cursor.lastrowid, lottery_id)
                )
                
                await db.commit()
                return lottery_id
        except Exception as e:
            print(f"Error creating lottery: {e}")
            return None
    
    async def get_lottery(self, lottery_id: int) -> Optional[Dict]:
        """Получение лотереи"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM lotteries WHERE id = ?', (lottery_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'ticket_item_id': row[3],
                'price': row[4],
                'prizes_json': row[5],
                'win_chance': row[6],
                'total_tickets': row[7],
                'sold_tickets': row[8],
                'created_by': row[9],
                'created_at': row[10],
                'is_active': bool(row[11])
            }
    
    async def use_lottery_ticket(self, user_id: int, lottery_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """Использование лотерейного билета"""
        lottery = await self.get_lottery(lottery_id)
        if not lottery or not lottery['is_active']:
            return False, "Лотерея не активна", None
        
        if lottery['total_tickets'] > 0 and lottery['sold_tickets'] >= lottery['total_tickets']:
            return False, "Все билеты проданы", None
        
        if random.random() < lottery['win_chance']:
            prizes = json.loads(lottery['prizes_json'])
            if prizes:
                prize = random.choice(prizes)
                
                if prize['type'] == 'money':
                    amount = int(prize['value'])
                    await self.update_balance(user_id, amount)
                    return True, f"Вы выиграли {amount} {CURRENCY_PLURAL}!", prize
                elif prize['type'] == 'item':
                    item = await self.get_item_by_name(prize['value'])
                    if item:
                        await self.add_item_to_inventory(user_id, item['id'], 1)
                        return True, f"Вы выиграли предмет: {item['name']}!", prize
                elif prize['type'] == 'title':
                    title = await self.get_title_by_name(prize['value'])
                    if title:
                        await self.grant_title(user_id, title['id'], lottery['created_by'])
                        return True, f"Вы получили титул: {title['name']}!", prize
            
            return True, "Вы что-то выиграли, но приз не найден!", None
        else:
            return False, "К сожалению, вы ничего не выиграли", None
    
    # ========== ГИЛЬДИИ ==========
    
    async def create_guild(self, name: str, description: str, leader_id: int) -> Optional[int]:
        """Создание гильдии"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'INSERT INTO guilds (name, description, leader_id) VALUES (?, ?, ?)',
                    (name, description, leader_id)
                )
                guild_id = cursor.lastrowid
                
                await db.execute(
                    'INSERT INTO guild_members (guild_id, user_id, role) VALUES (?, ?, ?)',
                    (guild_id, leader_id, 'leader')
                )
                
                await db.execute(
                    'UPDATE characters SET guild_id = ? WHERE user_id = ?',
                    (guild_id, leader_id)
                )
                
                await db.commit()
                return guild_id
        except:
            return None
    
    async def get_guild(self, guild_id: int = None, guild_name: str = None) -> Optional[Dict]:
        """Получение информации о гильдии"""
        async with aiosqlite.connect(self.db_path) as db:
            if guild_id:
                async with db.execute('SELECT * FROM guilds WHERE id = ?', (guild_id,)) as cursor:
                    row = await cursor.fetchone()
            elif guild_name:
                async with db.execute('SELECT * FROM guilds WHERE name = ?', (guild_name,)) as cursor:
                    row = await cursor.fetchone()
            else:
                return None
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'leader_id': row[3],
                'bank_balance': row[4],
                'created_at': row[5]
            }
    
    async def get_guild_members(self, guild_id: int) -> List[Dict]:
        """Получение участников гильдии"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT c.user_id, c.character_name, gm.role, gm.joined_at 
                   FROM guild_members gm 
                   JOIN characters c ON gm.user_id = c.user_id 
                   WHERE gm.guild_id = ? AND c.is_alive = TRUE
                   ORDER BY 
                       CASE gm.role 
                           WHEN 'leader' THEN 1
                           WHEN 'officer' THEN 2
                           ELSE 3 
                       END, gm.joined_at''',
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'user_id': r[0],
                'character_name': r[1],
                'role': r[2],
                'joined_at': r[3]
            } for r in rows]
    
    async def join_guild(self, guild_id: int, user_id: int) -> bool:
        """Вступление в гильдию"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO guild_members (guild_id, user_id) VALUES (?, ?)',
                    (guild_id, user_id)
                )
                
                await db.execute(
                    'UPDATE characters SET guild_id = ? WHERE user_id = ?',
                    (guild_id, user_id)
                )
                
                await db.commit()
                return True
        except:
            return False
    
    async def leave_guild(self, user_id: int) -> bool:
        """Выход из гильдии"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                character = await self.get_character(user_id)
                if not character or not character['guild_id']:
                    return False
                
                guild_id = character['guild_id']
                
                guild = await self.get_guild(guild_id=guild_id)
                if guild and guild['leader_id'] == user_id:
                    return False
                
                await db.execute(
                    'DELETE FROM guild_members WHERE guild_id = ? AND user_id = ?',
                    (guild_id, user_id)
                )
                
                await db.execute(
                    'UPDATE characters SET guild_id = NULL WHERE user_id = ?',
                    (user_id,)
                )
                
                await db.commit()
                return True
        except:
            return False
    
    async def deposit_to_guild_bank(self, guild_id: int, user_id: int, item_id: int, quantity: int) -> bool:
        """Внесение предметов в банк гильдии"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT id, quantity FROM guild_bank WHERE guild_id = ? AND item_id = ?',
                    (guild_id, item_id)
                ) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    await db.execute(
                        'UPDATE guild_bank SET quantity = quantity + ?, deposited_by = ? WHERE id = ?',
                        (quantity, user_id, existing[0])
                    )
                else:
                    await db.execute(
                        '''INSERT INTO guild_bank (guild_id, item_id, quantity, deposited_by) 
                           VALUES (?, ?, ?, ?)''',
                        (guild_id, item_id, quantity, user_id)
                    )
                
                await db.commit()
                return True
        except:
            return False
    
    async def withdraw_from_guild_bank(self, guild_id: int, user_id: int, item_id: int, quantity: int) -> bool:
        """Снятие предметов из банка гильдии"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT id, quantity FROM guild_bank WHERE guild_id = ? AND item_id = ?',
                    (guild_id, item_id)
                ) as cursor:
                    item = await cursor.fetchone()
                
                if not item or item[1] < quantity:
                    return False
                
                tax = int(quantity * GUILD_BANK_TAX)
                actual_quantity = quantity - tax
                
                if actual_quantity < 1:
                    actual_quantity = 1
                
                new_quantity = item[1] - quantity
                if new_quantity <= 0:
                    await db.execute(
                        'DELETE FROM guild_bank WHERE id = ?',
                        (item[0],)
                    )
                else:
                    await db.execute(
                        'UPDATE guild_bank SET quantity = ? WHERE id = ?',
                        (new_quantity, item[0])
                    )
                
                await db.commit()
                
                await self.add_item_to_inventory(user_id, item_id, actual_quantity)
                return True
        except:
            return False
    
    async def get_guild_bank(self, guild_id: int) -> List[Dict]:
        """Получение содержимого банка гильдии"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT gb.item_id, gb.quantity, i.name, i.description, i.type
                   FROM guild_bank gb 
                   JOIN items i ON gb.item_id = i.id 
                   WHERE gb.guild_id = ? AND gb.quantity > 0
                   ORDER BY i.name''',
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'item_id': r[0],
                'quantity': r[1],
                'name': r[2],
                'description': r[3],
                'type': r[4]
            } for r in rows]
    
    async def update_guild_bank_balance(self, guild_id: int, amount: int):
        """Обновление баланса банка гильдии"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE guilds SET bank_balance = bank_balance + ? WHERE id = ?',
                (amount, guild_id)
            )
            await db.commit()
    
    # ========== ОХОТА ЗА ГОЛОВАМИ ==========
    
    async def create_bounty(self, target_id: int, reward: int, reason: str, created_by: int,
                           channel_id: int) -> Optional[int]:
        """Создание заказа на охоту"""
        try:
            expires_at = datetime.now() + timedelta(days=BOUNTY_COMPLETION_DAYS)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO bounties (target_id, reward, reason, created_by, expires_at, channel_id)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (target_id, reward, reason, created_by, expires_at.isoformat(), channel_id)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def take_bounty(self, bounty_id: int, hunter_id: int) -> bool:
        """Взяться за заказ"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE bounties SET hunter_id = ? WHERE id = ? AND hunter_id IS NULL',
                    (hunter_id, bounty_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def complete_bounty(self, bounty_id: int, hunter_id: int) -> bool:
        """Завершение заказа"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('BEGIN TRANSACTION')
            
            try:
                async with db.execute(
                    'SELECT reward FROM bounties WHERE id = ? AND hunter_id = ?',
                    (bounty_id, hunter_id)
                ) as cursor:
                    bounty = await cursor.fetchone()
                
                if not bounty:
                    await db.execute('ROLLBACK')
                    return False
                
                await db.execute(
                    'UPDATE characters SET balance = balance + ? WHERE user_id = ?',
                    (bounty[0], hunter_id)
                )
                
                await db.execute(
                    '''UPDATE bounties SET completed = TRUE, completed_at = CURRENT_TIMESTAMP
                       WHERE id = ?''',
                    (bounty_id,)
                )
                
                await db.execute('COMMIT')
                return True
                
            except Exception as e:
                await db.execute('ROLLBACK')
                print(f"Error completing bounty: {e}")
                return False
    
    async def get_active_bounties(self, channel_id: int) -> List[Dict]:
        """Получение активных заказов в канале"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT b.*, tc.character_name as target_name, tc.user_id as target_user_id,
                          hc.character_name as hunter_name
                   FROM bounties b
                   JOIN characters tc ON b.target_id = tc.user_id
                   LEFT JOIN characters hc ON b.hunter_id = hc.user_id
                   WHERE b.channel_id = ? AND b.completed = FALSE 
                         AND b.expires_at > datetime('now')''',
                (channel_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'target_id': r[1],
                'reward': r[2],
                'reason': r[3],
                'created_by': r[4],
                'created_at': r[5],
                'hunter_id': r[6],
                'expires_at': r[7],
                'completed': bool(r[8]),
                'completed_at': r[9],
                'channel_id': r[10],
                'target_name': r[11],
                'target_user_id': r[12],
                'hunter_name': r[13]
            } for r in rows]
    
    async def add_bounty_channel(self, channel_id: int) -> bool:
        """Добавление канала для охоты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO bounty_channels (channel_id) VALUES (?)',
                    (channel_id,)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def is_bounty_channel(self, channel_id: int) -> bool:
        """Проверка, является ли канал каналом для охоты"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT 1 FROM bounty_channels WHERE channel_id = ?',
                (channel_id,)
            ) as cursor:
                return await cursor.fetchone() is not None
    
    # ========== БРАКИ ==========
    
    async def propose_marriage(self, proposer_id: int, target_id: int) -> Optional[int]:
        """Предложение брака"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                existing = await self.get_active_marriage(proposer_id)
                if existing:
                    return None
                
                existing = await self.get_active_marriage(target_id)
                if existing:
                    return None
                
                cursor = await db.execute(
                    '''INSERT INTO marriages (spouse1_id, spouse2_id, status)
                       VALUES (?, ?, 'pending')''',
                    (proposer_id, target_id)
                )
                
                marriage_id = cursor.lastrowid
                await db.execute(
                    'INSERT INTO family_bank (marriage_id, balance) VALUES (?, 0)',
                    (marriage_id,)
                )
                
                await db.commit()
                return marriage_id
        except:
            return None
    
    async def accept_marriage(self, marriage_id: int) -> bool:
        """Принятие предложения"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''UPDATE marriages 
                       SET status = 'accepted', accepted_at = CURRENT_TIMESTAMP
                       WHERE id = ? AND status = 'pending'''',
                    (marriage_id,)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def marry(self, marriage_id: int) -> bool:
        """Заключение брака"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''UPDATE marriages 
                       SET status = 'married', married_at = CURRENT_TIMESTAMP
                       WHERE id = ? AND status = 'accepted'''',
                    (marriage_id,)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def divorce(self, marriage_id: int) -> bool:
        """Развод"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT * FROM marriages WHERE id = ?',
                    (marriage_id,)
                ) as cursor:
                    marriage = await cursor.fetchone()
                
                if not marriage:
                    return False
                
                async with db.execute(
                    'SELECT balance FROM family_bank WHERE marriage_id = ?',
                    (marriage_id,)
                ) as cursor:
                    bank = await cursor.fetchone()
                
                if bank and bank[0] > 0:
                    half = bank[0] // 2
                    await db.execute(
                        'UPDATE characters SET balance = balance + ? WHERE user_id = ?',
                        (half, marriage[1])
                    )
                    await db.execute(
                        'UPDATE characters SET balance = balance + ? WHERE user_id = ?',
                        (half, marriage[2])
                    )
                
                await db.execute('DELETE FROM marriages WHERE id = ?', (marriage_id,))
                await db.commit()
                return True
        except:
            return False
    
    async def get_active_marriage(self, user_id: int) -> Optional[Dict]:
        """Получение активного брака персонажа"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT * FROM marriages 
                   WHERE (spouse1_id = ? OR spouse2_id = ?) 
                   AND status IN ('pending', 'accepted', 'married')''',
                (user_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'spouse1_id': row[1],
                'spouse2_id': row[2],
                'proposed_at': row[3],
                'accepted_at': row[4],
                'married_at': row[5],
                'status': row[6]
            }
    
    async def get_marriage_bank(self, marriage_id: int) -> int:
        """Получение баланса семейного банка"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT balance FROM family_bank WHERE marriage_id = ?',
                (marriage_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def add_to_marriage_bank(self, marriage_id: int, amount: int) -> bool:
        """Добавление в семейный банк"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE family_bank SET balance = balance + ? WHERE marriage_id = ?',
                    (amount, marriage_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def remove_from_marriage_bank(self, marriage_id: int, amount: int) -> bool:
        """Снятие из семейного банка"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT balance FROM family_bank WHERE marriage_id = ?',
                    (marriage_id,)
                ) as cursor:
                    balance = await cursor.fetchone()
                
                if not balance or balance[0] < amount:
                    return False
                
                await db.execute(
                    'UPDATE family_bank SET balance = balance - ? WHERE marriage_id = ?',
                    (amount, marriage_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    # ========== ДУЭЛИ ==========
    
    async def create_duel(self, challenger_id: int, opponent_id: int, stake: int, channel_id: int) -> Optional[int]:
        """Создание дуэли"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO duels (challenger_id, opponent_id, stake, channel_id, status)
                       VALUES (?, ?, ?, ?, 'pending')''',
                    (challenger_id, opponent_id, stake, channel_id)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def accept_duel(self, duel_id: int) -> bool:
        """Принятие дуэли"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''UPDATE duels SET status = 'accepted' 
                       WHERE id = ? AND status = 'pending'''',
                    (duel_id,)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def add_witness(self, duel_id: int, user_id: int) -> bool:
        """Добавление свидетеля"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR IGNORE INTO duel_witnesses (duel_id, user_id) VALUES (?, ?)',
                    (duel_id, user_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def complete_duel(self, duel_id: int, winner_id: int) -> bool:
        """Завершение дуэли"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('BEGIN TRANSACTION')
            
            try:
                async with db.execute(
                    'SELECT * FROM duels WHERE id = ? AND status = ?',
                    (duel_id, 'accepted')
                ) as cursor:
                    duel = await cursor.fetchone()
                
                if not duel:
                    await db.execute('ROLLBACK')
                    return False
                
                loser_id = duel[2] if winner_id == duel[1] else duel[1]
                
                if duel[3] > 0:
                    await db.execute(
                        'UPDATE characters SET balance = balance + ? WHERE user_id = ?',
                        (duel[3], winner_id)
                    )
                    await db.execute(
                        'UPDATE characters SET balance = balance - ? WHERE user_id = ?',
                        (duel[3], loser_id)
                    )
                
                await self.kill_character(loser_id, winner_id)
                
                await db.execute(
                    '''UPDATE duels SET status = 'completed', winner_id = ?, completed_at = CURRENT_TIMESTAMP
                       WHERE id = ?''',
                    (winner_id, duel_id)
                )
                
                await db.execute('COMMIT')
                return True
                
            except Exception as e:
                await db.execute('ROLLBACK')
                print(f"Error completing duel: {e}")
                return False
    
    # ========== ПУТЕШЕСТВИЯ ==========
    
    async def add_location(self, channel_id: int, name: str, description: str = "") -> bool:
        """Добавление локации"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR REPLACE INTO locations (channel_id, name, description) VALUES (?, ?, ?)',
                    (channel_id, name, description)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def remove_location(self, channel_id: int) -> bool:
        """Удаление локации"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM locations WHERE channel_id = ?', (channel_id,))
                await db.commit()
                return True
        except:
            return False
    
    async def get_location(self, channel_id: int) -> Optional[Dict]:
        """Получение информации о локации"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM locations WHERE channel_id = ?', (channel_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'channel_id': row[0],
                'name': row[1],
                'description': row[2],
                'weather': row[3],
                'smells': row[4],
                'sounds': row[5]
            }
    
    async def add_travel_path(self, loc1_id: int, loc2_id: int, travel_time: int) -> bool:
        """Добавление пути между локациями"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT OR REPLACE INTO travel_paths (loc1_id, loc2_id, travel_time) VALUES (?, ?, ?)',
                    (loc1_id, loc2_id, travel_time)
                )
                await db.execute(
                    'INSERT OR REPLACE INTO travel_paths (loc1_id, loc2_id, travel_time) VALUES (?, ?, ?)',
                    (loc2_id, loc1_id, travel_time)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def get_travel_time(self, from_loc: int, to_loc: int) -> Optional[int]:
        """Получение времени пути между локациями"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT travel_time FROM travel_paths WHERE loc1_id = ? AND loc2_id = ?',
                (from_loc, to_loc)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def get_available_destinations(self, from_loc: int) -> List[Dict]:
        """Получение доступных направлений из локации"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT tp.loc2_id, l.name, tp.travel_time
                   FROM travel_paths tp
                   JOIN locations l ON tp.loc2_id = l.channel_id
                   WHERE tp.loc1_id = ?''',
                (from_loc,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'channel_id': r[0],
                'name': r[1],
                'time': r[2]
            } for r in rows]
    
    async def start_travel(self, user_id: int, destination: int, travel_time: int):
        """Начало путешествия"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now()
            end = now + timedelta(minutes=travel_time)
            
            await db.execute(
                '''UPDATE characters 
                   SET travel_start = ?, travel_end = ?, travel_destination = ?
                   WHERE user_id = ?''',
                (now.isoformat(), end.isoformat(), destination, user_id)
            )
            await db.commit()
    
    async def finish_travel(self, user_id: int):
        """Завершение путешествия"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT travel_destination FROM characters WHERE user_id = ?',
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                destination = row[0] if row else None
            
            await db.execute(
                '''UPDATE characters 
                   SET current_location = ?, travel_start = NULL, travel_end = NULL, travel_destination = NULL
                   WHERE user_id = ?''',
                (destination, user_id)
            )
            await db.commit()
            return destination
    
    async def get_travelers_on_road(self) -> List[Dict]:
        """Получение всех путешественников"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT user_id, character_name, travel_start, travel_end, travel_destination
                   FROM characters
                   WHERE travel_start IS NOT NULL AND travel_end IS NOT NULL AND is_alive = TRUE'''
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'user_id': r[0],
                'name': r[1],
                'start': r[2],
                'end': r[3],
                'destination': r[4]
            } for r in rows]
    
    async def add_travel_event(self, event_text: str) -> bool:
        """Добавление атмосферного события"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO travel_events (event_text) VALUES (?)',
                    (event_text,)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def get_random_travel_event(self) -> Optional[str]:
        """Получение случайного атмосферного события"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT event_text FROM travel_events') as cursor:
                rows = await cursor.fetchall()
            
            if not rows:
                return None
            
            return random.choice(rows)[0]
    
    async def set_road_channel(self, channel_id: int):
        """Установка канала дороги"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO travel_settings (road_channel_id) VALUES (?)',
                (channel_id,)
            )
            await db.commit()
    
    async def get_road_channel(self) -> Optional[int]:
        """Получение канала дороги"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT road_channel_id FROM travel_settings') as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def set_event_interval(self, interval: int):
        """Установка интервала событий"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE travel_settings SET event_interval = ?',
                (interval,)
            )
            await db.commit()
    
    async def get_event_interval(self) -> int:
        """Получение интервала событий"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT event_interval FROM travel_settings') as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 60
    
    async def set_events_enabled(self, enabled: bool):
        """Включение/выключение событий"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE travel_settings SET events_enabled = ?',
                (enabled,)
            )
            await db.commit()
    
    async def get_events_enabled(self) -> bool:
        """Получение статуса событий"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT events_enabled FROM travel_settings') as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else True
    
    # ========== ХРАНИЛИЩА ==========
    
    async def create_treasury(self, name: str, description: str, created_by: int) -> Optional[int]:
        """Создание хранилища"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'INSERT INTO treasuries (name, description, created_by) VALUES (?, ?, ?)',
                    (name, description, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def get_treasury(self, treasury_id: int) -> Optional[Dict]:
        """Получение информации о хранилище"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM treasuries WHERE id = ?', (treasury_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'balance': row[3],
                'created_by': row[4],
                'created_at': row[5]
            }
    
    async def get_treasury_by_name(self, name: str) -> Optional[Dict]:
        """Получение хранилища по названию"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM treasuries WHERE name = ?', (name,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'balance': row[3],
                'created_by': row[4],
                'created_at': row[5]
            }
    
    async def add_treasury_access(self, treasury_id: int, role_id: int, can_deposit: bool, can_withdraw: bool) -> bool:
        """Добавление доступа к хранилищу для роли"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''INSERT OR REPLACE INTO treasury_access (treasury_id, role_id, can_deposit, can_withdraw)
                       VALUES (?, ?, ?, ?)''',
                    (treasury_id, role_id, can_deposit, can_withdraw)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def check_treasury_access(self, treasury_id: int, user_id: int, action: str) -> bool:
        """Проверка доступа пользователя к хранилищу"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT ta.can_deposit, ta.can_withdraw, u.roles
                   FROM treasury_access ta
                   WHERE ta.treasury_id = ?''',
                (treasury_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            if not rows:
                return False
            
            # Здесь должна быть проверка ролей пользователя
            # Упрощенно: возвращаем True если есть хоть какое-то право
            for row in rows:
                if action == 'deposit' and row[0]:
                    return True
                if action == 'withdraw' and row[1]:
                    return True
            
            return False
    
    async def deposit_to_treasury(self, treasury_id: int, user_id: int, amount: int) -> bool:
        """Внесение денег в хранилище"""
        if not await self.check_treasury_access(treasury_id, user_id, 'deposit'):
            return False
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE treasuries SET balance = balance + ? WHERE id = ?',
                (amount, treasury_id)
            )
            await db.commit()
            return True
    
    async def withdraw_from_treasury(self, treasury_id: int, user_id: int, amount: int) -> bool:
        """Снятие денег из хранилища"""
        if not await self.check_treasury_access(treasury_id, user_id, 'withdraw'):
            return False
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT balance FROM treasuries WHERE id = ?',
                (treasury_id,)
            ) as cursor:
                balance = await cursor.fetchone()
            
            if not balance or balance[0] < amount:
                return False
            
            await db.execute(
                'UPDATE treasuries SET balance = balance - ? WHERE id = ?',
                (amount, treasury_id)
            )
            await db.commit()
            return True
    
    # ========== НАЛОГИ ==========
    
    async def set_tax_settings(self, treasury_id: int, tax_rate: int, manager_role_id: int) -> bool:
        """Настройка налогов"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''INSERT OR REPLACE INTO tax_settings (treasury_id, tax_rate, tax_manager_role_id)
                       VALUES (?, ?, ?)''',
                    (treasury_id, tax_rate, manager_role_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def get_tax_settings(self) -> Optional[Dict]:
        """Получение настроек налогов"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM tax_settings') as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'treasury_id': row[0],
                'tax_rate': row[1],
                'tax_manager_role_id': row[2]
            }
    
    async def get_tax_stats(self) -> List[Dict]:
        """Получение статистики налогов за последние 3 часа"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                '''SELECT ts.payer_id, c.character_name, ts.amount, ts.treasury_id, t.name
                   FROM tax_stats ts
                   JOIN characters c ON ts.payer_id = c.user_id
                   JOIN treasuries t ON ts.treasury_id = t.id
                   WHERE ts.collected_at > datetime('now', '-3 hours')
                   ORDER BY ts.collected_at DESC''',
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'payer_id': r[0],
                'payer_name': r[1],
                'amount': r[2],
                'treasury_id': r[3],
                'treasury_name': r[4]
            } for r in rows]
    
    # ========== NPC ==========
    
    async def create_npc(self, name: str, npc_type: str, location_id: int, personality: str, created_by: int) -> Optional[int]:
        """Создание NPC"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    '''INSERT INTO npcs (name, type, location_id, personality, created_by)
                       VALUES (?, ?, ?, ?, ?)''',
                    (name, npc_type, location_id, personality, created_by)
                )
                await db.commit()
                return cursor.lastrowid
        except:
            return None
    
    async def get_npc(self, npc_id: int) -> Optional[Dict]:
        """Получение информации о NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM npcs WHERE id = ?', (npc_id,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'location_id': row[3],
                'personality': row[4],
                'created_by': row[5],
                'created_at': row[6],
                'is_dead': bool(row[7]),
                'death_time': row[8],
                'respawn_time': row[9]
            }
    
    async def get_npc_by_name(self, name: str) -> Optional[Dict]:
        """Получение NPC по имени"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM npcs WHERE name = ?', (name,)) as cursor:
                row = await cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'location_id': row[3],
                'personality': row[4],
                'created_by': row[5],
                'created_at': row[6],
                'is_dead': bool(row[7]),
                'death_time': row[8],
                'respawn_time': row[9]
            }
    
    async def get_npcs_in_location(self, location_id: int, exclude_dead: bool = True) -> List[Dict]:
        """Получение NPC в локации"""
        async with aiosqlite.connect(self.db_path) as db:
            query = 'SELECT * FROM npcs WHERE location_id = ?'
            params = [location_id]
            
            if exclude_dead:
                query += ' AND (is_dead = FALSE OR respawn_time > datetime("now"))'
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
            
            return [{
                'id': r[0],
                'name': r[1],
                'type': r[2],
                'location_id': r[3],
                'personality': r[4],
                'created_by': r[5],
                'created_at': r[6],
                'is_dead': bool(r[7]),
                'death_time': r[8],
                'respawn_time': r[9]
            } for r in rows]
    
    async def get_random_npcs_in_location(self, location_id: int, count: int = 3) -> List[Dict]:
        """Получение случайных NPC в локации"""
        npcs = await self.get_npcs_in_location(location_id)
        if not npcs:
            return []
        
        return random.sample(npcs, min(count, len(npcs)))
    
    async def add_npc_phrase(self, npc_id: int, phrase: str) -> bool:
        """Добавление фразы для NPC"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO npc_phrases (npc_id, phrase) VALUES (?, ?)',
                    (npc_id, phrase)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def get_npc_phrases(self, npc_id: int) -> List[str]:
        """Получение фраз NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT phrase FROM npc_phrases WHERE npc_id = ?',
                (npc_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            return [r[0] for r in rows]
    
    async def get_random_npc_phrase(self, npc_id: int) -> Optional[str]:
        """Получение случайной фразы NPC"""
        phrases = await self.get_npc_phrases(npc_id)
        if not phrases:
            return "..."
        
        return random.choice(phrases)
    
    async def add_npc_schedule(self, npc_id: int, hour: int, location_id: int) -> bool:
        """Добавление расписания для NPC"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO npc_schedules (npc_id, hour, location_id) VALUES (?, ?, ?)',
                    (npc_id, hour, location_id)
                )
                await db.commit()
                return True
        except:
            return False
    
    async def get_npc_location_by_hour(self, npc_id: int, hour: int) -> Optional[int]:
        """Получение локации NPC по часу"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT location_id FROM npc_schedules WHERE npc_id = ? AND hour = ?',
                (npc_id, hour)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def update_npc_reputation(self, npc_id: int, user_id: int, change: int):
        """Обновление репутации с NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''INSERT INTO npc_reputation (npc_id, user_id, reputation)
                   VALUES (?, ?, ?)
                   ON CONFLICT(npc_id, user_id) 
                   DO UPDATE SET reputation = reputation + ?''',
                (npc_id, user_id, change, change)
            )
            await db.commit()
    
    async def get_npc_reputation(self, npc_id: int, user_id: int) -> int:
        """Получение репутации с NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT reputation FROM npc_reputation WHERE npc_id = ? AND user_id = ?',
                (npc_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def kill_npc(self, npc_id: int, killer_id: int = None):
        """Убийство NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now()
            respawn = now + timedelta(minutes=random.randint(10, 60))
            
            await db.execute(
                '''UPDATE npcs 
                   SET is_dead = TRUE, death_time = ?, respawn_time = ?
                   WHERE id = ?''',
                (now.isoformat(), respawn.isoformat(), npc_id)
            )
            
            # Обновляем репутацию убийцы
            if killer_id:
                await self.update_npc_reputation(npc_id, killer_id, -50)
            
            await db.commit()
    
    async def respawn_npcs(self):
        """Возрождение NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now()
            
            await db.execute(
                '''UPDATE npcs 
                   SET is_dead = FALSE, death_time = NULL, respawn_time = NULL
                   WHERE is_dead = TRUE AND respawn_time < ?''',
                (now.isoformat(),)
            )
            
            # Перемещаем в случайную локацию
            await db.execute(
                '''UPDATE npcs 
                   SET location_id = (SELECT channel_id FROM locations ORDER BY RANDOM() LIMIT 1)
                   WHERE is_dead = FALSE AND type = 'путник' AND respawn_time IS NOT NULL'''
            )
            
            await db.commit()
    
    async def set_npc_report_channel(self, channel_id: int):
        """Установка канала для донесений NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO npc_report_channel (channel_id) VALUES (?)',
                (channel_id,)
            )
            await db.commit()
    
    async def get_npc_report_channel(self) -> Optional[int]:
        """Получение канала для донесений NPC"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT channel_id FROM npc_report_channel') as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    # ========== ОЧИСТКА ==========
    
    async def cleanup_old_data(self):
        """Очистка старых данных"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now()
            
            cutoff = (now - timedelta(days=7)).isoformat()
            await db.execute(
                'DELETE FROM bounties WHERE completed = TRUE AND completed_at < ?',
                (cutoff,)
            )
            
            await db.execute(
                'DELETE FROM bounties WHERE completed = FALSE AND expires_at < ?',
                (now.isoformat(),)
            )
            
            cutoff = (now - timedelta(hours=1)).isoformat()
            await db.execute(
                'DELETE FROM marriages WHERE status = "pending" AND proposed_at < ?',
                (cutoff,)
            )
            
            # Очистка старых налоговых записей (старше 3 часов)
            cutoff = (now - timedelta(hours=3)).isoformat()
            await db.execute(
                'DELETE FROM tax_stats WHERE collected_at < ?',
                (cutoff,)
            )
            
            await db.commit()
