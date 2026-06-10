import asyncio
import logging
import json
import os
from datetime import datetime
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════
TOKEN = os.getenv("BOT_TOKEN", "")
SUPPLIER_ID = int(os.getenv("SUPPLIER_ID", "0"))
COMPANY_NAME = "BOYARD Казахстан"
SUPPLIER_COMPANY = "ТОО Мебель Маркет"        # ← название компании поставщика
SUPPLIER_PHONE = "+7 700 000 0000"             # ← телефон поставщика

# ═══════════════════════════════════════════════════════════════
#  ПОСЁЛКИ И ГРУППЫ
# ═══════════════════════════════════════════════════════════════
VILLAGE_GROUPS = {
    "group_1": {
        "name": "Алматы и пригороды",
        "villages": ["Алматы", "Каскелен", "Талгар", "Алатау", "Есик", "Узынагаш", "Шамалган", "Туздыбастау"]
    },
    "group_2": {
        "name": "Конаев / Талдыкорган",
        "villages": ["Конаев", "Талдыкорган", "Текели"]
    },
    "group_3": {
        "name": "Уштобе / Сарыозек / Карабулак",
        "villages": ["Уштобе", "Сарыозек", "Карабулак"]
    },
    "group_4": {
        "name": "Жаркент / Чунджа / Саркан (восток)",
        "villages": ["Жаркент", "Чунджа", "Сарканд", "Жансугуров", "Балпык би"]
    },
    "group_5": {
        "name": "Шымкент / Тараз / Туркестан",
        "villages": ["Шымкент", "Тараз", "Туркестан"]
    },
    "group_6": {
        "name": "Жанакорган / Шиели",
        "villages": ["Жанакорган", "Шиели"]
    },
}

VILLAGE_TO_GROUP = {}
for gid, gdata in VILLAGE_GROUPS.items():
    for v in gdata["villages"]:
        VILLAGE_TO_GROUP[v] = gid

# ═══════════════════════════════════════════════════════════════
#  КАТАЛОГ ТОВАРОВ С ФОТО
# ═══════════════════════════════════════════════════════════════
CATALOG = {
    "Ручки": {
        "emoji": "🔧",
        "items": [
            {"name": "Ручки-скобы",       "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/jrVD6qcx6tKVqMUzId7HKHZIIxFZn8YfTQHFjyKG.jpg"},
            {"name": "Ручки-кнопки",      "photo": "https://www.boyard.biz/thumbs/product_list/products/Wwjssly3IijEe9MNU6EtbcchIMQ95bBD9shs7iHn.jpg"},
            {"name": "Торцевые ручки",    "photo": "https://www.boyard.biz/thumbs/product_list/products/ZI1slbhRyWiuQqSiSSYKtujVQRGEspaJiZY0WtUT.jpg"},
            {"name": "Профильные ручки",  "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/ms3ARc1nq6GVbjXMYvErjLzZyCO2ZqK7BLXTHNaR.jpg"},
            {"name": "Ручки-ракушки",     "photo": "https://www.boyard.biz/thumbs/product_list/products/5p5LRlRHf5PvMYtnNA5ZXScVqWo5kxdL8d3k54wl.jpg"},
            {"name": "Рейлинговые ручки", "photo": "https://www.boyard.biz/thumbs/product_list/products/rs067/ss6hi2GuQayLBXH8W0TNkznDgdj9RNApiNukJHxt.jpg"},
            {"name": "Врезные ручки",     "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/UWIIdeN3hyrYFPPtmRXF8N5dP5h9J26wFb71IJEU.jpg"},
        ]
    },
    "Петли": {
        "emoji": "🔩",
        "items": [
            {"name": "Петли NEO",         "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/c8c6YzZ58Lb8PDknYyEiPKVr1vrT0FAalzY9EH7S.jpg"},
            {"name": "Петли EVO",         "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/caboZfT138BSB2P2cIJCigjk1zwFD4y9XGrNUqmI.jpg"},
            {"name": "Накладные",         "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/clGZgfCDua9miVfKr3dyZhVa2kwB7fvpe448fa0s.jpg"},
            {"name": "Полунакладные",     "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/228IVZKfqBenLUvLqGqGgxAcKH5gSnQhWhXlarXx.jpg"},
            {"name": "Вкладные",          "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/N9vfhhdD7PynOgYhYctjcr7zWvnDOWBKBOoKGu8B.jpg"},
            {"name": "С доводчиком",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/k0SSIxY7lFJghNRSOCOagVniOvqynYEjy6qLX4DM.jpg"},
            {"name": "Без доводчика",     "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/frdOmJSGibM96ZQMzby0WZTZr9NTuf1w2mBVIML4.jpg"},
        ]
    },
    "Направляющие": {
        "emoji": "📏",
        "items": [
            {"name": "Шариковые",         "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/ti59mQ6QVMLvG3G1DJTwsRPCT9mhjpWnpj2fRWrp.jpg"},
            {"name": "Роликовые",         "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/eMGMtMwaPnbRCVsJ57Or8cBsl4lktGjeBRq0n07Y.jpg"},
            {"name": "Скрытого монтажа",  "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/PAxvZTgCwQhZkfQHZoHAEwuqLN53j6wFk2PRBaU2.jpg"},
            {"name": "Push-to-open",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/xMzJ81qzO9WFuUBbrpFMkyGMyOGu7biWW40jOwcw.jpg"},
            {"name": "Телескопические",   "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/UWIIdeN3hyrYFPPtmRXF8N5dP5h9J26wFb71IJEU.jpg"},
        ]
    },
    "Системы выдвижения": {
        "emoji": "🗄",
        "items": [
            {"name": "Металлобоксы",          "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/c8c6YzZ58Lb8PDknYyEiPKVr1vrT0FAalzY9EH7S.jpg"},
            {"name": "СТАРТ",                 "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/ms3ARc1nq6GVbjXMYvErjLzZyCO2ZqK7BLXTHNaR.jpg"},
            {"name": "Тонкостенные ящики",    "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/clGZgfCDua9miVfKr3dyZhVa2kwB7fvpe448fa0s.jpg"},
            {"name": "Внутренние ящики",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/228IVZKfqBenLUvLqGqGgxAcKH5gSnQhWhXlarXx.jpg"},
        ]
    },
    "Газлифты": {
        "emoji": "⚙️",
        "items": [
            {"name": "50N",  "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/jrVD6qcx6tKVqMUzId7HKHZIIxFZn8YfTQHFjyKG.jpg"},
            {"name": "60N",  "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/jrVD6qcx6tKVqMUzId7HKHZIIxFZn8YfTQHFjyKG.jpg"},
            {"name": "80N",  "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/jrVD6qcx6tKVqMUzId7HKHZIIxFZn8YfTQHFjyKG.jpg"},
            {"name": "100N", "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/jrVD6qcx6tKVqMUzId7HKHZIIxFZn8YfTQHFjyKG.jpg"},
            {"name": "120N", "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/jrVD6qcx6tKVqMUzId7HKHZIIxFZn8YfTQHFjyKG.jpg"},
            {"name": "150N", "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/jrVD6qcx6tKVqMUzId7HKHZIIxFZn8YfTQHFjyKG.jpg"},
        ]
    },
    "Корзины": {
        "emoji": "🧺",
        "items": [
            {"name": "Бутылочницы",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs067/ss6hi2GuQayLBXH8W0TNkznDgdj9RNApiNukJHxt.jpg"},
            {"name": "Карго",            "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/N9vfhhdD7PynOgYhYctjcr7zWvnDOWBKBOoKGu8B.jpg"},
            {"name": "Волшебный уголок", "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/eMGMtMwaPnbRCVsJ57Or8cBsl4lktGjeBRq0n07Y.jpg"},
            {"name": "Колонны",          "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/caboZfT138BSB2P2cIJCigjk1zwFD4y9XGrNUqmI.jpg"},
        ]
    },
    "Сушки": {
        "emoji": "🍽",
        "items": [
            {"name": "Верхние",         "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/UWIIdeN3hyrYFPPtmRXF8N5dP5h9J26wFb71IJEU.jpg"},
            {"name": "Нижние",          "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/c8c6YzZ58Lb8PDknYyEiPKVr1vrT0FAalzY9EH7S.jpg"},
            {"name": "Двухуровневые",   "photo": "https://www.boyard.biz/thumbs/product_list/products/rs160/caboZfT138BSB2P2cIJCigjk1zwFD4y9XGrNUqmI.jpg"},
            {"name": "Одноуровневые",   "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/ms3ARc1nq6GVbjXMYvErjLzZyCO2ZqK7BLXTHNaR.jpg"},
        ]
    },
    "Опоры": {
        "emoji": "🦵",
        "items": [
            {"name": "Кухонные",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/clGZgfCDua9miVfKr3dyZhVa2kwB7fvpe448fa0s.jpg"},
            {"name": "Регулируемые",  "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/228IVZKfqBenLUvLqGqGgxAcKH5gSnQhWhXlarXx.jpg"},
            {"name": "Барные",        "photo": "https://www.boyard.biz/thumbs/product_list/products/rs067/ss6hi2GuQayLBXH8W0TNkznDgdj9RNApiNukJHxt.jpg"},
            {"name": "Колёсные",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/ti59mQ6QVMLvG3G1DJTwsRPCT9mhjpWnpj2fRWrp.jpg"},
        ]
    },
    "Крепёж": {
        "emoji": "🔨",
        "items": [
            {"name": "Конфирматы",  "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/k0SSIxY7lFJghNRSOCOagVniOvqynYEjy6qLX4DM.jpg"},
            {"name": "Эксцентрики", "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/frdOmJSGibM96ZQMzby0WZTZr9NTuf1w2mBVIML4.jpg"},
            {"name": "Шканты",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/PAxvZTgCwQhZkfQHZoHAEwuqLN53j6wFk2PRBaU2.jpg"},
            {"name": "Евровинты",   "photo": "https://www.boyard.biz/thumbs/product_list/products/rs069/xMzJ81qzO9WFuUBbrpFMkyGMyOGu7biWW40jOwcw.jpg"},
            {"name": "Стяжки",      "photo": "https://www.boyard.biz/thumbs/product_list/products/rs068/N9vfhhdD7PynOgYhYctjcr7zWvnDOWBKBOoKGu8B.jpg"},
        ]
    },
}

# ═══════════════════════════════════════════════════════════════
#  ФАЙЛЫ ДАННЫХ
# ═══════════════════════════════════════════════════════════════
USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users(): return load_json(USERS_FILE, {})
def save_users(u): save_json(USERS_FILE, u)
def load_orders(): return load_json(ORDERS_FILE, {})
def save_orders(o): save_json(ORDERS_FILE, o)

def get_user(user_id):
    return load_users().get(str(user_id))

def save_user(user_id, data):
    users = load_users()
    users[str(user_id)] = data
    save_users(users)

def get_item_info(category, item_name):
    for item in CATALOG[category]["items"]:
        if item["name"] == item_name:
            return item
    return {"name": item_name, "photo": ""}

# ═══════════════════════════════════════════════════════════════
#  СОСТОЯНИЯ — один универсальный обработчик
# ═══════════════════════════════════════════════════════════════
(REG_NAME, REG_PHONE, REG_VILLAGE, MAIN_MENU,
 CATALOG_CAT, CATALOG_ITEM, CATALOG_QTY,
 CART_VIEW, ORDER_CONFIRM) = range(9)

# ═══════════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════════
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Каталог товаров", callback_data="open_catalog")],
        [InlineKeyboardButton("🛒 Моя корзина", callback_data="open_cart")],
        [InlineKeyboardButton("📋 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile")],
    ])

def catalog_kb():
    rows = []
    for cat_name, cat_data in CATALOG.items():
        rows.append([InlineKeyboardButton(
            f"{cat_data['emoji']} {cat_name}",
            callback_data=f"cat_{cat_name}"
        )])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def items_kb(category):
    rows = []
    for item in CATALOG[category]["items"]:
        rows.append([InlineKeyboardButton(
            f"📄 {item['name']}",
            callback_data=f"item_{category}|{item['name']}"
        )])
    rows.append([InlineKeyboardButton("← Назад к категориям", callback_data="open_catalog")])
    return InlineKeyboardMarkup(rows)

def qty_kb(category, item):
    rows = []
    row = []
    for qty in [1, 2, 3, 5, 10, 20, 50]:
        row.append(InlineKeyboardButton(str(qty), callback_data=f"qty_{category}|{item}|{qty}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("← Назад", callback_data=f"cat_{category}")])
    return InlineKeyboardMarkup(rows)

def after_add_kb(category):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Ещё из этой категории", callback_data=f"cat_{category}")],
        [InlineKeyboardButton("📦 К каталогу", callback_data="open_catalog")],
        [InlineKeyboardButton("🛒 Посмотреть корзину", callback_data="open_cart")],
    ])

def cart_kb(has_items):
    rows = []
    if has_items:
        rows.append([InlineKeyboardButton("✅ Отправить заявку поставщику", callback_data="send_order")])
        rows.append([InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart")])
    rows.append([InlineKeyboardButton("📦 Продолжить выбор", callback_data="open_catalog")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

# ═══════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════
async def go_to_catalog(update, context):
    query = update.callback_query
    try:
        await query.edit_message_text(
            "📦 *Каталог товаров BOYARD*\n\nВыберите категорию:",
            reply_markup=catalog_kb(),
            parse_mode="Markdown"
        )
    except:
        await query.message.reply_text(
            "📦 *Каталог товаров BOYARD*\n\nВыберите категорию:",
            reply_markup=catalog_kb(),
            parse_mode="Markdown"
        )
    return CATALOG_CAT

async def go_to_cart(update, context):
    query = update.callback_query
    cart = context.user_data.get("cart", {})
    if not cart:
        text = "🛒 *Корзина пуста*\n\nДобавьте товары из каталога."
    else:
        lines = ["🛒 *Ваша корзина:*\n"]
        for i, (key, qty) in enumerate(cart.items(), 1):
            cat, item = key.split("|", 1)
            lines.append(f"{i}. {item} — *{qty} шт.*")
        lines.append(f"\n📦 Итого позиций: {len(cart)}")
        lines.append(f"🔢 Итого единиц: {sum(cart.values())}")
        text = "\n".join(lines)
    try:
        await query.edit_message_text(text, reply_markup=cart_kb(bool(cart)), parse_mode="Markdown")
    except:
        await query.message.reply_text(text, reply_markup=cart_kb(bool(cart)), parse_mode="Markdown")
    return CART_VIEW

async def go_to_main(update, context):
    query = update.callback_query
    cart = context.user_data.get("cart", {})
    cart_count = sum(cart.values()) if cart else 0
    msg = "🏠 *Главное меню*"
    if cart_count > 0:
        msg += f"\n\n🛒 В корзине: {cart_count} ед."
    try:
        await query.edit_message_text(msg, reply_markup=main_menu_kb(), parse_mode="Markdown")
    except:
        await query.message.reply_text(msg, reply_markup=main_menu_kb(), parse_mode="Markdown")
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  СТАРТ / РЕГИСТРАЦИЯ
# ═══════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user:
        msg = f"👋 С возвращением, *{user['name']}*!\n\n🏠 Главное меню"
        cart = context.user_data.get("cart", {})
        if cart:
            msg += f"\n\n🛒 В корзине: {sum(cart.values())} ед."
        await update.message.reply_text(msg, reply_markup=main_menu_kb(), parse_mode="Markdown")
        return MAIN_MENU

    await update.message.reply_text(
        f"👋 Добро пожаловать!\n\n"
        f"Бот для заказа мебельной фурнитуры *{COMPANY_NAME}*\n"
        f"Поставщик: *{SUPPLIER_COMPANY}*\n\n"
        "Для начала давайте зарегистрируемся.\n\n"
        "📝 *Введите ваше имя:*",
        parse_mode="Markdown"
    )
    return REG_NAME

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["reg_name"] = update.message.text.strip()
    await update.message.reply_text("📞 *Введите номер телефона:*\nПример: +7 701 234 5678", parse_mode="Markdown")
    return REG_PHONE

async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["reg_phone"] = update.message.text.strip()
    rows = []
    for gid, gdata in VILLAGE_GROUPS.items():
        for village in gdata["villages"]:
            rows.append([InlineKeyboardButton(village, callback_data=f"village_{village}")])
    await update.message.reply_text(
        "📍 *Выберите ваш город/посёлок:*",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown"
    )
    return REG_VILLAGE

async def reg_village(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    village = query.data.replace("village_", "")
    user_id = update.effective_user.id
    save_user(user_id, {
        "name": context.user_data["reg_name"],
        "phone": context.user_data["reg_phone"],
        "village": village,
        "group": VILLAGE_TO_GROUP.get(village, "unknown"),
        "registered_at": datetime.now().isoformat()
    })
    await query.edit_message_text(
        f"✅ *Регистрация завершена!*\n\n"
        f"👤 {context.user_data['reg_name']}\n"
        f"📞 {context.user_data['reg_phone']}\n"
        f"📍 {village}\n\n"
        f"Теперь можете делать заказы!\n\n🏠 Главное меню",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК — все состояния через него
# ═══════════════════════════════════════════════════════════════
async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Навигация ─────────────────────────────────────────────
    if data == "main_menu":
        return await go_to_main(update, context)

    if data == "open_catalog":
        return await go_to_catalog(update, context)

    if data == "open_cart":
        return await go_to_cart(update, context)

    if data == "my_orders":
        return await show_my_orders(update, context)

    if data == "my_profile":
        return await show_profile(update, context)

    # ── Каталог: выбор категории ───────────────────────────────
    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        if category not in CATALOG:
            return CATALOG_CAT
        emoji = CATALOG[category]["emoji"]
        try:
            await query.edit_message_text(
                f"{emoji} *{category}*\n\nВыберите товар:",
                reply_markup=items_kb(category),
                parse_mode="Markdown"
            )
        except:
            await query.message.reply_text(
                f"{emoji} *{category}*\n\nВыберите товар:",
                reply_markup=items_kb(category),
                parse_mode="Markdown"
            )
        return CATALOG_ITEM

    # ── Каталог: выбор товара ──────────────────────────────────
    if data.startswith("item_"):
        rest = data.replace("item_", "")
        category, item_name = rest.split("|", 1)
        context.user_data["selected_cat"] = category
        context.user_data["selected_item"] = item_name

        cart = context.user_data.get("cart", {})
        key = f"{category}|{item_name}"
        in_cart = cart.get(key, 0)
        in_cart_text = f"\n✅ Уже в корзине: {in_cart} шт." if in_cart else ""

        item_info = get_item_info(category, item_name)
        photo_url = item_info.get("photo", "")

        caption = (
            f"📄 *{item_name}*\n"
            f"Категория: {category}{in_cart_text}\n\n"
            "Выберите количество:"
        )

        try:
            if photo_url:
                await query.message.reply_photo(
                    photo=photo_url,
                    caption=caption,
                    reply_markup=qty_kb(category, item_name),
                    parse_mode="Markdown"
                )
                await query.delete_message()
            else:
                await query.edit_message_text(
                    caption,
                    reply_markup=qty_kb(category, item_name),
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"Photo error: {e}")
            await query.edit_message_text(
                caption,
                reply_markup=qty_kb(category, item_name),
                parse_mode="Markdown"
            )
        return CATALOG_QTY

    # ── Каталог: выбор количества ──────────────────────────────
    if data.startswith("qty_"):
        parts = data.replace("qty_", "").split("|")
        category, item_name, qty = parts[0], parts[1], int(parts[2])

        cart = context.user_data.get("cart", {})
        key = f"{category}|{item_name}"
        cart[key] = cart.get(key, 0) + qty
        context.user_data["cart"] = cart

        total_units = sum(cart.values())
        text = (
            f"✅ *Добавлено в корзину!*\n\n"
            f"📄 {item_name}\n"
            f"🔢 +{qty} шт. (итого: {cart[key]} шт.)\n\n"
            f"🛒 Всего в корзине: {total_units} ед."
        )
        try:
            await query.edit_message_text(text, reply_markup=after_add_kb(category), parse_mode="Markdown")
        except:
            await query.message.reply_text(text, reply_markup=after_add_kb(category), parse_mode="Markdown")
        return CATALOG_QTY

    # ── Корзина: действия ──────────────────────────────────────
    if data == "clear_cart":
        context.user_data["cart"] = {}
        try:
            await query.edit_message_text(
                "🗑 Корзина очищена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 К каталогу", callback_data="open_catalog")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
                ])
            )
        except:
            pass
        return CART_VIEW

    if data == "send_order":
        return await confirm_order(update, context)

    # ── Подтверждение заказа ───────────────────────────────────
    if data == "confirm_yes":
        return await process_order(update, context)

    # ── Ответ клиента на заявку поставщика ─────────────────────
    if data.startswith("client_confirm|"):
        order_id = data.replace("client_confirm|", "")
        return await client_confirm(update, context, order_id)

    if data.startswith("client_cancel|"):
        order_id = data.replace("client_cancel|", "")
        orders = load_orders()
        if order_id in orders:
            orders[order_id]["status"] = "cancelled"
            save_orders(orders)
        try:
            await query.edit_message_text("❌ Заказ отменён. Нажмите /start чтобы начать заново.")
        except:
            pass
        return MAIN_MENU

    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ ПЕРЕД ОТПРАВКОЙ
# ═══════════════════════════════════════════════════════════════
async def confirm_order(update, context) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    user = get_user(user_id)
    cart = context.user_data.get("cart", {})

    lines = [f"📋 *Подтвердите заявку*\n"]
    lines.append(f"👤 {user['name']}")
    lines.append(f"📞 {user['phone']}")
    lines.append(f"📍 {user['village']}\n")
    lines.append(f"🏢 Поставщик: *{SUPPLIER_COMPANY}*\n")
    lines.append("*Товары:*")
    for i, (key, qty) in enumerate(cart.items(), 1):
        cat, item = key.split("|", 1)
        lines.append(f"{i}. {item} — {qty} шт.")

    try:
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm_yes")],
                [InlineKeyboardButton("← Назад в корзину", callback_data="open_cart")],
            ]),
            parse_mode="Markdown"
        )
    except:
        await query.message.reply_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm_yes")],
                [InlineKeyboardButton("← Назад в корзину", callback_data="open_cart")],
            ]),
            parse_mode="Markdown"
        )
    return ORDER_CONFIRM

# ═══════════════════════════════════════════════════════════════
#  ОТПРАВКА ЗАКАЗА
# ═══════════════════════════════════════════════════════════════
async def process_order(update, context) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    user = get_user(user_id)
    cart = context.user_data.get("cart", {})

    orders = load_orders()
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
    orders[order_id] = {
        "user_id": user_id,
        "user_name": user["name"],
        "user_phone": user["phone"],
        "village": user["village"],
        "group": user.get("group", ""),
        "cart": cart,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "availability": {}
    }
    save_orders(orders)

    # Отправляем поставщику
    await send_to_supplier(context, order_id, orders[order_id])

    # Уведомляем соседей
    await notify_neighbors(context, user_id, user, order_id)

    context.user_data["cart"] = {}

    try:
        await query.edit_message_text(
            f"✅ *Заявка отправлена в {SUPPLIER_COMPANY}!*\n\n"
            f"📋 Номер: `{order_id}`\n\n"
            f"Поставщик проверит наличие и уведомит вас.\n"
            f"📞 {SUPPLIER_PHONE}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]),
            parse_mode="Markdown"
        )
    except:
        pass
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  ОТПРАВКА ПОСТАВЩИКУ
# ═══════════════════════════════════════════════════════════════
async def send_to_supplier(context, order_id, order):
    if not SUPPLIER_ID:
        logger.error("SUPPLIER_ID не задан!")
        return

    # Короткий ключ для callback_data (макс 64 байта в Telegram)
    # Используем последние 12 символов order_id как short_oid
    short_oid = order_id[-12:]  # напр. "053350-123456"

    # Сохраняем маппинг short_oid -> full order_id в bot_data
    if "order_map" not in context.application.bot_data:
        context.application.bot_data["order_map"] = {}
    context.application.bot_data["order_map"][short_oid] = order_id

    lines = [f"🔔 *НОВАЯ ЗАЯВКА от мебельщика!*\n"]
    lines.append(f"🆔 {order_id}")
    lines.append(f"👤 {order['user_name']}")
    lines.append(f"📞 {order['user_phone']}")
    lines.append(f"📍 {order['village']}\n")
    lines.append("*Товары:*")

    rows = []
    keys = list(order["cart"].keys())
    for i, key in enumerate(keys):
        qty = order["cart"][key]
        cat, item = key.split("|", 1)
        lines.append(f"{i+1}. {item} — {qty} шт.")
        short_item = item[:12]
        # callback_data: "ay|<12chars>|<idx>" = макс ~20 байт ✅
        rows.append([
            InlineKeyboardButton(f"✅ {short_item}", callback_data=f"ay|{short_oid}|{i}"),
            InlineKeyboardButton(f"❌ {short_item}", callback_data=f"an|{short_oid}|{i}"),
        ])
    rows.append([InlineKeyboardButton("📤 Отправить ответ клиенту", callback_data=f"rc|{short_oid}")])

    try:
        await context.bot.send_message(
            chat_id=SUPPLIER_ID,
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="Markdown"
        )
        logger.info(f"Заявка {order_id} отправлена поставщику {SUPPLIER_ID}")
    except Exception as e:
        logger.error(f"Ошибка отправки поставщику: {e}")

# ═══════════════════════════════════════════════════════════════
#  ОБРАБОТКА ОТВЕТА ПОСТАВЩИКА
# ═══════════════════════════════════════════════════════════════
async def handle_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Восстанавливаем полный order_id из маппинга
    order_map = context.application.bot_data.get("order_map", {})

    # ── Отметка наличия товара ─────────────────────────────────
    if data.startswith("ay|") or data.startswith("an|"):
        parts = data.split("|")
        status = "yes" if parts[0] == "ay" else "no"
        short_oid = parts[1]
        item_idx = int(parts[2])

        order_id = order_map.get(short_oid)
        if not order_id:
            await query.answer("Заказ не найден", show_alert=True)
            return

        orders = load_orders()
        if order_id in orders:
            keys = list(orders[order_id]["cart"].keys())
            if item_idx < len(keys):
                item_key = keys[item_idx]
                orders[order_id]["availability"][item_key] = status
                save_orders(orders)
                emoji = "✅" if status == "yes" else "❌"
                cat, item = item_key.split("|", 1)
                await query.answer(f"{emoji} {item[:30]} отмечено", show_alert=False)

    # ── Отправить ответ клиенту ────────────────────────────────
    elif data.startswith("rc|"):
        short_oid = data.replace("rc|", "")
        order_id = order_map.get(short_oid)
        if not order_id:
            await query.answer("Заказ не найден", show_alert=True)
            return

        orders = load_orders()
        if order_id not in orders:
            await query.answer("Заказ не найден", show_alert=True)
            return

        order = orders[order_id]
        availability = order.get("availability", {})

        lines = [f"📋 *Ответ по вашей заявке*\n"]
        lines.append(f"🆔 {order_id}")
        lines.append(f"🏢 {SUPPLIER_COMPANY}\n")

        has_all = True
        for key, qty in order["cart"].items():
            cat, item = key.split("|", 1)
            avail = availability.get(key)
            if avail == "yes":
                lines.append(f"✅ {item} — {qty} шт.")
            elif avail == "no":
                lines.append(f"❌ {item} — {qty} шт. *(нет в наличии)*")
                has_all = False
            else:
                lines.append(f"⏳ {item} — {qty} шт. *(уточняется)*")

        lines.append("")
        if has_all:
            lines.append("✅ *Все товары есть в наличии!*")
        else:
            lines.append("⚠️ *Часть товаров отсутствует.*")
        lines.append("\nПодтвердите или отмените заказ:")

        try:
            await context.bot.send_message(
                chat_id=order["user_id"],
                text="\n".join(lines),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Подтвердить заказ", callback_data=f"client_confirm|{order_id}")],
                    [InlineKeyboardButton("❌ Отменить", callback_data=f"client_cancel|{order_id}")],
                ]),
                parse_mode="Markdown"
            )
            orders[order_id]["status"] = "awaiting_client"
            save_orders(orders)
            await query.answer("✅ Ответ отправлен клиенту!", show_alert=True)
        except Exception as e:
            await query.answer(f"Ошибка: {e}", show_alert=True)

# ═══════════════════════════════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ КЛИЕНТОМ
# ═══════════════════════════════════════════════════════════════
async def client_confirm(update, context, order_id) -> int:
    query = update.callback_query
    orders = load_orders()
    if order_id not in orders:
        return MAIN_MENU

    orders[order_id]["status"] = "confirmed"
    orders[order_id]["confirmed_at"] = datetime.now().isoformat()
    save_orders(orders)

    order = orders[order_id]

    if SUPPLIER_ID:
        try:
            await context.bot.send_message(
                chat_id=SUPPLIER_ID,
                text=(
                    f"✅ *Клиент подтвердил заказ!*\n\n"
                    f"🆔 {order_id}\n"
                    f"👤 {order['user_name']}\n"
                    f"📞 {order['user_phone']}\n"
                    f"📍 {order['village']}"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления поставщика: {e}")

    try:
        await query.edit_message_text(
            f"✅ *Заказ подтверждён!*\n\n"
            f"🆔 {order_id}\n"
            f"📍 Адрес доставки: *{order['village']}*\n\n"
            f"🚗 Закажите доставку через *InDrive*.\n"
            f"Если рядом есть другие мебельщики — разделите стоимость!\n\n"
            f"📞 Поставщик: {SUPPLIER_PHONE}",
            parse_mode="Markdown"
        )
    except:
        pass
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  МОИ ЗАКАЗЫ / ПРОФИЛЬ
# ═══════════════════════════════════════════════════════════════
async def show_my_orders(update, context) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    orders = load_orders()
    user_orders = {oid: o for oid, o in orders.items() if o.get("user_id") == user_id}

    status_map = {
        "pending": "⏳ Ожидает поставщика",
        "awaiting_client": "📩 Требует подтверждения",
        "confirmed": "✅ Подтверждён",
        "cancelled": "❌ Отменён",
    }

    if not user_orders:
        text = "📋 *Мои заказы*\n\nЗаказов пока нет."
    else:
        lines = ["📋 *Мои заказы:*\n"]
        for oid, o in sorted(user_orders.items(), reverse=True)[:5]:
            status = status_map.get(o.get("status", "pending"), "⏳")
            date = o.get("created_at", "")[:10]
            lines.append(f"📦 `{oid}`\n   {status}\n   📅 {date}\n")
        text = "\n".join(lines)

    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )
    except:
        pass
    return MAIN_MENU

async def show_profile(update, context) -> int:
    query = update.callback_query
    user = get_user(update.effective_user.id)
    text = (
        f"👤 *Мой профиль*\n\n"
        f"Имя: {user['name']}\n"
        f"Телефон: {user['phone']}\n"
        f"Посёлок: {user['village']}\n"
    )
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )
    except:
        pass
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  УВЕДОМЛЕНИЕ СОСЕДЯМ
# ═══════════════════════════════════════════════════════════════
async def notify_neighbors(context, sender_id, sender_user, order_id):
    sender_group = sender_user.get("group")
    if not sender_group:
        return
    users = load_users()
    for uid, udata in users.items():
        if int(uid) == sender_id:
            continue
        if udata.get("group") != sender_group:
            continue
        group_name = VILLAGE_GROUPS.get(sender_group, {}).get("name", "")
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    f"📢 *Заказ рядом с вами!*\n\n"
                    f"Мебельщик из района *{group_name}* оформляет заказ.\n\n"
                    f"💡 Присоединитесь сегодня — разделите стоимость доставки InDrive!\n\n"
                    f"/start — сделать заказ"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить {uid}: {e}")

# ═══════════════════════════════════════════════════════════════
#  КОМАНДЫ
# ═══════════════════════════════════════════════════════════════
async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📞 *Поставщик: {SUPPLIER_COMPANY}*\n\nТелефон: {SUPPLIER_PHONE}",
        parse_mode="Markdown"
    )

async def cmd_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPPLIER_ID:
        return
    users = load_users()
    orders = load_orders()
    confirmed = sum(1 for o in orders.values() if o.get("status") == "confirmed")
    pending = sum(1 for o in orders.values() if o.get("status") == "pending")
    await update.message.reply_text(
        f"📊 *Статистика*\n\n"
        f"👥 Мебельщиков: {len(users)}\n"
        f"📦 Всего заказов: {len(orders)}\n"
        f"✅ Подтверждённых: {confirmed}\n"
        f"⏳ Ожидают: {pending}",
        parse_mode="Markdown"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("↩️ /start — начать заново")
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════
#  HTTP СЕРВЕР (нужен для Fly.io)
# ═══════════════════════════════════════════════════════════════
async def health(request):
    return web.Response(text="OK")

async def start_web():
    app_web = web.Application()
    app_web.router.add_get("/", health)
    app_web.router.add_get("/health", health)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("HTTP сервер запущен на порту 8080")

# ═══════════════════════════════════════════════════════════════
#  ЗАПУСК
# ═══════════════════════════════════════════════════════════════
async def main():
    await start_web()
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone)],
            REG_VILLAGE:  [CallbackQueryHandler(reg_village, pattern="^village_")],
            MAIN_MENU:    [CallbackQueryHandler(universal_handler)],
            CATALOG_CAT:  [CallbackQueryHandler(universal_handler)],
            CATALOG_ITEM: [CallbackQueryHandler(universal_handler)],
            CATALOG_QTY:  [CallbackQueryHandler(universal_handler)],
            CART_VIEW:    [CallbackQueryHandler(universal_handler)],
            ORDER_CONFIRM:[CallbackQueryHandler(universal_handler)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        per_message=False,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("contact", cmd_contact))
    app.add_handler(CommandHandler("stat", cmd_stat))
    app.add_handler(CallbackQueryHandler(handle_supplier, pattern=r"^(ay|an|rc)\|"))

    print(f"🤖 Бот запущен! {COMPANY_NAME} | Поставщик: {SUPPLIER_COMPANY}")
    print(f"   Категорий: {len(CATALOG)} | Поставщик ID: {SUPPLIER_ID}")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
