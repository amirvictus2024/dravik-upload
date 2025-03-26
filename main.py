import logging
import datetime
import pickle
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
import uuid

# Bot settings
BOT_TOKEN = '7431582943:AAGpryYd3j0EA7_WiAgGY1pYUSDpbuGsjFw'
PRIMARY_ADMIN = 6712954701
CHANNEL_ID = "Dravik_official"
BOT_USERNAME = "DravikUploader_bot"

# Database files
DB_FILE = 'bot_database.pkl'
ADMINS_FILE = 'admins_database.pkl'


# Initialize database
def load_database():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'rb') as f:
            return pickle.load(f)
    return {}


def save_database(data):
    with open(DB_FILE, 'wb') as f:
        pickle.dump(data, f)


def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'rb') as f:
            return pickle.load(f)
    return [PRIMARY_ADMIN]


def save_admins(admins_list):
    with open(ADMINS_FILE, 'wb') as f:
        pickle.dump(admins_list, f)


# Load initial data
shared_files = load_database()
admins = load_admins()
# admin_state: می‌تواند یک رشته ساده یا tuple شامل (حالت, کلید فایل) باشد.
admin_state = None


def generate_share_link(file_id, bot_username):
    unique_id = str(uuid.uuid4())[:8]
    return f"https://t.me/{bot_username}?start={unique_id}", unique_id


def clean_expired_files():
    current_time = datetime.datetime.now()
    expired_keys = [
        k for k, v in shared_files.items()
        if v['expiry'] is not None and v['expiry'] < current_time
    ]
    for k in expired_keys:
        del shared_files[k]
    if expired_keys:
        save_database(shared_files)


def start(update: Update, context: CallbackContext):
    clean_expired_files()
    chat_id = update.effective_chat.id
    args = context.args

    if args and len(args) > 0:
        file_key = args[0]
        if file_key in shared_files:
            file_data = shared_files[file_key]
            if file_data['expiry'] is None or file_data[
                    'expiry'] > datetime.datetime.now():
                try:
                    context.bot.send_document(chat_id=chat_id,
                                              document=file_data['file_id'])
                except:
                    try:
                        context.bot.send_photo(chat_id=chat_id,
                                               photo=file_data['file_id'])
                    except:
                        try:
                            context.bot.send_video(chat_id=chat_id,
                                                   video=file_data['file_id'])
                        except:
                            try:
                                context.bot.send_audio(
                                    chat_id=chat_id,
                                    audio=file_data['file_id'])
                            except:
                                update.message.reply_text(
                                    "❌ خطا در ارسال فایل.")
                return
            else:
                update.message.reply_text("❌ این لینک منقضی شده است.")
                return

    if chat_id in admins:
        keyboard = [[
            InlineKeyboardButton("📤 آپلود فایل", callback_data='uploadfile'),
            InlineKeyboardButton("🔄 جایگزینی فایل",
                                 callback_data='replacefile')
        ],
                    [
                        InlineKeyboardButton("🗑️ حذف فایل",
                                             callback_data='deletefile'),
                        InlineKeyboardButton("➕ افزودن ادمین",
                                             callback_data='addadmin')
                    ],
                    [
                        InlineKeyboardButton("➖ حذف ادمین",
                                             callback_data='removeadmin'),
                        InlineKeyboardButton("📋 لیست فایل‌ها",
                                             callback_data='listfiles')
                    ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("🛠 پنل مدیریت:", reply_markup=reply_markup)
    else:
        update.message.reply_text(
            "👋 سلام! برای دریافت فایل، لطفا از لینک اشتراکی استفاده کنید.")


def button_handler(update: Update, context: CallbackContext):
    global admin_state
    query = update.callback_query
    query.answer()

    if query.from_user.id not in admins:
        query.edit_message_text("❌ شما اجازه دسترسی به این بخش را ندارید.")
        return

    data = query.data

    if data == 'uploadfile':
        admin_state = "upload"
        query.edit_message_text(
            "📤 لطفاً فایل خود را ارسال کنید (هر نوع فایلی پذیرفته می‌شود).")
    elif data == 'replacefile':
        admin_state = "replace"
        query.edit_message_text(
            "🔄 لطفاً فایل جدید را ارسال کنید تا جایگزین شود.")
    elif data == 'deletefile':
        shared_files.clear()
        save_database(shared_files)
        query.edit_message_text("🗑️ تمام فایل‌ها و لینک‌های اشتراک حذف شدند.")
    elif data == 'listfiles':
        clean_expired_files()
        if not shared_files:
            query.edit_message_text("📋 لیست فایل‌ها خالی است.")
        else:
            message = "📋 لیست فایل‌های موجود:\n\n"
            for key, data_item in shared_files.items():
                expiry = "دائمی" if data_item['expiry'] is None else data_item[
                    'expiry'].strftime('%Y-%m-%d %H:%M:%S')
                message += f"🔹 شناسه: {key}\n⏳ انقضا: {expiry}\n\n"
            query.edit_message_text(message)
    elif data == 'addadmin':
        admin_state = "addadmin"
        query.edit_message_text(
            "➕ لطفاً آی‌دی کاربر جدید را به صورت عدد ارسال کنید:")
    elif data == 'removeadmin':
        admin_state = "removeadmin"
        query.edit_message_text(
            "➖ لطفاً آی‌دی کاربر مورد نظر برای حذف را به صورت عدد ارسال کنید:")
    # پردازش دکمه‌های لینک اشتراک
    elif data.startswith("perm_"):
        file_key = data.split("_", 1)[1]
        share_link = f"https://t.me/{BOT_USERNAME}?start={file_key}"
        query.edit_message_text(f"🔗 لینک اشتراک دائمی:\n{share_link}")
    elif data.startswith("timed_"):
        file_key = data.split("_", 1)[1]
        admin_state = ("set_timed_hours", file_key)
        query.edit_message_text("⏳ لطفاً تعداد ساعت اعتبار لینک را وارد کنید:")


def file_handler(update: Update, context: CallbackContext):
    global admin_state
    if update.effective_chat.id not in admins:
        return
    if admin_state in ["upload", "replace"]:
        file_obj = None
        if update.message.document:
            file_obj = update.message.document
        elif update.message.photo:
            file_obj = update.message.photo[-1]
        elif update.message.video:
            file_obj = update.message.video
        elif update.message.audio:
            file_obj = update.message.audio
        elif update.message.voice:
            file_obj = update.message.voice
        elif update.message.video_note:
            file_obj = update.message.video_note

        if file_obj:
            share_link, unique_id = generate_share_link(
                file_obj.file_id, BOT_USERNAME)
            shared_files[unique_id] = {
                'file_id': file_obj.file_id,
                'expiry': None,
                'upload_date': datetime.datetime.now()
            }
            save_database(shared_files)
            admin_state = None

            keyboard = [[
                InlineKeyboardButton("🔗 لینک اشتراک دائمی",
                                     callback_data=f'perm_{unique_id}')
            ],
                        [
                            InlineKeyboardButton(
                                "⏳ لینک اشتراک زمان دار",
                                callback_data=f'timed_{unique_id}')
                        ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text("✅ فایل با موفقیت ذخیره شد.\n\n" +
                                      f"🔗 لینک اشتراک: {share_link}\n\n" +
                                      "می‌توانید نوع لینک را تغییر دهید:",
                                      reply_markup=reply_markup)
        else:
            update.message.reply_text("❗ فایل قابل پردازش نیست.")


def text_handler(update: Update, context: CallbackContext):
    global admin_state
    if update.effective_chat.id not in admins:
        return
    text = update.message.text.strip()

    # بررسی حالت تنظیم لینک زمان دار با داشتن کلید فایل به صورت tuple
    if isinstance(admin_state, tuple) and admin_state[0] == "set_timed_hours":
        file_key = admin_state[1]
        try:
            hours = int(text)
            expiry_time = datetime.datetime.now() + datetime.timedelta(
                hours=hours)
            if file_key in shared_files:
                shared_files[file_key]['expiry'] = expiry_time
                save_database(shared_files)
                share_link = f"https://t.me/{BOT_USERNAME}?start={file_key}"
                expiry_str = expiry_time.strftime('%Y-%m-%d %H:%M:%S')
                update.message.reply_text(
                    f"✅ لینک اشتراک زمان‌دار ساخته شد:\n{share_link}\n\n⏳ معتبر تا: {expiry_str}"
                )
            else:
                update.message.reply_text("❗ فایل مورد نظر یافت نشد.")
        except (ValueError, Exception):
            update.message.reply_text("❗ خطا در تنظیم زمان انقضا.")
        admin_state = None

    elif admin_state == "addadmin":
        try:
            new_admin = int(text)
            if new_admin in admins:
                update.message.reply_text("ℹ️ این کاربر از قبل ادمین است.")
            else:
                admins.append(new_admin)
                save_admins(admins)
                update.message.reply_text(
                    f"✅ کاربر با آی‌دی {new_admin} به عنوان ادمین اضافه شد.")
        except ValueError:
            update.message.reply_text("❗ آی‌دی وارد شده معتبر نیست.")
        admin_state = None

    elif admin_state == "removeadmin":
        try:
            rem_admin = int(text)
            if rem_admin not in admins:
                update.message.reply_text("ℹ️ این کاربر ادمین نیست.")
            elif rem_admin == PRIMARY_ADMIN:
                update.message.reply_text(
                    "❌ نمی‌توانید ادمین اصلی را حذف کنید.")
            else:
                admins.remove(rem_admin)
                save_admins(admins)
                update.message.reply_text(
                    f"✅ کاربر با آی‌دی {rem_admin} از لیست ادمین‌ها حذف شد.")
        except ValueError:
            update.message.reply_text("❗ آی‌دی وارد شده معتبر نیست.")
        admin_state = None


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(
        MessageHandler(
            Filters.document | Filters.photo | Filters.video | Filters.audio
            | Filters.voice | Filters.video_note, file_handler))
    dp.add_handler(
        MessageHandler(Filters.text & (~Filters.command), text_handler))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
