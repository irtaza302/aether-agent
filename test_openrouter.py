import asyncio
import json
import os

from openai import AsyncOpenAI


async def test():
    config_path = os.path.expanduser("~/.aizen_config.json")
    with open(config_path) as f:
        config = json.load(f)
    api_key = config.get("OPENROUTER_API_KEY")

    print("Testing OpenRouter with model: openrouter/free")
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model="openrouter/free",
            messages=[{"role": "user", "content": "Hello! Say exactly 'Working!'"}]
        )
        print("\n✅ SUCCESS! Received response:")
        print("—" * 40)
        print(response.choices[0].message.content)
        print("—" * 40)
    except Exception as e:
        print("\n❌ FAILED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {str(e)}")

asyncio.run(test())
