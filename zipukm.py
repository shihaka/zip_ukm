import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# Состояние для поиска
class SearchState(StatesGroup):
    waiting_for_query = State()

# Загружаем переменные окружения
load_dotenv()

# Контакты
CONTACT_NAME = os.getenv("CONTACT_NAME", "Кирилл")
CONTACT_PHONE = os.getenv("CONTACT_PHONE", "+79991234567")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "kirill@example.com")
CONTACT_LOCATION = os.getenv("CONTACT_LOCATION", "Лямино, Свердловская обл.")

# Токен
BOT_TOKEN = os.getenv("TOKEN_ZIPUKM")

# Бот и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Путь к Excel
EXCEL_FILE = "price.xlsx"

# Хранилище для текущего товара
user_current_product = {}

# --- УТИЛИТЫ ---

# Приветственный текст
WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в каталог неликвидной и б/у техники!</b>\n\n"
    "Здесь вы найдёте спецтехнику, доступную:\n"
    "🔧 <i>для разбора на запчасти</i>,\n"
    "🚜 <i>или для дальнейшего использования</i>.\n\n"
    "Все машины — в наличии.\n"
    "Часть стоит без дела давно — поэтому <b>цена приятно удивит</b>.\n\n"
    "🔍 Листайте каталог или воспользуйтесь поиском —\n"
    "найдите нужную модель по названию или году.\n\n"
    "📞 Свяжитесь с нами — расскажем о состоянии,\n"
    "месте хранения и условиях покупки.\n\n"
    "🛠 <i>Хорошее прошлое — не приговор.</i>\n"
    "Возьмите свой «УРАЛ» или «Камаз» ещё раз!"
)

# Главное меню
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Каталог", callback_data="catalog"),
            InlineKeyboardButton(text="🔍 Поиск", callback_data="search")
        ],
        [
            InlineKeyboardButton(text="📞 Связаться", callback_data="contact")
        ]
    ])

# Функция: получить ID товара
def get_product_id(product):
    for key in ['id', 'ID', 'Id', 'ID товара', 'Артикул']:
        val = product.get(key)
        if val and str(val).strip() not in ("", "nan"):
            return val
    return "unknown"

# Функция: получить пути к фото
def get_photo_paths(product):
    photo_paths = []
    for i in range(1, 4):
        img_col = f"image_{i}"
        img_path_base = product.get(img_col, "")
        if not img_path_base or (isinstance(img_path_base, float) and pd.isna(img_path_base)):
            continue
        img_path_base = str(img_path_base).strip()
        if img_path_base.lower() in ("", "nan"):
            continue

        img_path = None
        if os.path.exists(img_path_base):
            img_path = img_path_base
        else:
            for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                path_with_ext = img_path_base + ext
                if os.path.exists(path_with_ext):
                    img_path = path_with_ext
                    break
        if img_path:
            photo_paths.append(img_path)
    return photo_paths

# Кэширование товаров
_products_cache = None
_last_modified = None

def load_products():
    global _products_cache, _last_modified
    if not os.path.exists(EXCEL_FILE):
        return []
    current_modified = os.path.getmtime(EXCEL_FILE)
    if _products_cache is not None and _last_modified == current_modified:
        return _products_cache

    try:
        df = pd.read_excel(EXCEL_FILE)
        df.columns = df.columns.str.strip().str.lower()
        df = df.astype(object).fillna("")
        _products_cache = df.to_dict(orient="records")
        _last_modified = current_modified
        return _products_cache
    except Exception as e:
        print(f"Ошибка чтения Excel: {e}")
        return []

# Создание страницы каталога
def create_catalog_page(products, page=0, per_page=7):
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_products = products[start_idx:end_idx]

    buttons = [
        [InlineKeyboardButton(
            text=f"{p['name']} ({p['where']})",
            callback_data=f"product_{get_product_id(p)}"
        )] for p in page_products
    ]

    total_pages = (len(products) + per_page - 1) // per_page
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"catalog_prev_{page}"))
    nav.append(InlineKeyboardButton(text="🏠 На главную", callback_data="back_to_main"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"catalog_next_{page}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Установка команды /start
async def set_bot_commands(bot: Bot):
    await bot.set_my_commands([BotCommand(command="/start", description="🚀 Начать работу с ботом")])

# --- ОБРАБОТЧИКИ ---

# /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu(), parse_mode="HTML")

# Показ каталога
@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.answer()  # ✅ Снимаем "часы"
    products = load_products()
    if not products:
        await callback.message.answer("Товары временно отсутствуют.", reply_markup=get_main_menu())
        return

    keyboard = create_catalog_page(products)
    await callback.message.answer("Выберите товар:", reply_markup=keyboard)

# Навигация по каталогу
@dp.callback_query(lambda c: c.data.startswith("catalog_prev_") or c.data.startswith("catalog_next_"))
async def handle_catalog_navigation(callback: types.CallbackQuery):
    await callback.answer()  # ✅
    action = "prev" if "prev" in callback.data else "next"
    current_page = int(callback.data.split("_")[-1])
    page = current_page - 1 if action == "prev" else current_page + 1
    products = load_products()
    keyboard = create_catalog_page(products, page=page)
    await callback.message.answer("Выберите товар:", reply_markup=keyboard)

# Возврат к каталогу
@dp.callback_query(lambda c: c.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery):
    await callback.answer()  # ✅
    products = load_products()
    keyboard = create_catalog_page(products)
    await callback.message.answer("Выберите товар:", reply_markup=keyboard)

# Возврат на главную
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.answer()  # ✅
    await callback.message.answer(WELCOME_TEXT, reply_markup=get_main_menu(), parse_mode="HTML")

# Показ товара (с статусом загрузки)
@dp.callback_query(lambda c: c.data.startswith("product_"))
async def handle_product_selection(callback: types.CallbackQuery):
    await callback.answer()  # ✅ Снимаем "часы"

    try:
        product_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.message.answer("Товар не найден.")
        return

    products = load_products()
    selected_product = next((p for p in products if str(get_product_id(p)) == str(product_id)), None)
    if not selected_product:
        await callback.message.answer("Товар не найден.")
        return

    # Сохраняем для "доп. фото"
    user_current_product[callback.from_user.id] = selected_product

    # Статус загрузки
    status_msg = await callback.message.answer("⏳ Минуту, загружаем информацию...")

    photo_paths = get_photo_paths(selected_product)
    first_photo_path = photo_paths[0] if photo_paths else None

    text = (
        f"<b>{selected_product['name']}</b>\n"
        f"📍 <b>Место:</b> {selected_product.get('where', 'Не указано')}\n"
        f"📅 <b>Год:</b> {selected_product.get('both', 'Не указано')}\n"
        f"💰 <b>Цена:</b> {selected_product.get('cost', 'Не указана')}\n"
        f"📦 <b>Статус:</b> {selected_product.get('status', 'Не указан')}\n"
        f"📄 <b>Описание:</b> {selected_product.get('description', 'Нет описания')}"
    )

    # Кнопки
    buttons = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_catalog")]
    ]
    if len(photo_paths) > 1:
        buttons.insert(0, [InlineKeyboardButton(text="🖼 Дополнительные фото", callback_data="more_photos")])
    buttons.extend([
        [InlineKeyboardButton(text="🛒 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="search")],
        [InlineKeyboardButton(text="📞 Связаться", callback_data="contact")]
    ])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем фото и описание (не удаляем старое сообщение!)
    if first_photo_path:
        await callback.message.answer_photo(
            photo=types.FSInputFile(first_photo_path),
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    # Удаляем статус
    try:
        await status_msg.delete()
    except:
        pass

# Показ дополнительных фото
@dp.callback_query(lambda c: c.data == "more_photos")
async def show_more_photos(callback: types.CallbackQuery):
    await callback.answer()  # ✅ Снимаем "часы"
    product = user_current_product.get(callback.from_user.id)
    if not product:
        await callback.message.answer("Ошибка: товар не найден.")
        return

    # Статус загрузки
    status_msg = await callback.message.answer("🖼 Минуту, загружаем фото...")

    photo_paths = get_photo_paths(product)[1:]  # все кроме первого
    if not photo_paths:
        await callback.message.answer("Нет дополнительных фото.")
        try:
            await status_msg.delete()
        except:
            pass
        return

    album = MediaGroupBuilder()
    for path in photo_paths:
        album.add_photo(media=types.FSInputFile(path))

    try:
        await callback.message.answer_media_group(media=album.build())
    except Exception as e:
        await callback.message.answer("Не удалось отправить фото.")
        print(f"Ошибка: {e}")

    try:
        await status_msg.delete()
    except:
        pass

# Связаться
@dp.callback_query(lambda c: c.data == "contact")
async def handle_contact(callback: types.CallbackQuery):
    await callback.answer()  # ✅
    contact_info = (
        f"📞 <b>Контактное лицо:</b> {CONTACT_NAME}\n"
        f"📱 <b>Телефон:</b> <a href='tel:{CONTACT_PHONE}'>{CONTACT_PHONE}</a>\n"
        # f"✉️ <b>Email:</b> <a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a>\n"
        f"📍 <b>Место:</b> {CONTACT_LOCATION}\n"
        f"🕒 <b>График:</b> Пн–Пт, 8:30–17:30"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в Telegram", url="https://t.me/shihaleevka")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])
    await callback.message.answer(contact_info, reply_markup=keyboard, parse_mode="HTML")

# Поиск
@dp.callback_query(lambda c: c.data == "search")
async def start_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()  # ✅
    await callback.message.answer("Введите часть названия товара (например, УРАЛ, 4320, Камаз):")
    await state.set_state(SearchState.waiting_for_query)

@dp.message(StateFilter(SearchState.waiting_for_query))
async def handle_search_query(message: types.Message, state: FSMContext):
    query = message.text.strip().lower()
    if not query:
        await message.answer("Введите корректный запрос.")
        return
    products = load_products()
    matches = [
        p for p in products
        if query in p.get('name', '').lower() or
           query in p.get('where', '').lower() or
           query in p.get('status', '').lower()
    ]
    if not matches:
        await message.answer(f"Ничего не найдено по запросу: *{query}*", reply_markup=get_main_menu(), parse_mode="Markdown")
        await state.clear()
        return
    keyboard = create_catalog_page(matches, per_page=10)
    await message.answer(f"Найдено {len(matches)} результатов:", reply_markup=keyboard)
    await state.clear()

# Запуск
async def main():
    print("Бот запущен...")
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())