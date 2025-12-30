
import os

# Use environment variable or prompt for key
content = "GROQ_API_KEY=your_key_here"

with open(".env", "a", encoding="utf-8") as f:
    f.write(content + "\n")
print("Updated .env file")
