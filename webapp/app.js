let tg = window.Telegram.WebApp;

// Initialize Telegram Web App
tg.expand();
tg.ready();

// Check if user is admin
const isAdmin = tg.initDataUnsafe?.user?.id === ADMIN_ID;
if (isAdmin) {
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
}

// Show/hide sections
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('hidden');
    });
    document.getElementById(sectionId).classList.remove('hidden');
}

function showMainMenu() {
    showSection('mainMenu');
}

function showTestAnswer() {
    showSection('testAnswerSection');
}

function showTestCreation() {
    if (!isAdmin) {
        tg.showAlert('Faqat administrator test yarata oladi');
        return;
    }
    showSection('testCreationSection');
}

function showVideoTutorial() {
    if (!isAdmin) {
        tg.showAlert('Faqat administrator uchun');
        return;
    }
    window.open('https://abot.uz/mybots/Test_bot_yaratish_bot/testinfo.php?data=bWFqYnVyaXlfeGlsYldWRjBXMWhkR2lyWVh5MDl0Ym1GdGVRPT0=');
}

// Handle test submission
async function submitAnswers() {
    const testCode = document.getElementById('testCode').value.trim();
    const answers = document.getElementById('answers').value.trim();

    if (!testCode || !answers) {
        tg.showAlert('Test kodi va javoblarni kiriting!');
        return;
    }

    try {
        const response = await fetch('/submit-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                testCode,
                answers,
                userId: tg.initDataUnsafe?.user?.id
            })
        });

        const result = await response.json();
        
        if (result.success) {
            document.getElementById('resultContent').innerHTML = result.feedback;
            showSection('resultSection');
        } else {
            tg.showAlert(result.error || 'Xatolik yuz berdi');
        }
    } catch (error) {
        tg.showAlert('Serverga ulanishda xatolik');
    }
}

// Handle test creation
async function createTest() {
    if (!isAdmin) {
        tg.showAlert('Faqat administrator test yarata oladi');
        return;
    }

    const testName = document.getElementById('testName').value.trim();
    const testKey = document.getElementById('testKey').value.trim();

    if (!testName || !testKey) {
        tg.showAlert('Test nomi va kalitini kiriting!');
        return;
    }

    try {
        const response = await fetch('/create-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                testName,
                testKey,
                userId: tg.initDataUnsafe?.user?.id
            })
        });

        const result = await response.json();
        
        if (result.success) {
            tg.showAlert(`Test yaratildi!\nTest kodi: ${result.testCode}`);
            showMainMenu();
        } else {
            tg.showAlert(result.error || 'Xatolik yuz berdi');
        }
    } catch (error) {
        tg.showAlert('Serverga ulanishda xatolik');
    }
}

// Handle back button
tg.BackButton.onClick(() => {
    showMainMenu();
}); 