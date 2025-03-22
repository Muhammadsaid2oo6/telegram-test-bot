# Bot Database Files

This directory contains JSON files that store the bot's data. Here's how to use each file:

## 1. students.json
Stores information about all registered students:
```json
{
  "user_id": {
    "user_id": 123456789,
    "full_name": "Student Name",
    "test_results": {
      "test_code": {
        "score": 85.5,
        "date": "2024-03-20T15:30:00"
      }
    },
    "registration_date": "2024-03-20T15:00:00"
  }
}
```

## 2. tests.json
Stores information about all regular tests:
```json
{
  "test_code": {
    "code": "abc123",
    "creator_id": 123456789,
    "attempts": {
      "user_id": "answer"
    },
    "is_scored": true,
    "max_score": 100,
    "date_created": "2024-03-20T15:00:00"
  }
}
```

## 3. open_tests.json
Stores information about all open tests:
```json
{
  "test_code": {
    "code": "O001",
    "creator_id": 123456789,
    "questions": ["Question 1", "Question 2"],
    "attempts": {
      "user_id": {
        "Question 1": "Answer 1",
        "Question 2": "Answer 2"
      }
    }
  }
}
```

## How to Use

1. **Backup**: Regularly copy these files to a safe location
2. **Restore**: If needed, you can restore from a backup by replacing the files
3. **Manual Edit**: You can edit these files manually, but be careful with the JSON format
4. **View Data**: You can open these files in any text editor to view the data

## Important Notes

- The bot automatically saves data when it shuts down
- Data is loaded when the bot starts
- Don't edit these files while the bot is running
- Always make backups before making manual changes
- Keep the JSON format valid when editing manually 