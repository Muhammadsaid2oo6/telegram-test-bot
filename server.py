from flask import Flask, send_from_directory, request, jsonify
from bot import tests, Test, ADMIN_ID
import os
from datetime import datetime

app = Flask(__name__)

# Serve static files
@app.route('/')
def serve_index():
    return send_from_directory('webapp', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('webapp', path)

# API endpoints
@app.route('/submit-test', methods=['POST'])
def submit_test():
    data = request.json
    test_code = data.get('testCode')
    answer = data.get('answers')
    user_id = data.get('userId')

    if not all([test_code, answer, user_id]):
        return jsonify({'success': False, 'error': 'Ma\'lumotlar to\'liq emas'})

    if test_code not in tests:
        return jsonify({'success': False, 'error': 'Test mavjud emas'})

    test = tests[test_code]
    
    if test.creator_id != ADMIN_ID:
        return jsonify({'success': False, 'error': 'Bu test mavjud emas'})

    if user_id in test.attempts:
        return jsonify({'success': False, 'error': 'Siz bu testga allaqachon javob bergansiz'})

    correct_key = test.code
    if len(answer) != len(correct_key):
        return jsonify({'success': False, 'error': 'Javob uzunligi noto\'g\'ri'})

    # Create detailed feedback
    feedback = "📝 Test natijalari:<br><br>"
    correct_count = 0
    for idx, (user_ans, correct_ans) in enumerate(zip(answer.lower(), correct_key), 1):
        is_correct = user_ans == correct_ans
        if is_correct:
            correct_count += 1
            feedback += f"{idx}. ✅ {user_ans.upper()}<br>"
        else:
            feedback += f"{idx}. ❌ {user_ans.upper()} (To'g'ri javob: {correct_ans.upper()})<br>"

    percentage = (correct_count / len(correct_key)) * 100

    if test.is_scored:
        score = (percentage / 100) * test.max_score
        test.attempts[user_id] = score
        feedback += f"<br>📊 Umumiy natija: {correct_count}/{len(correct_key)} ({percentage:.1f}%)<br>"
        feedback += f"💯 Ball: {score:.1f}/{test.max_score}"
    else:
        test.attempts[user_id] = percentage
        feedback += f"<br>📊 Umumiy natija: {correct_count}/{len(correct_key)} ({percentage:.1f}%)"

    return jsonify({
        'success': True,
        'feedback': feedback
    })

@app.route('/create-test', methods=['POST'])
def create_test():
    data = request.json
    user_id = data.get('userId')
    test_name = data.get('testName')
    test_key = data.get('testKey')

    if user_id != ADMIN_ID:
        return jsonify({'success': False, 'error': 'Faqat administrator test yarata oladi'})

    if not all([test_name, test_key]):
        return jsonify({'success': False, 'error': 'Test nomi va kaliti kiritilmagan'})

    test_code = f"{len(tests) + 1:03d}"
    tests[test_code] = Test(test_key.lower(), user_id)

    return jsonify({
        'success': True,
        'testCode': test_code
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 