# Aizen Plugin System

Aizen supports a powerful plugin system that allows you to easily add new custom tools that the AI can use.

Plugins are simple Python files that define two functions: `get_tools()` and `execute_tool(tool_call, auto_approve)`.

## Installing Plugins

To install a plugin, simply place the Python script in the Aizen plugins directory:
`~/.aizen/plugins/`

Aizen automatically loads all Python files in this directory on startup.

## Creating a Plugin

A plugin must define two functions:
1. `get_tools()`: Returns a list of dictionaries representing the OpenAI Tool Call schemas for the tools your plugin provides.
2. `execute_tool(tool_call, auto_approve=False)`: Called when the AI invokes one of your tools. It should return a string with the result.

### Example: Weather Plugin

Here is a simple example of a plugin that fetches the current weather (using a mock API).

Create a file `~/.aizen/plugins/weather_plugin.py`:

```python
import json

def get_tools():
    """Returns the tool schema for the AI."""
    return [{
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location"]
            }
        }
    }]

def execute_tool(tool_call, auto_approve=False):
    """Executes the tool call."""
    if tool_call.function.name == "get_current_weather":
        args = json.loads(tool_call.function.arguments)
        location = args.get("location")
        unit = args.get("unit", "celsius")
        
        # In a real plugin, you would call an actual weather API here.
        # We will just return mock data for the example.
        if "san francisco" in location.lower():
            return f"The weather in {location} is 15 {unit} and cloudy."
        elif "tokyo" in location.lower():
            return f"The weather in {location} is 22 {unit} and sunny."
        else:
            return f"The weather in {location} is 20 {unit} and clear."
```

## Tips for Plugin Developers
- **Logging**: You can import `from aizen.logging_config import logger` to log debug information.
- **Dependencies**: If your plugin requires third-party packages, the user will need to install them in their global Python environment or the environment where Aizen is running.
- **Auto Approval**: Respect the `auto_approve` flag. If your tool performs a dangerous action (like modifying a database), you should prompt the user for confirmation if `auto_approve` is `False`.
