import uvicorn
import multiprocessing
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runner")

def run_fastapi():
    logger.info("Starting FastAPI Backend Server on port 8000...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

def run_discord_bot():
    logger.info("Starting Discord Bot Service...")
    from bot.bot import main as bot_main
    bot_main()

if __name__ == "__main__":
    logger.info("==================================================")
    logger.info("  Discord Coin + CPX Research Reward System v1.0  ")
    logger.info("==================================================")
    
    # Process 1: FastAPI Web Server
    web_process = multiprocessing.Process(target=run_fastapi)
    web_process.start()

    # Process 2: Discord Bot (if token configured)
    bot_process = multiprocessing.Process(target=run_discord_bot)
    bot_process.start()

    web_process.join()
    bot_process.join()
