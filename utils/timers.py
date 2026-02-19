import asyncio
from datetime import datetime, timedelta
import discord
import random
from database import Database
from config import *
from utils.helpers import create_embed, EMBED_COLORS

class TimerManager:
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.running = False
    
    async def start(self):
        """Запуск всех таймеров"""
        self.running = True
        await self.bot.wait_until_ready()
        print("✅ Таймеры запущены")
        
        asyncio.create_task(self.hunger_timer())
        asyncio.create_task(self.death_timer())
        asyncio.create_task(self.salary_timer())
        asyncio.create_task(self.travel_timer())
        asyncio.create_task(self.travel_events_timer())
        asyncio.create_task(self.npc_respawn_timer())
        asyncio.create_task(self.cleanup_timer())
    
    async def hunger_timer(self):
        """Таймер голода (каждые 2 минуты)"""
        while self.running and not self.bot.is_closed():
            try:
                await asyncio.sleep(HUNGER_ACTIVE_CHECK_INTERVAL)
                await self.db.decrease_hunger_for_active(1)
            except Exception as e:
                print(f"Ошибка в hunger_timer: {e}")
    
    async def death_timer(self):
        """Таймер смерти (каждую минуту)"""
        while self.running and not self.bot.is_closed():
            try:
                await asyncio.sleep(60)
                
                dying = await self.db.get_dying_characters()
                now = datetime.now()
                
                for char in dying:
                    try:
                        death_time = datetime.fromisoformat(char['death_timer_start']) + timedelta(minutes=DEATH_TIMER_MINUTES)
                        
                        if now >= death_time:
                            await self.db.kill_character(char['user_id'])
                            
                            user = self.bot.get_user(char['user_id'])
                            if user:
                                embed = create_embed(
                                    "💀 СМЕРТЬ ПЕРСОНАЖА",
                                    f"Ваш персонаж **{char['character_name']}** умер от голода.",
                                    EMBED_COLORS["death"]
                                )
                                try:
                                    await user.send(embed=embed)
                                except:
                                    pass
                    
                    except Exception as e:
                        print(f"Ошибка при смерти персонажа {char['user_id']}: {e}")
                
            except Exception as e:
                print(f"Ошибка в death_timer: {e}")
    
    async def salary_timer(self):
        """Таймер выплат зарплат по титулам (каждый час)"""
        while self.running and not self.bot.is_closed():
            try:
                await asyncio.sleep(3600)
                
                # Получаем все титулы с зарплатой
                async with self.db.db.execute(
                    'SELECT * FROM titles WHERE salary > 0 AND salary_interval > 0'
                ) as cursor:
                    titles = await cursor.fetchall()
                
                for title_row in titles:
                    title_id = title_row[0]
                    salary = title_row[2]
                    interval = title_row[3]
                    treasury_id = title_row[4]
                    
                    # Проверяем, прошло ли достаточно времени
                    # В реальной реализации нужно хранить время последней выплаты
                    
                    # Получаем владельцев титула
                    async with self.db.db.execute(
                        'SELECT character_id FROM character_titles WHERE title_id = ?',
                        (title_id,)
                    ) as cursor:
                        owners = await cursor.fetchall()
                    
                    for owner in owners:
                        user_id = owner[0]
                        
                        if treasury_id:
                            # Берем из хранилища
                            treasury = await self.db.get_treasury(treasury_id)
                            if treasury and treasury['balance'] >= salary:
                                await self.db.withdraw_from_treasury(treasury_id, 0, salary)
                                await self.db.update_balance(user_id, salary)
                            else:
                                # Недостаточно средств
                                pass
                        else:
                            # Просто выдаем
                            await self.db.update_balance(user_id, salary)
                
            except Exception as e:
                print(f"Ошибка в salary_timer: {e}")
    
    async def travel_timer(self):
        """Таймер путешествий (каждые 10 секунд)"""
        while self.running and not self.bot.is_closed():
            try:
                await asyncio.sleep(10)
                
                travelers = await self.db.get_travelers_on_road()
                now = datetime.now()
                
                for traveler in travelers:
                    try:
                        end_time = datetime.fromisoformat(traveler['end'])
                        
                        if now >= end_time:
                            # Завершаем путешествие
                            destination = await self.db.finish_travel(traveler['user_id'])
                            
                            user = self.bot.get_user(traveler['user_id'])
                            if user:
                                # Отправляем в канал назначения
                                # В реальной реализации нужно получить канал и отправить сообщение
                                pass
                    
                    except Exception as e:
                        print(f"Ошибка при завершении путешествия {traveler['user_id']}: {e}")
                
            except Exception as e:
                print(f"Ошибка в travel_timer: {e}")
    
    async def travel_events_timer(self):
        """Таймер атмосферных событий в пути"""
        while self.running and not self.bot.is_closed():
            try:
                interval = await self.db.get_event_interval()
                enabled = await self.db.get_events_enabled()
                
                if not enabled:
                    await asyncio.sleep(60)
                    continue
                
                await asyncio.sleep(interval)
                
                road_channel_id = await self.db.get_road_channel()
                if not road_channel_id:
                    await asyncio.sleep(60)
                    continue
                
                road_channel = self.bot.get_channel(road_channel_id)
                if not road_channel:
                    await asyncio.sleep(60)
                    continue
                
                event_text = await self.db.get_random_travel_event()
                if event_text:
                    await road_channel.send(f"*{event_text}*")
                
            except Exception as e:
                print(f"Ошибка в travel_events_timer: {e}")
    
    async def npc_respawn_timer(self):
        """Таймер возрождения NPC (каждые 5 минут)"""
        while self.running and not self.bot.is_closed():
            try:
                await asyncio.sleep(300)
                await self.db.respawn_npcs()
            except Exception as e:
                print(f"Ошибка в npc_respawn_timer: {e}")
    
    async def cleanup_timer(self):
        """Таймер очистки (каждые 24 часа)"""
        while self.running and not self.bot.is_closed():
            try:
                await asyncio.sleep(86400)
                await self.db.cleanup_old_data()
                print("✅ Очистка старых данных выполнена")
            except Exception as e:
                print(f"Ошибка в cleanup_timer: {e}")
