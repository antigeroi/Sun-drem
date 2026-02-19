import discord
from discord import ui
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from config import *

class ConfirmView(ui.View):
    """View для подтверждения действий"""
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None
    
    @ui.button(label="✅ Подтвердить", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label="❌ Отменить", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()

class PaginationView(ui.View):
    """View для пагинации"""
    def __init__(self, pages: List[discord.Embed], timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.max_page = len(pages) - 1
        self.update_buttons()
    
    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == self.max_page
    
    @ui.button(label="◀️ Назад", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @ui.button(label="▶️ Вперед", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < self.max_page:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

class TravelMeetView(ui.View):
    """View для встречи в пути"""
    def __init__(self, traveler1_id: int, traveler2_id: int):
        super().__init__(timeout=60)
        self.traveler1_id = traveler1_id
        self.traveler2_id = traveler2_id
    
    @ui.button(label="👋 Поприветствовать", style=discord.ButtonStyle.primary)
    async def greet(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"{interaction.user.mention} приветствует путника!")
    
    @ui.button(label="🚶 Идти дальше", style=discord.ButtonStyle.secondary)
    async def ignore(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"{interaction.user.mention} проходит мимо...")

def create_embed(title: str, description: str = "", color: int = EMBED_COLORS["info"],
                fields: List[Dict] = None, footer: str = None) -> discord.Embed:
    """Создание эмбеда"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now()
    )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', ''),
                value=field.get('value', ''),
                inline=field.get('inline', False)
            )
    
    if footer:
        embed.set_footer(text=footer)
    
    return embed

def format_currency(amount: int) -> str:
    """Форматирование валюты"""
    if abs(amount) == 1:
        return f"{amount} {CURRENCY_NAME}"
    return f"{amount} {CURRENCY_PLURAL}"

def create_hunger_bar(hunger: int) -> str:
    """Создание шкалы голода"""
    filled = hunger // 10
    empty = 10 - filled
    
    if hunger >= 70:
        emoji = "🟢"
    elif hunger >= 30:
        emoji = "🟡"
    else:
        emoji = "🔴"
    
    return f"{emoji} [{'█' * filled}{'░' * empty}] {hunger}/100"

def format_time_delta(delta: timedelta) -> str:
    """Форматирование временного интервала"""
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")
    if seconds > 0:
        parts.append(f"{seconds}с")
    
    return " ".join(parts)

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def create_paginated_embeds(title: str, items: List[Dict], items_per_page: int = 10,
                           color: int = EMBED_COLORS["info"]) -> List[discord.Embed]:
    """Создание пагинированных эмбедов"""
    if not items:
        return [create_embed(title, "Нет данных", color)]
    
    pages = []
    total_pages = (len(items) - 1) // items_per_page + 1
    
    for page in range(total_pages):
        start = page * items_per_page
        end = start + items_per_page
        page_items = items[start:end]
        
        description = ""
        for i, item in enumerate(page_items, start=start+1):
            description += f"**{i}.** {item.get('name', 'Без имени')}\n"
            if 'description' in item:
                description += f"   {truncate_text(item['description'], 50)}\n"
            if 'price' in item:
                description += f"   Цена: {format_currency(item['price'])}\n"
            if 'quantity' in item:
                description += f"   Количество: {item['quantity']}\n"
            description += "\n"
        
        embed = create_embed(
            f"{title} (Страница {page+1}/{total_pages})",
            description,
            color
        )
        pages.append(embed)
    
    return pages

def time_until_death(death_timer_start: Optional[str]) -> Optional[str]:
    """Время до смерти"""
    if not death_timer_start:
        return None
    
    try:
        death_time = datetime.fromisoformat(death_timer_start) + timedelta(minutes=DEATH_TIMER_MINUTES)
        now = datetime.now()
        
        if now >= death_time:
            return "СЕЙЧАС"
        
        return format_time_delta(death_time - now)
    except:
        return None
