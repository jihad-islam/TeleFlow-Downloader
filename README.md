# 🚀 TeleFlow Downloader

A powerful Telegram media downloader built with **Python** and **Telethon**.

TeleFlow Downloader supports two modes:

* **CLI Mode** – Download multiple Telegram media files from a list of links.
* **Bot Mode** – Turn your Telegram **Saved Messages** into a personal cloud storage assistant that automatically downloads and re-uploads media.

---

## ✨ Features

* 📥 Bulk download Telegram media using a list of links
* 🤖 Background Bot Mode
* ☁️ Automatically upload downloaded files to **Saved Messages**
* 🗑️ Delete local files after successful upload to save disk space
* ⚡ Parallel downloads with configurable concurrency
* 📊 Clean real-time progress bars for downloading and uploading
* 🛑 Gracefully stop the bot remotely using `/stop`
* 🐳 Docker support
* 🔒 Secure local Telegram session management

---

## 📁 Project Structure

```text
TeleFlow-Downloader/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── src/
│   ├── __init__.py
│   ├── application.py
│   ├── bot.py
│   ├── cli.py
│   ├── config.py
│   ├── downloader.py
│   └── utils.py
│
├── downloads/
├── links.txt
├── .env
├── .gitignore
├── requirements.txt
├── main.py
└── README.md
```

---

# ⚙️ Requirements

* Python **3.11+**
* Telegram API credentials (`API_ID` & `API_HASH`)
* Docker (optional)

---

# 🔑 Get Telegram API Credentials

Telethon requires your own Telegram API credentials.

1. Visit **https://my.telegram.org**
2. Log in using your Telegram account.
3. Open **API Development Tools**.
4. Create a new application.
5. Copy your:

* `API_ID`
* `API_HASH`

Create a `.env` file in the project root:

```env
API_ID=your_api_id
API_HASH=your_api_hash
```

---

# 🛠 Installation

## Clone the repository

```bash
git clone https://github.com/jihad-islam/TeleFlow-Downloader.git

cd TeleFlow-Downloader
```

---

## Create Virtual Environment

Linux/macOS

```bash
python -m venv .venv

source .venv/bin/activate
```

Windows

```powershell
python -m venv .venv

.venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

### Python 3.14 Users

If you're using Python **3.14 or newer**, update Telethon to the latest version:

```bash
pip install -U telethon
```

Older Telethon releases may produce asyncio-related errors on Python 3.14.

---

# 🔐 First Login

The first time you run the application, Telethon will ask for:

* Phone number
* Verification code
* Two-step password (if enabled)

After successful authentication, a local session file is created automatically:

```text
my_account_session.session
```

As long as this file exists, you won't need to log in again on that device.

> **Note**
>
> If you use multiple computers, each device should keep its own session file.

---

# 🚀 Usage

## CLI Mode

Add Telegram links to `links.txt` (one link per line).

Example:

```text
https://t.me/channel/123
https://t.me/channel/124
https://t.me/channel/125
```

Run:

```bash
python main.py --mode cli
```

The downloader will:

* Read every link
* Download files concurrently
* Save them into the `downloads/` directory

---

## Bot Mode

Start the background bot:

```bash
python main.py --mode bot
```

Now simply:

1. Open Telegram.
2. Go to **Saved Messages**.
3. Send or forward a Telegram media link.

The bot will automatically:

* Download the media
* Upload it back to Saved Messages
* Delete the local copy

To stop the bot remotely:

```text
/stop
```

---

# 🐳 Docker

Run in background:

```bash
docker compose -f docker/docker-compose.yml up -d
```

View logs:

```bash
docker logs -f tg_downloader_bot
```

Stop:

```bash
docker compose -f docker/docker-compose.yml down
```

---

# ⚡ Parallel Downloads

The downloader supports concurrent downloads using **asyncio**.

You can place many links inside `links.txt`.

Example:

```
10 links
↓
Only 2 downloads run simultaneously
↓
Remaining links wait in the queue
↓
When one finishes, the next starts automatically
```

This keeps resource usage low while improving download speed.

---

# 📦 Output

CLI Mode:

```text
downloads/
├── video1.mp4
├── file.pdf
└── image.jpg
```

Bot Mode:

```text
Downloaded
      ↓
Uploaded to Saved Messages
      ↓
Local file deleted automatically
```

---

# 🛠 Troubleshooting

### `RuntimeError: There is no current event loop`

Update Telethon:

```bash
pip install -U telethon
```

This commonly occurs when using older Telethon versions with Python 3.14.

---

### Login requested every time

Make sure the generated `.session` file is not deleted.

---

### Invalid API_ID or API_HASH

Verify your `.env` configuration.

---

### Media cannot be downloaded

Possible reasons:

* Private channel access required
* Deleted message
* Invalid Telegram link

---

# 🤝 Contributing

Contributions, feature requests, and pull requests are welcome.

If you discover a bug or have an idea for an improvement, feel free to open an issue.

---

# 📄 License

This project is licensed under the **MIT License**.
