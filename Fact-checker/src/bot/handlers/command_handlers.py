"""
هندلرهای مربوط به دستورات تلگرام.
این ماژول شامل هندلرهای مختلف برای پردازش دستورات تلگرام است.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from ...core.services.fact_checker import FactCheckerService
from ...core.services.reporting_service import ReportingService
from ...utils.helpers import get_logger
from ..keyboards.inline_keyboards import get_main_menu_keyboard

logger = get_logger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    پردازش دستور شروع
    """
    try:
        user = update.effective_user
        context.user_data['language'] = 'fa'  # زبان پیش‌فرض فارسی

        welcome_text = (
            f"سلام {user.first_name} 👋\n\n"
            "به ربات فکت‌چکر خوش آمدید!\n"
            "من می‌توانم به شما در راستی‌آزمایی اخبار و اطلاعات کمک کنم.\n\n"
            "برای شروع می‌توانید:\n"
            "• متن خبر یا ادعا را برای من ارسال کنید\n"
            "• تصویر یا ویدیو موردنظر را بفرستید\n"
            "• لینک مطلب را به اشتراک بگذارید\n"
            "• فایل صوتی حاوی ادعا را ارسال کنید\n\n"
            "از منوی زیر گزینه مورد نظر را انتخاب کنید:"
        )

        await update.message.reply_text(
            text=welcome_text,
            reply_markup=get_main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text(
            "متأسفانه در پردازش درخواست شما مشکلی پیش آمد. لطفاً دوباره تلاش کنید."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    پردازش دستور راهنما
    """
    try:
        help_text = (
            "🔍 راهنمای استفاده از ربات فکت‌چکر:\n\n"
            "1️⃣ ارسال متن:\n"
            "متن خبر یا ادعای مورد نظر را مستقیماً ارسال کنید\n\n"
            "2️⃣ ارسال تصویر:\n" 
            "تصویر را به همراه کپشن توضیحی ارسال کنید\n\n"
            "3️⃣ ارسال لینک:\n"
            "لینک خبر یا مطلب را ارسال کنید\n\n"
            "4️⃣ ارسال صوت و ویدیو:\n"
            "فایل صوتی یا ویدیویی حاوی ادعا را ارسال کنید\n\n"
            "5️⃣ دریافت نتایج:\n"
            "پس از بررسی، نتیجه به همراه منابع ارسال می‌شود\n\n"
            "🔸 سایر دستورات:\n"
            "/settings - تنظیمات\n"
            "/stats - آمار بررسی‌ها\n"
            "/lang - تغییر زبان\n"
            "/about - درباره ربات"
        )

        await update.message.reply_text(help_text)

    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        await update.message.reply_text(
            "متأسفانه در نمایش راهنما مشکلی پیش آمد. لطفاً دوباره تلاش کنید."
        )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    پردازش دستور تنظیمات
    """
    try:
        settings_text = (
            "⚙️ تنظیمات ربات:\n\n"
            "🔹 زبان فعلی: فارسی\n"
            "🔹 فرمت گزارش: متنی\n"
            "🔹 دریافت اعلان: فعال\n\n"
            "برای تغییر هر کدام از موارد بالا از دکمه‌های زیر استفاده کنید:"
        )

        # TODO: اضافه کردن کیبورد تنظیمات

        await update.message.reply_text(settings_text)

    except Exception as e:
        logger.error(f"Error in settings command: {str(e)}")
        await update.message.reply_text(
            "متأسفانه در نمایش تنظیمات مشکلی پیش آمد. لطفاً دوباره تلاش کنید."
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    پردازش دستور آمار
    """
    try:
        # دریافت آمار از سرویس فکت‌چکر
        fact_checker = FactCheckerService()
        stats = await fact_checker.get_user_statistics(update.effective_user.id)

        stats_text = (
            "📊 آمار بررسی‌های شما:\n\n"
            f"🔸 تعداد کل بررسی‌ها: {stats['total_checks']}\n"
            f"🔸 تأیید شده: {stats['verified_count']}\n"
            f"🔸 رد شده: {stats['false_count']}\n"
            f"🔸 نامشخص: {stats['unknown_count']}\n\n"
            f"📅 تاریخ عضویت: {stats['join_date']}\n"
            f"⌛️ آخرین فعالیت: {stats['last_activity']}"
        )

        await update.message.reply_text(stats_text)

    except Exception as e:
        logger.error(f"Error in stats command: {str(e)}")
        await update.message.reply_text(
            "متأسفانه در دریافت آمار مشکلی پیش آمد. لطفاً دوباره تلاش کنید."
        )

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    پردازش دستور تغییر زبان
    """
    try:
        lang_text = (
            "🌐 انتخاب زبان ربات:\n\n"
            "زبان فعلی: فارسی\n\n"
            "برای تغییر زبان یکی از گزینه‌های زیر را انتخاب کنید:"
        )

        # TODO: اضافه کردن کیبورد انتخاب زبان

        await update.message.reply_text(lang_text)

    except Exception as e:
        logger.error(f"Error in language command: {str(e)}")
        await update.message.reply_text(
            "متأسفانه در تغییر زبان مشکلی پیش آمد. لطفاً دوباره تلاش کنید."
        )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    پردازش دستور درباره ربات
    """
    try:
        about_text = (
            "ℹ️ درباره ربات فکت‌چکر\n\n"
            "این ربات با هدف کمک به راستی‌آزمایی اخبار و اطلاعات طراحی شده است."
            " با استفاده از هوش مصنوعی و منابع معتبر، صحت اطلاعات را بررسی می‌کند.\n\n"
            "🔸 قابلیت‌های اصلی:\n"
            "• تحلیل متن، تصویر و ویدیو\n"
            "• بررسی منابع معتبر خبری\n"
            "• تشخیص اخبار جعلی\n"
            "• ارائه گزارش تحلیلی\n\n"
            "🔗 وب‌سایت پروژه: factchecker.ir\n"
            "📧 ایمیل پشتیبانی: support@factchecker.ir\n\n"
            "نسخه: 1.0.0"
        )

        await update.message.reply_text(about_text)

    except Exception as e:
        logger.error(f"Error in about command: {str(e)}")
        await update.message.reply_text(
            "متأسفانه در نمایش اطلاعات ربات مشکلی پیش آمد. لطفاً دوباره تلاش کنید."
        )

def register_command_handlers(application):
    """
    ثبت تمام هندلرهای دستورات
    """
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('settings', settings_command))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CommandHandler('lang', lang_command))
    application.add_handler(CommandHandler('about', about_command))
