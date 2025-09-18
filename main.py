import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import datetime
import random

# ==========================
# CONFIG
# ==========================
BOT_TOKEN = "yyy"
ADMIN_ID = 8300129370
ADMIN_USERNAME = "@BD_Network_Spport"

# Initialize Bot
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ==========================
# DATABASE (In-Memory Demo)
# ==========================
users_balance = {}       # {user_id: balance}
orders_history = {}      # {user_id: [orders]}


# ==========================
# States
# ==========================
class OrderState(StatesGroup):
    waiting_quantity = State()
    waiting_file = State()

class WithdrawState(StatesGroup):
    waiting_method = State()
    waiting_number = State()
    waiting_amount = State()


# ==========================
# Helpers
# ==========================
def generate_order_id():
    return ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=7))

def add_order(user_id, service, amount, status="Pending"):
    order_id = generate_order_id()
    order = {
        "id": order_id,
        "service": service,
        "amount": amount,
        "status": status,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    if user_id not in orders_history:
        orders_history[user_id] = []
    orders_history[user_id].append(order)
    return order


# ==========================
# START
# ==========================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    users_balance.setdefault(message.from_user.id, 0)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🛒 Account Sell", "💰 Main Account Balance")
    keyboard.add("💸 Withdrawal Balance", "📜 Transaction History")
    keyboard.add("📞 Support Info")
    await message.answer("🔥 Welcome to BD Network Bot", reply_markup=keyboard)


# ==========================
# ACCOUNT SELL
# ==========================
@dp.message_handler(lambda m: m.text == "🛒 Account Sell")
async def account_sell(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Fresh Gmail – 9৳", callback_data="buy_gmail"))
    keyboard.add(types.InlineKeyboardButton("Talkatone – 28৳", callback_data="buy_talkatone"))
    keyboard.add(types.InlineKeyboardButton("TextNow – 25৳", callback_data="buy_textnow"))
    keyboard.add(types.InlineKeyboardButton("Google Voice – 200৳", callback_data="buy_gvoice"))
    await message.answer("🛒 Select the account type you want to buy:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery, state: FSMContext):
    service_map = {
        "buy_gmail": ("Fresh Gmail", 9),
        "buy_talkatone": ("Talkatone", 28),
        "buy_textnow": ("TextNow", 25),
        "buy_gvoice": ("Google Voice", 200),
    }
    service, price = service_map[call.data]
    await state.update_data(service=service, price=price, quantity=1)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("➖", callback_data="qty_minus"),
        types.InlineKeyboardButton("➕", callback_data="qty_plus")
    )
    keyboard.add(types.InlineKeyboardButton("✅ Confirm", callback_data="qty_confirm"))

    await call.message.edit_text(
        f"🛒 {service} selected\n💵 Price: {price}৳ per pcs\n\n"
        f"➡️ Please select quantity: 1",
        reply_markup=keyboard
    )
    await OrderState.waiting_quantity.set()


@dp.callback_query_handler(lambda c: c.data.startswith("qty_"), state=OrderState.waiting_quantity)
async def process_quantity(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    service, price, qty = data["service"], data["price"], data["quantity"]

    if call.data == "qty_plus":
        qty += 1
    elif call.data == "qty_minus" and qty > 1:
        qty -= 1
    elif call.data == "qty_confirm":
        total = price * qty
        await state.update_data(quantity=qty, total=total)

        await call.message.edit_text(
            f"✅ Quantity: {qty}\n💵 Total Price: {total}৳\n\n"
            f"📂 Please upload your file (CSV/EXCEL)."
        )
        await OrderState.waiting_file.set()
        return

    await state.update_data(quantity=qty)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("➖", callback_data="qty_minus"),
        types.InlineKeyboardButton("➕", callback_data="qty_plus")
    )
    keyboard.add(types.InlineKeyboardButton("✅ Confirm", callback_data="qty_confirm"))

    await call.message.edit_text(
        f"🛒 {service} selected\n💵 Price: {price}৳ per pcs\n\n"
        f"➡️ Please select quantity: {qty}",
        reply_markup=keyboard
    )


@dp.message_handler(content_types=["document"], state=OrderState.waiting_file)
async def process_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    service, total = data["service"], data["total"]

    order = add_order(message.from_user.id, service, total)

    # Forward to admin
    await bot.send_message(
        ADMIN_ID,
        f"📥 New Order\n👤 User: {message.from_user.full_name}\n"
        f"🆔 Order ID: {order['id']}\n🛒 Service: {service}\n💵 Amount: {total}৳"
    )
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    await message.answer(
        "✅ আপনার অর্ডার গ্রহণ করা হয়েছে!\n"
        "📌 অনুগ্রহ করে 24 ঘন্টা অপেক্ষা করুন, রিপোর্ট পেমেন্ট Clear করে দেওয়া হবে।\n\n"
        "⚠️ কোনো Used File পেলে Payment বাতিল হবে।\n"
        "* Password Changed হলেও Payment বাতিল হবে।"
    )
    await state.finish()


# ==========================
# MAIN ACCOUNT BALANCE
# ==========================
@dp.message_handler(lambda m: m.text == "💰 Main Account Balance")
async def account_balance(message: types.Message):
    balance = users_balance.get(message.from_user.id, 0)
    await message.answer(
        f"👤 User: {message.from_user.full_name}\n"
        f"💳 Current Balance: {balance}৳\n\n"
        f"⚠️ Note: Balance update only by Admin after order/payment verification."
    )


# ==========================
# WITHDRAW BALANCE
# ==========================
@dp.message_handler(lambda m: m.text == "💸 Withdrawal Balance")
async def withdrawal(message: types.Message):
    await message.answer("💸 Withdrawal Request\n\n✅ Minimum 100 টাকা থেকে শুরু\n\n"
                         "Please enter Method (Bkash/Nagad/Binance):")
    await WithdrawState.waiting_method.set()


@dp.message_handler(state=WithdrawState.waiting_method)
async def withdraw_method(message: types.Message, state: FSMContext):
    await state.update_data(method=message.text)
    await message.answer("📱 Enter your number:")
    await WithdrawState.waiting_number.set()


@dp.message_handler(state=WithdrawState.waiting_number)
async def withdraw_number(message: types.Message, state: FSMContext):
    await state.update_data(number=message.text)
    await message.answer("💵 Enter amount (Minimum 100):")
    await WithdrawState.waiting_amount.set()


@dp.message_handler(state=WithdrawState.waiting_amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 100:
            await message.answer("❌ Minimum withdrawal 100৳")
            return
    except:
        await message.answer("❌ Enter a valid number")
        return

    data = await state.get_data()
    method, number = data["method"], data["number"]

    order = add_order(message.from_user.id, f"Withdraw {method}", amount)

    await bot.send_message(
        ADMIN_ID,
        f"💸 Withdrawal Request\n👤 {message.from_user.full_name}\n"
        f"Method: {method}\nNumber: {number}\nAmount: {amount}৳\nOrder ID: {order['id']}"
    )

    await message.answer(
        f"✅ Withdrawal request submitted!\n🆔 Order ID: {order['id']}\n"
        "📌 অনুগ্রহ করে এডমিন Approve না করা পর্যন্ত অপেক্ষা করুন।"
    )
    await state.finish()


# ==========================
# TRANSACTION HISTORY
# ==========================
@dp.message_handler(lambda m: m.text == "📜 Transaction History")
async def history(message: types.Message):
    user_id = message.from_user.id
    if user_id not in orders_history or len(orders_history[user_id]) == 0:
        await message.answer("❌ আপনার কোনো Transaction History নেই।")
        return

    text = "📜 Your Transactions\n\n"
    for order in orders_history[user_id]:
        text += f"🆔 {order['id']} | {order['service']} | {order['amount']}৳ | {order['status']} | {order['time']}\n"
    await message.answer(text)


# ==========================
# SUPPORT INFO
# ==========================
@dp.message_handler(lambda m: m.text == "📞 Support Info")
async def support(message: types.Message):
    await message.answer(
        "📞 Support Info  \n\n"
        "👤 Admin: @BD_Network_Spport  \n"
        "📢 Telegram Channel: https://t.me/Bd_Network_24  \n\n"
        "🕒 Support Time: 24/7 Active"
    )

