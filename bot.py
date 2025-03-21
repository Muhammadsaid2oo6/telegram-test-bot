import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScope
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
import re
from datetime import datetime

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store tests temporarily (in production, use a database)
tests = {}
open_tests = {}
user_names = {}
students = {}  # Store student information
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Add your Telegram ID in .env file

class Student:
    def __init__(self, user_id, full_name):
        self.user_id = user_id
        self.full_name = full_name
        self.test_results = {}  # {test_code: {score: float, date: datetime}}
        self.registration_date = datetime.now()

class Test:
    def __init__(self, code, creator_id):
        self.code = code
        self.creator_id = creator_id
        self.attempts = {}  # user_id: number_of_attempts
        self.is_scored = False
        self.max_score = 100
        self.date_created = datetime.now()

class OpenTest:
    def __init__(self, code, creator_id, questions):
        self.code = code
        self.creator_id = creator_id
        self.questions = questions
        self.attempts = {}  # user_id: {question: answer}

async def setup_commands(application: Application):
    """Setup bot commands that appear in the menu."""
    # Only admin gets commands
    if ADMIN_ID:
        admin_commands = [
            BotCommand("start", "Botni ishga tushirish"),
            BotCommand("edit", "Ismni o'zgartirish uchun bosing"),
        ]
        chat_scope = BotCommandScope.CHAT
        await application.bot.set_my_commands(
            admin_commands,
            scope={"type": chat_scope, "chat_id": ADMIN_ID}
        )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send info about the bot when /info is issued."""
    await update.message.reply_text(
        "Bot ishlash haqida ma'lumotlar:\n\n"
        "1. Oddiy test - javoblar kalit bilan tekshiriladi\n"
        "2. Ochiq test - savollarga erkin javob beriladi\n"
        "3. Balli test - har bir to'g'ri javob uchun ball beriladi\n\n"
        "❗️ Botning barcha imkoniyatlari bilan tanishish uchun /start ni bosing"
    )

async def testlarim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's tests when /testlarim is issued."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat administrator uchun!")
        return

    user_tests = [code for code, test in tests.items() if test.creator_id == ADMIN_ID]
    user_open_tests = [code for code, test in open_tests.items() if test.creator_id == ADMIN_ID]
    
    if not user_tests and not user_open_tests:
        await update.message.reply_text("❌ Siz hali test yaratmagansiz!")
        return

    response = "📚 Sizning testlaringiz:\n\n"
    if user_tests:
        response += "📝 Oddiy testlar:\n"
        for code in user_tests:
            test = tests[code]
            response += f"📌 Test kodi: {code}\n"
            response += f"✅ Javoblar soni: {len(test.attempts)} ta\n"
            response += f"📊 Ball: {test.max_score if test.is_scored else 'Oddiy'}\n"
            response += f"📅 Sana: {test.date_created.strftime('%Y-%m-%d %H:%M')}\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n"
    
    if user_open_tests:
        response += "\n📖 Ochiq testlar:\n"
        for code in user_open_tests:
            test = open_tests[code]
            response += f"📌 Test kodi: {code}\n"
            response += f"❓ Savollar soni: {len(test.questions)} ta\n"
            response += f"✅ Javoblar soni: {len(test.attempts)} ta\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n"
    
    await update.message.reply_text(response)

async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /edit command."""
    await update.message.reply_text(
        "Ismingizni o'zgartirish uchun quyidagi formatda yuboring:\n"
        "name:Yangi ismingiz"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Skip registration check for admin
    if user_id != ADMIN_ID:
        # Check if user is registered
        if user_id not in students:
            await update.message.reply_text(
                "👋 Xush kelibsiz!\n\n"
                "📝 Ism familiyangizni kiriting"
            )
            await update.message.reply_text(
                "Misol: Muhammad hasa"
            )
            return

    if user_id == ADMIN_ID:
        keyboard = [
            [
                InlineKeyboardButton("📝 Testga qanday javob beriladi?", callback_data="check_test"),
                InlineKeyboardButton("📋 Yangi test qanday yaratiladi?", callback_data="create_test"),
            ],
            [
                InlineKeyboardButton("🎯 Botda test ishlash va yaratish(+video)", callback_data="video_tutorial")
            ]
        ]
    else:
        # For regular users, only show test answering option
        keyboard = [
            [InlineKeyboardButton("📝 Testga qanday javob beriladi?", callback_data="check_test")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "👤 Hurmatli Administrator!\n\n"
            "❗️ Botning barcha imkoniyatlari bilan tanishish uchun pastdagi botda test ishlash va yaratish(+video) tugmasini bosing",
            reply_markup=reply_markup
        )
    else:
        student = students[user_id]
        await update.message.reply_text(
            f"👤 Hurmatli {student.full_name}\n\n"
            "❗️ Test ishlash uchun quyidagi tugmani bosing",
            reply_markup=reply_markup
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id == ADMIN_ID:
        if query.data == "create_test":
            keyboard = [
                [InlineKeyboardButton("❌ Nechta topgani berilishi❌", callback_data="score_info")],
                [InlineKeyboardButton("📊 Ball qo'shish📊", callback_data="add_score")],
                [InlineKeyboardButton("📚 Test turlari haqida", callback_data="test_types")],
                [InlineKeyboardButton("📝 Test ma'lumoti📝", callback_data="test_info")],
                [InlineKeyboardButton("📋 Test ma'lumoti(saytdagi jadval)📋", callback_data="test_table")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                "❗️Yangi test yaratish\n\n"
                "✅Test nomini kiritib + (plus) belgisini qo'yasiz va barcha kalitni kiritasiz.\n\n"
                "✍️Misol uchun:\n"
                "Yangitest+abcdabcdabcd...  yoki\n"
                "Yangitest+1a2b3c4d5a6b7c...\n\n"
                "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi.",
                reply_markup=reply_markup
            )
        elif query.data == "check_test":
            await query.message.reply_text(
                "❗️Testga javob berish\n\n"
                "✅Test kodini kiritib * (yulduzcha) belgisini qo'yasiz va barcha kalitlarni kiritasiz.\n\n"
                "✍️Misol uchun:\n"
                "123*abcdabcdabcd...  yoki\n"
                "123*1a2b3c4d5a6b7c...\n\n"
                "⁉️Testga faqat bir marta javob berish mumkin.\n\n"
                "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
            )
        elif query.data == "video_tutorial":
            await query.message.reply_text(
                "https://abot.uz/mybots/Test_bot_yaratish_bot/testinfo.php?data=bWFqYnVyaXlfeGlsYldWRjBXMWhkR2lyWVh5MDl0Ym1GdGVRPT0="
            )
        elif query.data == "test_types":
            await query.message.reply_text(
                "Test turlari:\n"
                "1. Oddiy test - javoblar kalit bilan tekshiriladi\n"
                "2. Ochiq test - savollarga erkin javob beriladi\n"
                "3. Balli test - har bir to'g'ri javob uchun ball beriladi"
            )
        elif query.data == "score_info":
            await query.message.reply_text(
                "❌ Nechta topgani berilishi❌\n\n"
                "Test yaratuvchisi test natijalarini ko'rishi mumkin"
            )
        elif query.data == "add_score":
            await query.message.reply_text(
                "📊 Ball qo'shish uchun:\n"
                "score:test_kodi:maksimal_ball\n"
                "Misol: score:123:100"
            )
        elif query.data == "test_info":
            await query.message.reply_text(
                "📝 Test ma'lumoti\n\n"
                "Test yaratish uchun:\n"
                "test_nomi+javoblar\n"
                "Misol: 5-sinf+abcdabcd"
            )
        elif query.data == "test_table":
            await query.message.reply_text(
                "📋 Test ma'lumoti (saytdagi jadval)\n\n"
                "Saytda test natijalarini jadval ko'rinishida ko'rish mumkin"
            )
    else:
        if query.data == "check_test":
            await query.message.reply_text(
                "❗️Testga javob berish\n\n"
                "✅Test kodini kiritib * (yulduzcha) belgisini qo'yasiz va barcha kalitlarni kiritasiz.\n\n"
                "✍️Misol uchun:\n"
                "123*abcdabcdabcd...  yoki\n"
                "123*1a2b3c4d5a6b7c...\n\n"
                "⁉️Testga faqat bir marta javob berish mumkin.\n\n"
                "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
            )

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle student registration."""
    await update.message.reply_text(
        "📝 O'quvchi sifatida ro'yxatdan o'tish uchun quyidagi formatda ma'lumot yuboring:\n\n"
        "register:Ism Familiya\n\n"
        "Misol: register:Jahongir Rahimov"
    )

async def students_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all registered students (admin only)."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat administrator uchun!")
        return

    if not students:
        await update.message.reply_text("Hozircha ro'yxatdan o'tgan o'quvchilar yo'q!")
        return

    response = "📚 Ro'yxatdan o'tgan o'quvchilar:\n\n"
    for student in students.values():
        response += f"👤 {student.full_name}\n"
        response += f"📱 ID: {student.user_id}\n"
        response += f"📅 Sana: {student.registration_date.strftime('%Y-%m-%d')}\n"
        response += "➖➖➖➖➖➖➖➖➖➖\n"

    await update.message.reply_text(response)

async def scores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all test scores (admin only)."""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Bu buyruq faqat administrator uchun!")
        return

    if not students:
        await update.message.reply_text("Hozircha natijalar mavjud emas!")
        return

    response = "📊 Barcha test natijalari:\n\n"
    has_results = False
    
    # Group results by test code first
    test_results = {}
    for student in students.values():
        for test_code, result in student.test_results.items():
            if test_code not in test_results:
                test_results[test_code] = []
            test_results[test_code].append({
                "student": student,
                "score": result["score"],
                "date": result["date"]
            })

    # Display results grouped by test
    for test_code, results in test_results.items():
        has_results = True
        test = tests.get(test_code)
        max_score = test.max_score if test and test.is_scored else 100
        
        response += f"📝 Test #{test_code} natijalari:\n"
        # Sort results by score in descending order
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
        
        for idx, result in enumerate(sorted_results, 1):
            student = result["student"]
            score = result["score"]
            date = result["date"]
            response += f"{idx}. {student.full_name}: {score:.1f}/{max_score} ball"
            response += f" ({date.strftime('%Y-%m-%d %H:%M')})\n"
        response += "➖➖➖➖➖➖➖➖➖➖\n\n"
    
    if not has_results:
        await update.message.reply_text("Hozircha test natijalari mavjud emas!")
        return

    await update.message.reply_text(response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    message = update.message.text
    user_id = update.effective_user.id

    # Check if user is registered before allowing other actions (skip for admin)
    if user_id != ADMIN_ID and user_id not in students:
        # Try to register user with direct name input
        full_name = message.strip()
        
        if not full_name:
            await update.message.reply_text("❌ Ism kiritilmagan!")
            return
            
        if "+" in full_name or "*" in full_name or ":" in full_name:
            await update.message.reply_text(
                "❌ Ism noto'g'ri formatda kiritildi!\n\n"
                "📝 Ism familiyangizni kiriting\n\n"
                "Misol: Muhammad hasa"
            )
            return
            
        students[user_id] = Student(user_id, full_name)
        
        # Send welcome message after successful registration
        keyboard = [
            [InlineKeyboardButton("📝 Testga qanday javob beriladi?", callback_data="check_test")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👤 Hurmatli {full_name}\n\n"
            "❗️ Test ishlash uchun quyidagi tugmani bosing",
            reply_markup=reply_markup
        )
        return

    # For regular users, only allow test answering
    if user_id != ADMIN_ID:
        if "*" in message:
            try:
                test_code, answer = message.split("*", 1)
                test_code = test_code.strip()
                answer = answer.strip().lower()

                if test_code not in tests:
                    await update.message.reply_text("❌ Bunday test mavjud emas!")
                    return

                test = tests[test_code]
                
                # Check if the test was created by admin
                if test.creator_id != ADMIN_ID:
                    await update.message.reply_text("❌ Bu test mavjud emas!")
                    return

                if user_id in test.attempts:
                    await update.message.reply_text("❌ Siz bu testga allaqachon javob bergansiz!")
                    return

                correct_key = test.code
                if len(answer) != len(correct_key):
                    await update.message.reply_text("❌ Javob uzunligi noto'g'ri!")
                    return

                # Create detailed feedback for each answer
                feedback = "📝 Test natijalari:\n\n"
                correct_count = 0
                for idx, (user_ans, correct_ans) in enumerate(zip(answer, correct_key), 1):
                    is_correct = user_ans == correct_ans
                    if is_correct:
                        correct_count += 1
                        feedback += f"{idx}. ✅ {user_ans.upper()}\n"
                    else:
                        feedback += f"{idx}. ❌ {user_ans.upper()} (To'g'ri javob: {correct_ans.upper()})\n"

                percentage = (correct_count / len(correct_key)) * 100

                if test.is_scored:
                    score = (percentage / 100) * test.max_score
                    test.attempts[user_id] = score
                    students[user_id].test_results[test_code] = {
                        "score": score,
                        "date": datetime.now()
                    }
                    feedback += f"\n📊 Umumiy natija: {correct_count}/{len(correct_key)} ({percentage:.1f}%)\n"
                    feedback += f"💯 Ball: {score:.1f}/{test.max_score}"
                else:
                    test.attempts[user_id] = percentage
                    students[user_id].test_results[test_code] = {
                        "score": percentage,
                        "date": datetime.now()
                    }
                    feedback += f"\n📊 Umumiy natija: {correct_count}/{len(correct_key)} ({percentage:.1f}%)"

                await update.message.reply_text(feedback)
            except Exception as e:
                await update.message.reply_text(
                    "❗️Testga javob berish\n\n"
                    "✅Test kodini kiritib * (yulduzcha) belgisini qo'yasiz va barcha kalitlarni kiritasiz.\n\n"
                    "✍️Misol uchun:\n"
                    "123*abcdabcdabcd...  yoki\n"
                    "123*1a2b3c4d5a6b7c...\n\n"
                    "⁉️Testga faqat bir marta javob berish mumkin.\n\n"
                    "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
                )
        else:
            await update.message.reply_text(
                "❗️Testga javob berish\n\n"
                "✅Test kodini kiritib * (yulduzcha) belgisini qo'yasiz va barcha kalitlarni kiritasiz.\n\n"
                "✍️Misol uchun:\n"
                "123*abcdabcdabcd...  yoki\n"
                "123*1a2b3c4d5a6b7c...\n\n"
                "⁉️Testga faqat bir marta javob berish mumkin.\n\n"
                "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
            )
        return

    # Admin functionality remains unchanged
    # Handle name editing
    if message.startswith("name:"):
        new_name = message[5:].strip()
        if new_name:
            user_names[user_id] = new_name
            await update.message.reply_text(
                f"✅ Ismingiz muvaffaqiyatli o'zgartirildi: {new_name}"
            )
        return

    # Handle test scoring
    if message.startswith("score:"):
        try:
            _, test_code, max_score = message.split(":")
            max_score = int(max_score)
            if test_code in tests:
                test = tests[test_code]
                if test.creator_id == user_id:
                    test.is_scored = True
                    test.max_score = max_score
                    await update.message.reply_text(
                        f"✅ Test {max_score} ballik qilib o'zgartirildi"
                    )
                else:
                    await update.message.reply_text(
                        "❌ Siz faqat o'zingiz yaratgan testlarni balli qila olasiz"
                    )
            else:
                await update.message.reply_text("❌ Bunday test mavjud emas")
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri format!")
        return

    # Handle open test creation
    if message.startswith("open+"):
        try:
            test_name, *questions = message[5:].strip().split("\n")
            if questions:
                test_code = f"O{len(open_tests) + 1:03d}"
                open_tests[test_code] = OpenTest(test_code, user_id, questions)
                await update.message.reply_text(
                    f"✅ Ochiq test yaratildi!\n"
                    f"Test kodi: {test_code}\n"
                    f"Savollar soni: {len(questions)}"
                )
            else:
                await update.message.reply_text("❌ Savollar kiritilmagan!")
        except Exception:
            await update.message.reply_text("❌ Noto'g'ri format!")
        return

    # Handle open test answers
    if message.startswith("answer:"):
        try:
            test_code = message[7:].split("\n")[0].strip()
            answers = message[7:].split("\n")[1:]
            
            if test_code in open_tests:
                test = open_tests[test_code]
                if user_id in test.attempts:
                    await update.message.reply_text("❌ Siz bu testga allaqachon javob bergansiz!")
                    return
                
                if len(answers) != len(test.questions):
                    await update.message.reply_text("❌ Javoblar soni savollar soniga teng emas!")
                    return
                
                test.attempts[user_id] = dict(zip(test.questions, answers))
                await update.message.reply_text("✅ Javoblaringiz qabul qilindi!")
            else:
                await update.message.reply_text("❌ Bunday test mavjud emas!")
        except Exception:
            await update.message.reply_text("❌ Noto'g'ri format!")
        return

    # Handle regular test creation
    if "+" in message:
        try:
            test_name, test_key = message.split("+", 1)
            test_key = test_key.strip().lower()
            
            if not re.match("^[a-zA-Z0-9]+$", test_key):
                await update.message.reply_text(
                    "❗️Yangi test yaratish\n\n"
                    "✅Test nomini kiritib + (plus) belgisini qo'yasiz va barcha kalitni kiritasiz.\n\n"
                    "✍️Misol uchun:\n"
                    "Yangitest+abcdabcdabcd...  yoki\n"
                    "Yangitest+1a2b3c4d5a6b7c...\n\n"
                    "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
                )
                return

            test_code = f"{len(tests) + 1:03d}"
            tests[test_code] = Test(test_key, user_id)
            
            await update.message.reply_text(
                f"✅ Test muvaffaqiyatli yaratildi!\n"
                f"Test kodi: {test_code}\n"
                f"Uzunlik: {len(test_key)} ta belgi"
            )
        except Exception:
            await update.message.reply_text(
                "❗️Yangi test yaratish\n\n"
                "✅Test nomini kiritib + (plus) belgisini qo'yasiz va barcha kalitni kiritasiz.\n\n"
                "✍️Misol uchun:\n"
                "Yangitest+abcdabcdabcd...  yoki\n"
                "Yangitest+1a2b3c4d5a6b7c...\n\n"
                "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
            )
            return

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Setup commands menu
    application.post_init = setup_commands

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 