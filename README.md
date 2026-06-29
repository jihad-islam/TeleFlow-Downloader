# 🚀 TeleFlow Downloader

A powerful, hybrid Telegram media downloader built with Python and Telethon. TeleFlow Downloader operates in two distinct modes: a **CLI Mode** for bulk downloading from a list of links, and a seamless **Bot Mode** that runs in the background and acts as your personal cloud storage assistant.

## ✨ Key Features

* **Hybrid Architecture:** Choose between terminal-based bulk downloading or a silent background bot.
* **Cloud Storage Mode (Bot):** Forward any Telegram link to your "Saved Messages". The script downloads it, re-uploads it as a native media file, and instantly deletes the local copy to save your PC's storage.
* **Remote Control:** Safely shut down the background script anytime by simply sending `/stop` in your Saved Messages.
* **Parallel Processing:** Uses `asyncio` to handle multiple downloads concurrently with a configurable queue limit.
* **Clean Terminal UI:** Real-time, single-line progress bars for both downloading and uploading operations.
* **Docker Ready:** Fully containerized setup for easy deployment on any server or local machine without manual environment configuration.

## 📁 Project Structure

```text
tg-downloader/
├── docker/                     # Docker configuration files
│   ├── docker-compose.yml
│   └── Dockerfile
├── src/                        # Core application logic
│   ├── __init__.py             
│   ├── config.py
│   ├── utils.py
│   └── downloader.py
├── .env                        # Environment variables (API Credentials)
├── .gitignore                  
├── requirements.txt            # Python dependencies
├── links.txt                   # URL list for CLI mode
└── main.py                     # Application entry point

```

## ⚙️ Prerequisites

* **Python 3.11+** (If running manually)
* **Docker & Docker Compose** (If using the containerized setup)
* **Telegram API Credentials:** You need an `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).

## 🛠️ Installation & Setup

**1. Clone the repository:**

```bash
git clone https://github.com/jihad-islam/TeleFlow-Downloader.git
cd tg-downloader

```

**2. Configure Environment Variables:**
Create a `.env` file in the root directory and add your Telegram API credentials:

```env
API_ID=your_api_id_here
API_HASH=your_api_hash_here

```
## 🔑 How to get API_ID and API_HASH

To use this script, you must generate your own Telegram API credentials. It's free and takes only a minute:

1. Go to [my.telegram.org](https://my.telegram.org) and log in with your Telegram phone number.
2. Click on **"API development tools"**.
3. A form will appear. Fill in the **App title** and **Short name** (you can write anything, e.g., `MyDownloaderApp`). Leave the URL field empty and select your platform.
4. Click on **"Create application"**.
5. You will now see your **`api_id`** and **`api_hash`**. Copy these values.
6. Create a `.env` file in the root folder of this project and paste them like this:
   ```env
   API_ID=your_api_id_here
   API_HASH=your_api_hash_here


### Option A: Run via Docker (Recommended)

You can easily spin up the project in the background using Docker. The default command runs the script in `bot` mode.

```bash
docker-compose -f docker/docker-compose.yml up -d

```

*To view logs:* `docker logs -f tg_downloader_bot`
*To stop:* `docker-compose -f docker/docker-compose.yml down`

### Option B: Manual Setup (Local PC)

Create a virtual environment and install the required dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt

```

## 🚀 Usage

### 1. CLI Mode (Bulk Download)

Add your Telegram links to `links.txt` (one link per line), then run:

```bash
python main.py --mode cli

```

The script will concurrently download all media files into the `downloads/` folder with a clean progress bar.

### 2. Bot Mode (Cloud Storage Assistant)

Run the script in bot mode to keep it listening in the background:

```bash
python main.py --mode bot

```

* Go to your Telegram app.
* Send or forward any media link to your **Saved Messages**.
* The script will automatically process the link, upload the media directly into your Saved Messages, and delete the temporary local file.
* Send `/stop` to gracefully shut down the application.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://www.google.com/search?q=https://github.com/your_username/tg-downloader/issues).

## 📜 License

This project is licensed under the MIT License.