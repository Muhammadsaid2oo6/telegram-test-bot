# Telegram Test Bot

This bot allows users to create and check tests through Telegram. Users can create tests with answer keys and others can attempt to solve them.

## Features

- Create new tests with answer keys
- Check test answers
- One attempt per test per user
- Support for both uppercase and lowercase answers
- Percentage-based scoring system

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a new bot through [@BotFather](https://t.me/BotFather) on Telegram and get your bot token.

3. Copy the bot token to the `.env` file:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

4. Run the bot:
```bash
python bot.py
```

## Usage

1. Start the bot by sending `/start`
2. Choose between creating a new test or checking an existing test

### Creating a Test
- Format: `test_name+answer_key`
- Example: `MyTest+abcdabcd`

### Checking a Test
- Format: `test_code*your_answers`
- Example: `001*abcdabcd`

## Notes

- Test codes are automatically generated
- Users can only attempt each test once
- Both uppercase and lowercase letters are accepted
- Only letters and numbers are allowed in answer keys 