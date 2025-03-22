import os
import logging
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScope
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
import re
from datetime import datetime
import asyncio

# Load environment variables
load_dotenv(override=True)  # Force reload of environment variables

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Data storage files
TESTS_FILE = "data/tests.json"
STUDENTS_FILE = "data/students.json"

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Store tests temporarily (in production, use a database)
tests = {}
user_names = {}
students = {}  # Store student information
ADMIN_IDS = [int(os.getenv("ADMIN_ID", "0"))]  # List of admin IDs

# Verify token is loaded
token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise ValueError("No token found in environment variables. Check your .env file.")

class Student:
    def __init__(self, user_id, full_name):
        self.user_id = user_id
        self.full_name = full_name
        self.test_results = {}  # {test_code: {score: float, date: datetime}}
        self.registration_date = datetime.now()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "full_name": self.full_name,
            "test_results": {
                code: {
                    "score": result["score"],
                    "date": result["date"].isoformat()
                }
                for code, result in self.test_results.items()
            },
            "registration_date": self.registration_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        student = cls(data["user_id"], data["full_name"])
        student.test_results = {
            code: {
                "score": result["score"],
                "date": datetime.fromisoformat(result["date"])
            }
            for code, result in data["test_results"].items()
        }
        student.registration_date = datetime.fromisoformat(data["registration_date"])
        return student

class Test:
    def __init__(self, code, creator_id, name="Test"):
        self.code = code
        self.creator_id = creator_id
        self.name = name
        self.attempts = {}  # user_id: answer
        self.date_created = datetime.now()
        self.is_scored = False
        self.max_score = 0

    def to_dict(self):
        return {
            "code": self.code,
            "creator_id": self.creator_id,
            "name": self.name,
            "attempts": self.attempts,
            "date_created": self.date_created.strftime("%Y-%m-%d %H:%M:%S"),
            "is_scored": self.is_scored,
            "max_score": self.max_score
        }

    @classmethod
    def from_dict(cls, data):
        test = cls(data["code"], data["creator_id"], data.get("name", "Test"))
        test.attempts = data["attempts"]
        test.date_created = datetime.strptime(data["date_created"], "%Y-%m-%d %H:%M:%S")
        test.is_scored = data.get("is_scored", False)
        test.max_score = data.get("max_score", 0)
        return test

def save_data():
    """Save all data to JSON files."""
    try:
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            logger.info("Created data directory")

        # Save tests
        with open(TESTS_FILE, 'w', encoding='utf-8') as f:
            test_data = {code: test.to_dict() for code, test in tests.items()}
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(test_data)} tests to {TESTS_FILE}")
        
        # Save students
        with open(STUDENTS_FILE, 'w', encoding='utf-8') as f:
            student_data = {str(user_id): student.to_dict() for user_id, student in students.items()}
            json.dump(student_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(student_data)} students to {STUDENTS_FILE}")

        logger.info("All data saved successfully")
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        raise e  # Re-raise the exception to ensure it's not silently ignored

def load_data():
    """Load all data from JSON files."""
    global tests, students
    
    try:
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            logger.info("Created data directory")
        
        # Load tests
        if os.path.exists(TESTS_FILE):
            with open(TESTS_FILE, 'r', encoding='utf-8') as f:
                tests_data = json.load(f)
                tests = {code: Test.from_dict(data) for code, data in tests_data.items()}
                logger.info(f"Loaded {len(tests)} tests from {TESTS_FILE}")
        
        # Load students
        if os.path.exists(STUDENTS_FILE):
            with open(STUDENTS_FILE, 'r', encoding='utf-8') as f:
                students_data = json.load(f)
                students = {int(user_id): Student.from_dict(data) for user_id, data in students_data.items()}
                logger.info(f"Loaded {len(students)} students from {STUDENTS_FILE}")

        logger.info("All data loaded successfully")
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise e  # Re-raise the exception to ensure it's not silently ignored

async def setup_commands(application: Application):
    """Setup bot commands that appear in the menu."""
    # Commands for all users
    common_commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("info", "Bot haqida ma'lumot"),
        BotCommand("edit", "Ismni o'zgartirish"),
    ]
    
    # Additional commands for admins
    admin_commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("testlarim", "Testlaringiz haqida ma'lumotlar"),
        BotCommand("students", "O'quvchilar ro'yxati"),
        BotCommand("scores", "Barcha natijalar"),
        BotCommand("info", "Bot haqida ma'lumot"),
    ]
    
    try:
        # Set commands for all users
        await application.bot.set_my_commands(common_commands)
        
        # Set admin commands for each admin
        for admin_id in ADMIN_IDS:
            try:
                await application.bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScope.CHAT(chat_id=admin_id)
                )
            except Exception as e:
                logger.error(f"Failed to set admin commands for {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to set commands: {e}")

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
    
    # Only admins can use this command
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bu buyruq faqat administrator uchun!")
        return

    user_tests = [code for code, test in tests.items() if test.creator_id in ADMIN_IDS]
    
    if not user_tests:
        await update.message.reply_text("❌ Siz hali test yaratmagansiz!")
        return

    response = "📚 Sizning testlaringiz:\n\n"
    if user_tests:
        response += "📝 Testlar:\n"
        for code in user_tests:
            test = tests[code]
            response += f"📌 Test kodi: {code}\n"
            response += f"📋 Test nomi: {test.name if hasattr(test, 'name') else 'Test'}\n"
            response += f"✅ Javoblar soni: {len(test.attempts)} ta\n"
            response += f"🔑 To'g'ri javoblar: {test.code.upper()}\n"
            response += f"📅 Sana: {test.date_created.strftime('%Y-%m-%d %H:%M')}\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n"
    
    await update.message.reply_text(response)

async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /edit command."""
    user_id = update.effective_user.id
    
    # Don't allow admins to edit their names
    if user_id in ADMIN_IDS:
        await update.message.reply_text("❌ Administrator ismini o'zgartira olmaydi!")
        return
        
    if user_id not in students:
        await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz!")
        return
    
    context.user_data['awaiting_name_change'] = True
    await update.message.reply_text(
        "📝 Ismingizni o'zgartirish uchun quyidagi formatda yuboring:\n\n"
        "Yangi ismingiz\n\n"
        "✍️ Misol: Muhammadsaid Hasanboyev"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Skip registration check for admins
    if user_id not in ADMIN_IDS:
        # Check if user is registered
        if user_id not in students:
            await update.message.reply_text(
                "👋 Xush kelibsiz!\n\n"
                "📝 Ism familiyangizni kiriting\n\n"
                "Misol: Muhammadsaid Hasanboyev"
            )
            return

    if user_id in ADMIN_IDS:
        keyboard = [
            [
                InlineKeyboardButton("📝 Testga qanday javob beriladi?", callback_data="check_test"),
                InlineKeyboardButton("📋 Yangi test qanday yaratiladi?", callback_data="create_test"),
            ]
        ]
    else:
        # For regular users, only show test answering option
        keyboard = [
            [InlineKeyboardButton("📝 Testga qanday javob beriladi?", callback_data="check_test")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if user_id in ADMIN_IDS:
        await update.message.reply_text(
            "👤 Hurmatli Administrator!\n\n"
            "❗️ Botning barcha imkoniyatlari bilan tanishish uchun quyidagi tugmalarni bosing",
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

    if user_id in ADMIN_IDS:
        if query.data == "create_test":
            await query.message.reply_text(
                "❗️Yangi test yaratish\n\n"
                "✅Test nomini kiritib + (plus) belgisini qo'yasiz va barcha kalitni kiritasiz.\n\n"
                "✍️Misol uchun:\n"
                "Yangitest+abcdabcdabcd...  yoki\n"
                "Yangitest+1a2b3c4d5a6b7c...\n\n"
                "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
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
    if update.effective_user.id not in ADMIN_IDS:
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
    
    if user_id not in ADMIN_IDS:
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
        if not test:
            continue
            
        max_score = test.max_score if test.is_scored else 100
        correct_key = test.code.lower()  # Get correct answers
        
        response += f"📝 Test #{test_code} natijalari:\n"
        response += f"✅ To'g'ri javoblar: {correct_key}\n\n"
        
        # Sort results by score in descending order
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
        
        for idx, result in enumerate(sorted_results, 1):
            student = result["student"]
            score = result["score"]
            date = result["date"]
            student_answer = test.attempts.get(student.user_id, "").lower()
            
            response += f"{idx}. {student.full_name}:\n"
            response += f"📊 Ball: {score:.1f}/{max_score}\n"
            response += f"📅 Sana: {date.strftime('%Y-%m-%d %H:%M')}\n"
            
            # Show detailed answer feedback
            if student_answer:
                response += "📝 Javoblar tahlili:\n"
                for i, (user_ans, correct_ans) in enumerate(zip(student_answer, correct_key), 1):
                    if user_ans == correct_ans:
                        response += f"{i}) ✅ {user_ans.upper()}\n"
                    else:
                        response += f"{i}) ❌ {user_ans.upper()} → {correct_ans.upper()}\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n\n"
    
    if not has_results:
        await update.message.reply_text("Hozircha test natijalari mavjud emas!")
        return

    # Split long messages if needed
    if len(response) > 4096:
        parts = [response[i:i+4096] for i in range(0, len(response), 4096)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(response)

def validate_name(name: str) -> tuple[bool, str]:
    """Validate the name format."""
    # Remove extra spaces
    name = " ".join(name.split())
    
    # Check if name contains numbers
    if any(char.isdigit() for char in name):
        return False, "❌ Ism raqamlarni o'z ichiga olmasligi kerak!"
    
    # Check if name contains only letters and spaces
    if not all(char.isalpha() or char.isspace() for char in name):
        return False, "❌ Ism faqat harflardan iborat bo'lishi kerak!"
    
    # Check if name has exactly two parts (first name and surname)
    parts = name.split()
    if len(parts) != 2:
        return False, "❌ Ism va familiyani kiriting!"
    
    # Check if each part is between 2 and 20 characters
    if any(len(part) < 2 or len(part) > 20 for part in parts):
        return False, "❌ Ism yoki familiya juda uzun yoki qisqa!"
    
    return True, name

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    message = update.message.text
    user_id = update.effective_user.id

    # Check if user is registered before allowing other actions (skip for admins)
    if user_id not in ADMIN_IDS and user_id not in students:
        # Try to register user with direct name input
        full_name = message.strip()
        
        if not full_name:
            await update.message.reply_text("❌ Ism kiritilmagan!")
            return
            
        if "+" in full_name or "*" in full_name or ":" in full_name:
            await update.message.reply_text(
                "❌ Ism noto'g'ri formatda kiritildi!\n\n"
                "📝 Ism familiyangizni kiriting\n\n"
                "Misol: Muhammadsaid Hasanboyev"
            )
            return
        
        # Validate name format
        is_valid, result = validate_name(full_name)
        if not is_valid:
            await update.message.reply_text(
                f"{result}\n\n"
                "📝 Ism familiyangizni kiriting\n\n"
                "Misol: Muhammadsaid Hasanboyev"
            )
            return

        # Create new student and store in database
        new_student = Student(user_id, result)
        students[user_id] = new_student
        save_data()  # Save after registration
        
        # Update user's profile name in Telegram
        try:
            await update.effective_chat.set_title(f"👤 Hurmatli {result}")
        except Exception:
            pass  # Ignore if we can't set chat title
        
        # Send welcome message after successful registration
        keyboard = [
            [InlineKeyboardButton("📝 Testga qanday javob beriladi?", callback_data="check_test")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👤 Hurmatli {result}\n\n"
            "❗️ Test ishlash uchun quyidagi tugmani bosing",
            reply_markup=reply_markup
        )
        return

    # Check if user is trying to change their name (after /edit command)
    if context.user_data.get('awaiting_name_change', False):
        new_name = message.strip()
        
        if not new_name:
            await update.message.reply_text("❌ Ism kiritilmagan!")
            return
            
        if "+" in new_name or "*" in new_name or ":" in new_name:
            await update.message.reply_text(
                "❌ Ism noto'g'ri formatda kiritildi!\n\n"
                "📝 Ism familiyangizni kiriting\n\n"
                "Misol: Muhammadsaid Hasanboyev"
            )
            return
        
        # Validate name format
        is_valid, result = validate_name(new_name)
        if not is_valid:
            await update.message.reply_text(
                f"{result}\n\n"
                "📝 Ism familiyangizni kiriting\n\n"
                "Misol: Muhammadsaid Hasanboyev"
            )
            return
        
        # Update the student's name
        if user_id in students:
            old_name = students[user_id].full_name
            students[user_id].full_name = result
            save_data()  # Save after name change
            await update.message.reply_text(f"✅ Ismingiz muvaffaqiyatli o'zgartirildi!\n\n{old_name} ➡️ {result}")
        else:
            await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz!")
        
        context.user_data['awaiting_name_change'] = False
        return

    # For regular users, only allow test answering
    if user_id not in ADMIN_IDS:
        if "*" in message:
            try:
                test_code, answer = message.split("*", 1)
                test_code = test_code.strip()
                answer = answer.strip().lower()

                if test_code not in tests:
                    await update.message.reply_text("❌ Bunday test mavjud emas!")
                    return

                test = tests[test_code]
                
                # Check if the test was created by an admin
                if test.creator_id not in ADMIN_IDS:
                    await update.message.reply_text("❌ Bu test mavjud emas!")
                    return

                if user_id in test.attempts:
                    await update.message.reply_text("❌ Siz bu testga allaqachon javob bergansiz!")
                    return

                correct_key = test.code
                if len(answer) != len(correct_key):
                    await update.message.reply_text("❌ Javob uzunligi noto'g'ri!")
                    return

                # Calculate score without showing individual answers
                student = students[user_id]  # Get student info for personalized message
                correct_count = sum(1 for user_ans, correct_ans in zip(answer, correct_key) if user_ans == correct_ans)
                total_questions = len(correct_key)
                percentage = (correct_count / total_questions) * 100

                # Store test result
                if test.is_scored:
                    score = (correct_count / total_questions) * test.max_score
                    student.test_results[test_code] = {"score": score, "date": datetime.now()}
                    feedback = f"📝 {student.full_name} ning test natijalari:\n\n"
                    feedback += f"✅ To'g'ri javoblar: {correct_count} ta\n"
                    feedback += f"📊 Ball: {score:.1f}/{test.max_score}\n"
                    feedback += f"💯 Foiz: {percentage:.1f}%"
                else:
                    student.test_results[test_code] = {"score": percentage, "date": datetime.now()}
                    feedback = f"📝 {student.full_name} ning test natijalari:\n\n"
                    feedback += f"✅ To'g'ri javoblar: {correct_count} ta\n"
                    feedback += f"💯 Foiz: {percentage:.1f}%"

                test.attempts[user_id] = answer
                save_data()  # Save after test submission
                await update.message.reply_text(feedback)

            except ValueError:
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
            student = students[user_id]  # Get student info for personalized message
            await update.message.reply_text(
                f"👤 Hurmatli {student.full_name}\n\n"
                "❗️Testga javob berish\n\n"
                "✅Test kodini kiritib * (yulduzcha) belgisini qo'yasiz va barcha kalitlarni kiritasiz.\n\n"
                "✍️Misol uchun:\n"
                "123*abcdabcdabcd...  yoki\n"
                "123*1a2b3c4d5a6b7c...\n\n"
                "⁉️Testga faqat bir marta javob berish mumkin.\n\n"
                "✅Katta(A) va kichik(a) harflar bir xil hisoblanadi."
            )
        return

    # Admin functionality
    if message.startswith("name:"):
        new_name = message[5:].strip()
        if new_name:
            user_names[user_id] = new_name
            save_data()  # Save after name change
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
                if test.creator_id in ADMIN_IDS:
                    test.is_scored = True
                    test.max_score = max_score
                    save_data()  # Save after test score update
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

    # Handle regular test creation
    if "+" in message:
        try:
            test_name, test_key = message.split("+", 1)
            test_name = test_name.strip()
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
            tests[test_code] = Test(test_key, user_id, test_name)
            save_data()  # Save after test creation

            await update.message.reply_text(
                f"✅ Test muvaffaqiyatli yaratildi!\n"
                f"📋 Test nomi: {test_name}\n"
                f"📌 Test kodi: {test_code}\n"
                f"🔑 Javoblar: {test_key.upper()}\n"
                f"📏 Uzunlik: {len(test_key)} ta belgi"
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

def main():
    """Start the bot."""
    try:
        # Load saved data
        load_data()
        
        # Create the Application and pass it your bot's token
        application = Application.builder().token(token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("testlarim", testlarim_command))
        application.add_handler(CommandHandler("students", students_command))
        application.add_handler(CommandHandler("scores", scores_command))
        application.add_handler(CommandHandler("edit", edit_command))
        application.add_handler(CommandHandler("info", info_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise e
    finally:
        # Save data before shutting down
        save_data()

if __name__ == "__main__":
    # Set up event loop policy for Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main() 