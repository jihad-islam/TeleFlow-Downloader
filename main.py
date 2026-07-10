import asyncio
import sys

from src.application import main


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Script stopped manually (Ctrl+C). Goodbye!")
        sys.exit(0)
