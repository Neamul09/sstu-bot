# SSTU Bot 🎓

A comprehensive Telegram Bot designed for academic management at SSTU. This bot helps students and faculty manage class routines, notices, resources, and deadlines efficiently through a centralized, automated system.

## 🚀 Key Features

### 📅 Smart Timetable Management
*   **Dynamic Routine:** View daily class schedules with real-time updates.
*   **Management Dashboard:** Authorized users (CRs/Teachers) can add, delete, or reschedule classes.
*   **Official Routine:** Quick access to the scanned official routine images.
*   **Automatic Reminders:** Notifications for upcoming classes and routine changes.

### 📢 Digital Notice Board
*   **Direct Broadcasts:** Delivers important news instantly to every student.
*   **Multimedia Support:** Support for text, images, and document attachments.
*   **Search Functionality:** Quickly find specific notices from history.
*   **Management:** Easy cleanup and moderation of the notice feed.

### 🔔 Intelligent Notifications
*   **Batching:** Prevents notification fatigue by grouping updates.
*   **Scheduling:** CRs can schedule alerts for specific times (e.g., nightly routine updates).
*   **Instant Alerts:** Real-time notifications for cancellations or room changes.

### 🛠️ Additional Tools
*   **Resource Sharing:** Centralized hub for lecture notes and study materials.
*   **Deadline Tracker:** Monitor assignments, quizzes, and project dates.
*   **Multilingual:** Full support for English and Bengali (বাংলা).
*   **Role-Based Access:** Distinct permissions for Students, CRs, Teachers, and Admins.

## 💻 Tech Stack

*   **Language:** Python 3.10+
*   **Library:** [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
*   **Database:** [Supabase](https://supabase.com/) (PostgreSQL)
*   **Timezone Management:** Pytz (Optimized for Bangladesh Standard Time)

## 🛠️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Neamul09/sstu-bot.git
    cd sstu-bot
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `config.py` file or set the following variables:
    *   `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather.
    *   `SUPABASE_URL`: Your Supabase project URL.
    *   `SUPABASE_SERVICE_KEY`: Your Supabase service role key.
    *   `TZ`: Timezone (Default: `Asia/Dhaka`).

4.  **Database Setup:**
    Execute the provided `supabase_schema.sql` in your Supabase SQL Editor to set up the necessary tables and relationships.

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## 📂 Project Structure

```text
├── handlers/           # Telegram command and callback handlers
│   ├── timetable.py    # Routine management logic
│   ├── notices.py      # Notice board logic
│   ├── deadlines.py    # Assignment tracking
│   └── ...
├── utils/              # Helper functions, i18n, and timezone tools
├── main.py             # Entry point - Bot initialization
├── database.py         # Supabase database interface
├── config.py           # Configuration settings
└── supabase_schema.sql # Database schema definition
```

## 🤝 Contributing

Contributions are welcome! If you have suggestions for improvements or new features, feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License.

---
*Created with ❤️ for the SSTU Community.*
