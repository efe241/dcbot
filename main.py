import sys
import os
from dotenv import load_dotenv

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Load environment variables from .env or env.txt
env_file = os.path.join(root_dir, ".env")
alt_file = os.path.join(root_dir, "env.txt")
if os.path.exists(env_file):
    load_dotenv(env_file)
if os.path.exists(alt_file):
    load_dotenv(alt_file)

print("Starting SurveyTR Discord Bot...", flush=True)

from bot.bot import main

if __name__ == "__main__":
    main()
