# ElevenLabs Tools Setup Guide

## Overview
Your reminder tools are already registered in code using ElevenLabs' `ClientTools` API. This guide explains how to ensure they work properly with your ElevenLabs agent.

## Code Setup (Already Done ✅)

The tools are registered in `tools.py`:
- `setReminder` - Set reminders from natural language
- `listReminders` - List all active reminders  
- `deleteReminder` - Delete reminders by number

These are passed to the Conversation object in `main.py` via `client_tools=client_tools`.

## ElevenLabs Dashboard Configuration

### Option 1: Client Tools (Current Setup - Recommended)
Client Tools are registered in your code and automatically available to the agent. However, you may need to:

1. **Update Agent System Prompt** (if you have access):
   - Go to your ElevenLabs dashboard
   - Navigate to your agent settings
   - Update the system prompt to mention reminder capabilities:
   
   ```
   You have access to reminder management tools:
   - setReminder: Use when users want to create reminders. Extract the full reminder text including time (e.g., "remind me to call mom tomorrow at 3pm")
   - listReminders: Use when users ask to see their reminders or list reminders
   - deleteReminder: Use when users want to cancel/delete reminders. First list reminders to get the number, then delete by number.
   ```

2. **Verify Tool Discovery**:
   - The agent should automatically discover Client Tools
   - Test by saying: "remind me to test this in 1 minute"
   - The agent should call `setReminder` automatically

### Option 2: Server Tools (Alternative - More Complex)
If Client Tools don't work as expected, you can create Server Tools via API:

```python
import requests

url = "https://api.elevenlabs.io/v1/convai/tools"

# Tool 1: Set Reminder
set_reminder_tool = {
    "tool_config": {
        "name": "setReminder",
        "description": "Set a reminder from natural language text. Use when user wants to create a reminder.",
        "api_schema": {
            "url": "https://your-server.com/api/reminders/set",
            "method": "POST",
            "request_body_schema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The reminder text with time, e.g., 'remind me to call mom tomorrow at 3pm'"
                    }
                },
                "required": ["text"]
            }
        }
    }
}

# Tool 2: List Reminders
list_reminders_tool = {
    "tool_config": {
        "name": "listReminders",
        "description": "List all active reminders that haven't been triggered yet.",
        "api_schema": {
            "url": "https://your-server.com/api/reminders/list",
            "method": "GET"
        }
    }
}

# Tool 3: Delete Reminder
delete_reminder_tool = {
    "tool_config": {
        "name": "deleteReminder",
        "description": "Delete a reminder by its number. First list reminders to get the number.",
        "api_schema": {
            "url": "https://your-server.com/api/reminders/delete",
            "method": "POST",
            "request_body_schema": {
                "type": "object",
                "properties": {
                    "number": {
                        "type": "integer",
                        "description": "The reminder number (1-based index from the list)"
                    }
                },
                "required": ["number"]
            }
        }
    }
}

headers = {
    "xi-api-key": "YOUR_ELEVENLABS_API_KEY",
    "Content-Type": "application/json"
}

# Create each tool
for tool in [set_reminder_tool, list_reminders_tool, delete_reminder_tool]:
    response = requests.post(url, json=tool, headers=headers)
    print(f"Created tool: {response.json()}")
```

**Note**: Server Tools require you to expose API endpoints, which is more complex than Client Tools.

## Testing Your Tools

### Test in Online Mode:

1. **Set a Reminder**:
   ```
   User: "Remind me to call my mom tomorrow at 3pm"
   Expected: Agent calls setReminder tool
   ```

2. **List Reminders**:
   ```
   User: "What are my reminders?"
   Expected: Agent calls listReminders tool
   ```

3. **Delete Reminder**:
   ```
   User: "Delete reminder number 1"
   Expected: Agent calls deleteReminder tool with number=1
   ```

## Troubleshooting

### If tools aren't being called:

1. **Check Agent Configuration**:
   - Ensure your agent has tool calling enabled
   - Check if there are any restrictions on tool usage

2. **Verify Tool Registration**:
   - Add debug prints in your tool functions to confirm they're being called
   - Check the conversation logs in ElevenLabs dashboard

3. **Update Agent Instructions**:
   - Be explicit in your agent's system prompt about when to use reminders
   - Example: "When users mention reminders, scheduling, or remembering something, use the setReminder tool"

4. **Test Tool Functions Directly**:
   ```python
   from tools import set_reminder, list_reminders, delete_reminder
   
   # Test set_reminder
   result = set_reminder({"text": "test reminder in 1 minute"})
   print(result)
   
   # Test list_reminders
   result = list_reminders({})
   print(result)
   ```

## Current Status

✅ Tools registered in code (`tools.py`)
✅ Tools passed to Conversation object (`main.py`)
✅ Reminder manager integrated (`reminder_manager.py`)
✅ Background scheduler running (`main.py`)

**Next Step**: Test with your ElevenLabs agent to ensure it recognizes and calls these tools automatically. If not, update the agent's system prompt as described above.

