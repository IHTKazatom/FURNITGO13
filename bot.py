import asyncio
import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
SUPPLIER_ID = int(os.getenv("SUPPLIER_ID", "0"))  # Telegram ID поставщика
COMPANY_NAME = "BOYARD Казахстан"

# ═══════════════════════════════════════════════════════════════
#  ПОСЁЛКИ И ГРУППЫ (соседние посёлки)
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

# Плоский список всех посёлков
ALL_VILLAGES = []
VILLAGE_TO_GROUP = {}
for gid, gdata in VILLAGE_GROUPS.items():
    for v in gdata["villages"]:
        ALL_VILLAGES.append(v)
        VILLAGE_TO_GROUP[v] = gid

# ═══════════════════════════════════════════════════════════════
#  КАТАЛОГ ТОВАРОВ
# ═══════════════════════════════════════════════════════════════
CATALOG = {
    "Ручки": {
        "emoji": "🔧",
        "items": [
            "Ручки-скобы", "Ручки-кнопки", "Торцевые ручки",
            "Профильные ручки", "Ручки-ракушки", "Рейлинговые ручки", "Врезные ручки"
        ]
    },
    "Петли": {
        "emoji": "🔩",
        "items": [
            "Петли NEO", "Петли EVO", "Накладные", "Полунакладные",
            "Вкладные", "С доводчиком", "Без доводчика"
        ]
    },
    "Направляющие": {
        "emoji": "📏",
        "items": [
            "Шариковые", "Роликовые", "Скрытого монтажа",
            "Push-to-open", "Телескопические"
        ]
    },
    "Системы выдвижения": {
        "emoji": "🗄",
        "items": ["Металлобоксы", "СТАРТ", "Тонкостенные ящики", "Внутренние ящики"]
    },
    "Газлифты": {
        "emoji": "⚙️",
        "items": ["50N", "60N", "80N", "100N", "120N", "150N"]
    },
    "Корзины": {
        "emoji": "🧺",
        "items": ["Бутылочницы", "Карго", "Волшебный уголок", "Колонны"]
    },
    "Сушки": {
        "emoji": "🍽",
        "items": ["Верхние", "Нижние", "Двухуровневые", "Одноуровневые"]
    },
    "Опоры": {
        "emoji": "🦵",
        "items": ["Кухонные", "Регулируемые", "Барные", "Колёсные"]
    },
    "Крепёж": {
        "emoji": "🔨",
        "items": ["Конфирматы", "Эксцентрики", "Шканты", "Евровинты", "Стяжки"]
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

def load_users():
    return load_json(USERS_FILE, {})

def save_users(users):
    save_json(USERS_FILE, users)

def load_orders():
    return load_json(ORDERS_FILE, {})

def save_orders(orders):
    save_json(ORDERS_FILE, orders)

def get_user(user_id):
    users = load_users()
    return users.get(str(user_id))

def save_user(user_id, data):
    users = load_users()
    users[str(user_id)] = data
    save_users(users)

# ═══════════════════════════════════════════════════════════════
#  СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════
(REG_NAME, REG_PHONE, REG_VILLAGE,
 MAIN_MENU, CATALOG_CAT, CATALOG_ITEM, CATALOG_QTY,
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
    items = CATALOG[category]["items"]
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(f"📄 {item}", callback_data=f"item_{category}|{item}")])
    rows.append([InlineKeyboardButton("← Назад", callback_data="open_catalog")])
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

def cart_kb(has_items):
    rows = []
    if has_items:
        rows.append([InlineKeyboardButton("✅ Отправить заявку поставщику", callback_data="send_order")])
        rows.append([InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart")])
    rows.append([InlineKeyboardButton("📦 Продолжить выбор", callback_data="open_catalog")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

# ═══════════════════════════════════════════════════════════════
#  СТАРТ / РЕГИСТРАЦИЯ
# ═══════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user:
        await show_main_menu(update, context, f"👋 С возвращением, {user['name']}!")
        return MAIN_MENU

    await update.message.reply_text(
        f"👋 Добро пожаловать в *{COMPANY_NAME}*!\n\n"
        "Это бот для заказа мебельной фурнитуры с доставкой в ваш посёлок.\n\n"
        "Для начала зарегистрируйтесь.\n\n"
        "📝 *Введите ваше имя:*",
        parse_mode="Markdown"
    )
    return REG_NAME

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["reg_name"] = update.message.text.strip()
    await update.message.reply_text("📞 *Введите ваш номер телефона:*\nПример: +7 701 234 5678", parse_mode="Markdown")
    return REG_PHONE

async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["reg_phone"] = update.message.text.strip()

    # Показываем список посёлков
    rows = []
    for gid, gdata in VILLAGE_GROUPS.items():
        for village in gdata["villages"]:
            rows.append([InlineKeyboardButton(village, callback_data=f"village_{village}")])

    await update.message.reply_text(
        "📍 *Выберите ваш посёлок:*",
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
        f"👤 Имя: {context.user_data['reg_name']}\n"
        f"📞 Телефон: {context.user_data['reg_phone']}\n"
        f"📍 Посёлок: {village}\n\n"
        "Теперь вы можете делать заказы!",
        parse_mode="Markdown"
    )
    await show_main_menu(update, context)
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text=None):
    user_id = update.effective_user.id
    user = get_user(user_id)
    cart = context.user_data.get("cart", {})
    cart_count = sum(cart.values()) if cart else 0

    msg = text or "🏠 *Главное меню*"
    if cart_count > 0:
        msg += f"\n\n🛒 В корзине: {cart_count} позиций"

    kb = main_menu_kb()
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=kb, parse_mode="Markdown")
        except:
            await update.callback_query.message.reply_text(msg, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="Markdown")

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        await show_main_menu(update, context)
        return MAIN_MENU
    elif query.data == "open_catalog":
        await query.edit_message_text(
            "📦 *Каталог товаров BOYARD*\n\nВыберите категорию:",
            reply_markup=catalog_kb(),
            parse_mode="Markdown"
        )
        return CATALOG_CAT
    elif query.data == "open_cart":
        return await show_cart(update, context)
    elif query.data == "my_orders":
        return await show_my_orders(update, context)
    elif query.data == "my_profile":
        return await show_profile(update, context)
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════
#  КАТАЛОГ
# ═══════════════════════════════════════════════════════════════
async def handle_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "open_catalog":
        await query.edit_message_text(
            "📦 *Каталог товаров BOYARD*\n\nВыберите категорию:",
            reply_markup=catalog_kb(),
            parse_mode="Markdown"
        )
        return CATALOG_CAT

    if query.data == "main_menu":
        await show_main_menu(update, context)
        return MAIN_MENU

    if query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        emoji = CATALOG[category]["emoji"]
        await query.edit_message_text(
            f"{emoji} *{category}*\n\nВыберите товар:",
            reply_markup=items_kb(category),
            parse_mode="Markdown"
        )
        return CATALOG_ITEM

    return CATALOG_CAT

async def handle_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "open_catalog":
        await query.edit_message_text(
            "📦 *Каталог товаров BOYARD*\n\nВыберите категорию:",
            reply_markup=catalog_kb(),
            parse_mode="Markdown"
        )
        return CATALOG_CAT

    if query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        emoji = CATALOG[category]["emoji"]
        await query.edit_message_text(
            f"{emoji} *{category}*\n\nВыберите товар:",
            reply_markup=items_kb(category),
            parse_mode="Markdown"
        )
        return CATALOG_ITEM

    if query.data.startswith("item_"):
        parts = query.data.replace("item_", "").split("|")
        category, item = parts[0], parts[1]
        context.user_data["selected_cat"] = category
        context.user_data["selected_item"] = item

        # Проверяем есть ли уже в корзине
        cart = context.user_data.get("cart", {})
        key = f"{category}|{item}"
        in_cart = cart.get(key, 0)
        in_cart_text = f"\n✅ Уже в корзине: {in_cart} шт." if in_cart else ""

        await query.edit_message_text(
            f"📄 *{item}*\nКатегория: {category}{in_cart_text}\n\n"
            "Выберите количество:",
            reply_markup=qty_kb(category, item),
            parse_mode="Markdown"
        )
        return CATALOG_QTY

    return CATALOG_ITEM

async def handle_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        emoji = CATALOG[category]["emoji"]
        await query.edit_message_text(
            f"{emoji} *{category}*\n\nВыберите товар:",
            reply_markup=items_kb(category),
            parse_mode="Markdown"
        )
        return CATALOG_ITEM

    if query.data.startswith("qty_"):
        parts = query.data.replace("qty_", "").split("|")
        category, item, qty = parts[0], parts[1], int(parts[2])

        cart = context.user_data.get("cart", {})
        key = f"{category}|{item}"
        cart[key] = cart.get(key, 0) + qty
        context.user_data["cart"] = cart

        total = sum(cart.values())
        await query.edit_message_text(
            f"✅ *Добавлено в корзину!*\n\n"
            f"📄 {item}\n"
            f"🔢 Количество: +{qty} шт. (итого: {cart[key]} шт.)\n\n"
            f"🛒 Всего в корзине: {total} позиций",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё из этой категории", callback_data=f"cat_{category}")],
                [InlineKeyboardButton("📦 К каталогу", callback_data="open_catalog")],
                [InlineKeyboardButton("🛒 Посмотреть корзину", callback_data="open_cart")],
            ]),
            parse_mode="Markdown"
        )
        return CATALOG_QTY

    return CATALOG_QTY

# ═══════════════════════════════════════════════════════════════
#  КОРЗИНА
# ═══════════════════════════════════════════════════════════════
async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    cart = context.user_data.get("cart", {})

    if not cart:
        text = "🛒 *Корзина пуста*\n\nДобавьте товары из каталога."
    else:
        lines = ["🛒 *Ваша корзина:*\n"]
        for i, (key, qty) in enumerate(cart.items(), 1):
            cat, item = key.split("|")
            lines.append(f"{i}. {item} — *{qty} шт.*")
        lines.append(f"\n📦 Итого позиций: {len(cart)}")
        lines.append(f"🔢 Итого единиц: {sum(cart.values())}")
        text = "\n".join(lines)

    try:
        await query.edit_message_text(text, reply_markup=cart_kb(bool(cart)), parse_mode="Markdown")
    except:
        await query.message.reply_text(text, reply_markup=cart_kb(bool(cart)), parse_mode="Markdown")
    return CART_VIEW

async def handle_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "open_catalog":
        await query.edit_message_text(
            "📦 *Каталог товаров BOYARD*\n\nВыберите категорию:",
            reply_markup=catalog_kb(),
            parse_mode="Markdown"
        )
        return CATALOG_CAT

    if query.data == "main_menu":
        await show_main_menu(update, context)
        return MAIN_MENU

    if query.data == "clear_cart":
        context.user_data["cart"] = {}
        await query.edit_message_text(
            "🗑 Корзина очищена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 К каталогу", callback_data="open_catalog")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ])
        )
        return CART_VIEW

    if query.data == "send_order":
        return await confirm_order(update, context)

    if query.data == "open_cart":
        return await show_cart(update, context)

    return CART_VIEW

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    user = get_user(user_id)
    cart = context.user_data.get("cart", {})

    lines = [f"📋 *Подтвердите заявку*\n"]
    lines.append(f"👤 {user['name']}")
    lines.append(f"📞 {user['phone']}")
    lines.append(f"📍 {user['village']}\n")
    lines.append("*Товары:*")
    for i, (key, qty) in enumerate(cart.items(), 1):
        cat, item = key.split("|")
        lines.append(f"{i}. {item} — {qty} шт.")

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm_yes")],
            [InlineKeyboardButton("← Назад в корзину", callback_data="open_cart")],
        ]),
        parse_mode="Markdown"
    )
    return ORDER_CONFIRM

async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "open_cart":
        return await show_cart(update, context)

    if query.data == "confirm_yes":
        user_id = update.effective_user.id
        user = get_user(user_id)
        cart = context.user_data.get("cart", {})

        # Сохраняем заказ
        orders = load_orders()
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
        orders[order_id] = {
            "user_id": user_id,
            "user_name": user["name"],
            "user_phone": user["phone"],
            "village": user["village"],
            "group": user["group"],
            "cart": cart,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "availability": {}
        }
        save_orders(orders)

        # Отправляем поставщику
        await send_order_to_supplier(context, order_id, orders[order_id])

        # Уведомляем соседних мебельщиков
        await notify_neighbors(context, user_id, user, order_id)

        # Очищаем корзину
        context.user_data["cart"] = {}

        await query.edit_message_text(
            f"✅ *Заявка отправлена!*\n\n"
            f"📋 Номер заказа: `{order_id}`\n\n"
            f"Поставщик проверит наличие и вернётся к вам.\n"
            f"Вы получите уведомление.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]),
            parse_mode="Markdown"
        )
        return MAIN_MENU

    return ORDER_CONFIRM

# ═══════════════════════════════════════════════════════════════
#  УВЕДОМЛЕНИЕ СОСЕДЯМ
# ═══════════════════════════════════════════════════════════════
async def notify_neighbors(context, sender_id, sender_user, order_id):
    sender_group = sender_user.get("group")
    if not sender_group:
        return

    users = load_users()
    notified = 0

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
                    f"📢 *Новый заказ рядом с вами!*\n\n"
                    f"Мебельщик из района *{group_name}* оформляет заказ у поставщика.\n\n"
                    f"💡 Присоединитесь сегодня — разделите стоимость доставки InDrive!\n\n"
                    f"Нажмите /start чтобы сделать свой заказ."
                ),
                parse_mode="Markdown"
            )
            notified += 1
        except Exception as e:
            logger.warning(f"Не удалось уведомить {uid}: {e}")

    logger.info(f"Уведомлено соседей: {notified}")

# ═══════════════════════════════════════════════════════════════
#  ОТПРАВКА ПОСТАВЩИКУ
# ═══════════════════════════════════════════════════════════════
async def send_order_to_supplier(context, order_id, order):
    if not SUPPLIER_ID:
        return

    lines = [f"📦 *НОВАЯ ЗАЯВКА*\n"]
    lines.append(f"🆔 {order_id}")
    lines.append(f"👤 {order['user_name']}")
    lines.append(f"📞 {order['user_phone']}")
    lines.append(f"📍 {order['village']}\n")
    lines.append("*Товары:*")
    for i, (key, qty) in enumerate(order["cart"].items(), 1):
        cat, item = key.split("|")
        lines.append(f"{i}. {item} — {qty} шт.")

    # Кнопки наличия для каждой позиции
    rows = []
    for key in order["cart"]:
        cat, item = key.split("|")
        short = item[:20]
        rows.append([
            InlineKeyboardButton(f"✅ {short}", callback_data=f"avail_yes|{order_id}|{key}"),
            InlineKeyboardButton(f"❌ {short}", callback_data=f"avail_no|{order_id}|{key}"),
        ])
    rows.append([InlineKeyboardButton("📤 Отправить ответ клиенту", callback_data=f"reply_client|{order_id}")])

    try:
        await context.bot.send_message(
            chat_id=SUPPLIER_ID,
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить поставщику: {e}")

# ═══════════════════════════════════════════════════════════════
#  ОБРАБОТКА ОТВЕТА ПОСТАВЩИКА
# ═══════════════════════════════════════════════════════════════
async def handle_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("avail_yes|") or query.data.startswith("avail_no|"):
        parts = query.data.split("|")
        status = "yes" if parts[0] == "avail_yes" else "no"
        order_id = parts[1]
        item_key = "|".join(parts[2:])

        orders = load_orders()
        if order_id in orders:
            if "availability" not in orders[order_id]:
                orders[order_id]["availability"] = {}
            orders[order_id]["availability"][item_key] = status
            save_orders(orders)

        emoji = "✅" if status == "yes" else "❌"
        cat, item = item_key.split("|")
        await query.answer(f"{emoji} {item} — отмечено", show_alert=False)

    elif query.data.startswith("reply_client|"):
        order_id = query.data.replace("reply_client|", "")
        orders = load_orders()
        if order_id not in orders:
            await query.answer("Заказ не найден", show_alert=True)
            return

        order = orders[order_id]
        availability = order.get("availability", {})

        # Формируем ответ клиенту
        lines = [f"📋 *Ответ по вашей заявке*\n"]
        lines.append(f"🆔 {order_id}\n")

        has_all = True
        for key, qty in order["cart"].items():
            cat, item = key.split("|")
            avail = availability.get(key)
            if avail == "yes":
                lines.append(f"✅ {item} — {qty} шт. *ЕСТЬ*")
            elif avail == "no":
                lines.append(f"❌ {item} — {qty} шт. *НЕТ*")
                has_all = False
            else:
                lines.append(f"⏳ {item} — {qty} шт. *уточняется*")

        if has_all:
            lines.append("\n✅ *Все товары в наличии!*")
        else:
            lines.append("\n⚠️ *Часть товаров отсутствует.*")

        lines.append("\nПодтвердите заказ или отмените.")

        # Отправляем клиенту
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
            await query.edit_message_text(
                query.message.text + "\n\n✅ *Ответ отправлен клиенту!*",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.answer(f"Ошибка: {e}", show_alert=True)

# ═══════════════════════════════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ КЛИЕНТОМ
# ═══════════════════════════════════════════════════════════════
async def handle_client_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("client_confirm|"):
        order_id = query.data.replace("client_confirm|", "")
        orders = load_orders()
        if order_id in orders:
            orders[order_id]["status"] = "confirmed"
            orders[order_id]["confirmed_at"] = datetime.now().isoformat()
            save_orders(orders)

            order = orders[order_id]
            village = order["village"]

            # Уведомляем поставщика
            if SUPPLIER_ID:
                await context.bot.send_message(
                    chat_id=SUPPLIER_ID,
                    text=f"✅ *Клиент подтвердил заказ!*\n\n🆔 {order_id}\n👤 {order['user_name']}\n📞 {order['user_phone']}\n📍 {village}",
                    parse_mode="Markdown"
                )

            await query.edit_message_text(
                f"✅ *Заказ подтверждён!*\n\n"
                f"🆔 {order_id}\n\n"
                f"📍 Ваш адрес: *{village}*\n\n"
                f"🚗 Теперь вы можете заказать доставку через *InDrive*.\n"
                f"Если в вашем районе есть другие мебельщики — разделите стоимость доставки!\n\n"
                f"📞 Телефон поставщика уточните командой /contact",
                parse_mode="Markdown"
            )

    elif query.data.startswith("client_cancel|"):
        order_id = query.data.replace("client_cancel|", "")
        orders = load_orders()
        if order_id in orders:
            orders[order_id]["status"] = "cancelled"
            save_orders(orders)

        await query.edit_message_text("❌ Заказ отменён. Нажмите /start чтобы начать заново.")

# ═══════════════════════════════════════════════════════════════
#  МОИ ЗАКАЗЫ / ПРОФИЛЬ
# ═══════════════════════════════════════════════════════════════
async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    orders = load_orders()

    user_orders = {oid: o for oid, o in orders.items() if o.get("user_id") == user_id}

    if not user_orders:
        text = "📋 *Мои заказы*\n\nЗаказов пока нет."
    else:
        status_map = {
            "pending": "⏳ Ожидает поставщика",
            "awaiting_client": "📩 Требует вашего подтверждения",
            "confirmed": "✅ Подтверждён",
            "cancelled": "❌ Отменён",
        }
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

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = update.effective_user.id
    user = get_user(user_id)

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
#  КОМАНДЫ
# ═══════════════════════════════════════════════════════════════
async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Контакт поставщика BOYARD:*\n\nСвяжитесь с вашим менеджером для уточнения деталей.",
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
#  ЗАПУСК
# ═══════════════════════════════════════════════════════════════
async def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone)],
            REG_VILLAGE:  [CallbackQueryHandler(reg_village, pattern="^village_")],
            MAIN_MENU:    [CallbackQueryHandler(handle_main_menu)],
            CATALOG_CAT:  [CallbackQueryHandler(handle_catalog)],
            CATALOG_ITEM: [CallbackQueryHandler(handle_items)],
            CATALOG_QTY:  [CallbackQueryHandler(handle_qty)],
            CART_VIEW:    [CallbackQueryHandler(handle_cart)],
            ORDER_CONFIRM:[CallbackQueryHandler(handle_confirm)],
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
    app.add_handler(CallbackQueryHandler(handle_supplier, pattern="^(avail_yes|avail_no|reply_client)"))
    app.add_handler(CallbackQueryHandler(handle_client_response, pattern="^(client_confirm|client_cancel)"))

    print(f"🤖 Бот запущен! {COMPANY_NAME}")
    print(f"   Категорий: {len(CATALOG)}")
    print(f"   Поставщик ID: {SUPPLIER_ID}")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
