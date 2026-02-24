import os
import random
import string
import time
import datetime
from sqlite3 import connect
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
import smtplib
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "medialert.db")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "devsecret123")

# EMAIL & SMS CONFIG (env)
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMS_TO_EMAIL_DOMAIN = os.environ.get("SMS_TO_EMAIL_DOMAIN")

# TRANSLATIONS (simplified; expand as needed)
TRANSLATIONS = {
    "en": {
        "About":"About", "Emergency":"Emergency", "Feedback":"Feedback", "Login":"Login",
        "Register Patient":"Register Patient", "Register Caretaker":"Register Caretaker",
        "Send OTP":"Send OTP", "Role":"Role", "Email":"Email", "Password":"Password",
        "Phone":"Phone", "Age":"Age", "Gender":"Gender", "Send":"Send",
        "Report":"Report", "Reports":"Reports", "Profile":"Profile",
        "Patient Instructions":"Patient Instructions", "Patient Profile":"Patient Profile",
        "Medicines":"Medicines", "Action":"Action", "Taken":"Taken", "Missed":"Missed",
        "Add Medicine":"Add Medicine", "Register":"Register", "Name":"Name",
        "Need Help Note":"Need help? Use the Feedback page to contact the administrator."
    },
    "kn": {
        "About":"ಬಗ್ಗೆ", "Emergency":"ತುರ್ತು", "Feedback":"ಪ್ರತಿಕ್ರಿಯೆ", "Login":"ಲಾಗಿನ್",
        "Register Patient":"ರೋಗಿಯನ್ನು ನೋಂದಾಯಿಸಿ", "Register Caretaker":"ಸಂರಕ್ಷಕನನ್ನು ನೋಂದಾಯಿಸಿ",
        "Send OTP":"OTP ಕಳುಹಿಸಿ", "Role":"ಭೂมಿಕೆ", "Email":"ಇಮೇಲ್", "Password":"ಗುಪ್ತಪದ",
        "Phone":"ದೂರವಾಣಿ", "Age":"ವಯಸ್ಸು", "Gender":"ಲಿಂಗ", "Send":"ಕಳಿಸಿ",
        "Report":"ವರದಿ", "Reports":"ವರದಿಗಳು", "Profile":"ಪ್ರೊಫೈಲ್",
        "Patient Instructions":"ರೋಗಿ ಸೂಚನೆಗಳು", "Patient Profile":"ರೋಗಿಯ ಪ್ರೊಫೈಲ್",
        "Medicines":"ಮೆಡಿಸಿನ್‌ಗಳು", "Action":"ಕ್ರಿಯೆ", "Taken":"ತೆಗೆದುಕೊಂಡ", "Missed":"ಕಳೆತ",
        "Add Medicine":"ಮೆಡಿಸಿನ್ ಸೇರಿಸಿ", "Register":"ನೋಂದಾಯಿಸಿ", "Name":"ಹೆಸರು",
        "Need Help Note":"ಸಹಾಯ ಬೇಕೆ? ವ್ಯವಸ್ಥಾಪಕರನ್ನು ಸಂಪರ್ಕಿಸಲು ದಯವಿಟ್ಟು ಪ್ರತಿಕ್ರಿಯೆ ಪುಟವನ್ನು ಉಪಯೋಗಿಸಿ."
    }
}

# Longer UI text translations (About page and login instructions)
TRANSLATIONS['en'].update({
    'AboutPara1': 'MediAlert is a patient-centered medication management platform designed to simplify medicine adherence and improve safety for individuals and their caregivers. Built with real-world workflows in mind, MediAlert combines automated reminders, clear on-screen and voice alerts, role-based dashboards, and streamlined caregiver notifications to reduce missed doses and help families stay informed.',
    'AboutPara2': 'The product supports both patients and caretakers with separate views: patients receive straightforward, accessible prompts at scheduled times while caretakers get consolidated reports and timely notifications when a dose is taken, missed, or an emergency is raised. Notifications are delivered via email and—where configured—via SMS gateways. For accessibility, MediAlert also includes a repeated audible alert and an in-page full-screen notice to make sure time-sensitive prompts are hard to miss.',
    'AboutPara3': 'Reporting features provide daily and weekly summaries that list taken and missed medications, and a visual chart helps caretakers understand adherence trends at a glance. A dedicated reports panel allows three-dot inspection of patient data, including medication schedules and caretaker contact details, presented in an easy-to-read table format. Feedback and rating tools let users share experience and help prioritize future improvements.',
    'AboutPara4': 'Security and privacy are central to the design. Sensitive information is stored in the application database; email delivery is routed through configurable SMTP settings and an outbox fallback is available to preserve messages when an external mail provider is not configured. The system avoids exposing unnecessary personal data and supports role-based access so only authorized caretakers can view patient details.',
    'AboutPara5': 'Our mission is to reduce preventable medication errors and provide families with a reliable, low-friction tool that complements clinical care. MediAlert is intentionally lightweight and simple to operate: it works well for home use, requires minimal setup, and integrates with common notification channels. We welcome feedback and continually refine the product based on caregiver and patient needs.',
    'AboutPara6': 'For questions, setup help, or to suggest features, use the Feedback page or reach out to the account administrator. In urgent situations, use the Emergency page to notify assigned caretakers immediately.'
})

TRANSLATIONS['kn'].update({
    'AboutPara1': 'MediAlert ಒಂದು ರೋಗಿ-ಕೇಂದ್ರಿತ ಔಷಧಿ ನಿರ್ವಹಣೆ ವೇದಿಕೆ ಆಗಿದ್ದು, ಔಷಧಿ ಅನುಸರಣೆ ಸರಳಗೊಳಿಸಲು ಮತ್ತು ವ್ಯಕ್ತಿಗಳು ಮತ್ತು ಅವರ ಸಂರಕ್ಷಕರಿಗಾಗಿ ಭದ್ರತೆ ಹೆಚ್ಚಿಸಲು ವಿನ್ಯಾಸಗೊಳಿಸಲಾಗಿದೆ. ವಾಸ್ತವದಲ್ಲಿ ಬಳಸುವ ಕೆಲಸದ ಹರಿವನ್ನು ಗಮನದಲ್ಲಿರಿಸಿಕೊಂಡು ನಿರ್ಮಿಸಲಾಗಿದ್ದು, MediAlert ಸ್ವಯಂಚಾಲಿತ ನೆನಪಣೆಗಳನ್ನು, ಸ್ಪಷ್ಟ ಆನ್-ಸ್ಕ್ರೀನ್ ಮತ್ತು ಧ್ವನಿ ಎಚ್ಚರಿಕೆಗಳನ್ನು, ಪಾತ್ರಾಧಾರಿತ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗಳನ್ನು ಮತ್ತು ಸಂರಕ್ಷಕ ಸಂದೇಶಗಳನ್ನು ಒದಗಿಸುತ್ತದೆ যাতে ಕಳೆದುಕೊಂಡ ಡೋಸ್‍ಗಳು ಕಡಿಮೆಯಾಗುತ್ತವೆ ಮತ್ತು ಕುಟುಂಬಗಳು ಮಾಹಿತಿ ಪಡೆಯುತ್ತವೆ.',
    'AboutPara2': 'ಉತ್ಪನ್ನವು ರೋಗಿಗಳು ಮತ್ತು ಸಂರಕ್ಷಕರಿಗೆ ವಿಭಿನ್ನ ವೀಕ್ಷಣೆಯನ್ನು ನೀಡುತ್ತದೆ: ರೋಗಿಗಳು ಸರಳ ಮತ್ತು ಸುಲಭವಾಗಿ ಅರ್ಥವಾಗುವ ಸೂಚನೆಗಳನ್ನು ಸಮಯಕ್ಕೆ ಪಡೆದರೆ, ಸಂರಕ್ಷಕರು ಸಂಗ್ರಹಿತ ವರದಿಗಳನ್ನು ಮತ್ತು ಡೋಸ್ ತೆಗೆದಾಗ, ತಪ್ಪಾದಾಗ ಅಥವಾ ತುರ್ತು ಸಿಗುವಾಗ ತಕ್ಷಣದ ಅಥವಾ ನಿಯಮಿತ ತಿಳಿಸುವಿಕೆಗಳನ್ನು ಪಡೆಯುತ್ತಾರೆ. ಸೂಚನೆಗಳು ಇಮೇಲ್ ಮೂಲಕ ಹಾಗೂ ವ್ಯವಸ್ಥೆಯು ಸಕ್ರೀಯಗಿದ್ದರೆ SMS ಗೇಟ್‌ವೇಗಳ ಮೂಲಕ ಕಳುಹಿಸಲಾಗುತ್ತವೆ. ಪ್ರವೇಶೋಪಾಯಕ್ಕಾಗಿ, MediAlert ಪುನರಾವೃತ್ತಿ ಆಗುವ ಶ್ರವಣ ಎಚ್ಚರಿಕೆಯನ್ನು ಮತ್ತು ಪೇಜ್-內 ಪೂರ್ಣ-ಸ್ಕ್ರೀನ್ ಸೂಚನೆಯನ್ನು ಒಳಗೊಂಡಿದೆ.',
    'AboutPara3': 'ವರದಿ ವೈಶಿಷ್ಟ್ಯಗಳು taken ಮತ್ತು missed ಔಷಧಿಗಳ ದಿನನಿತ್ಯ/ವಾರಾಂತ್ಯ ಸಂಕ್ಷೇಪಣೆಯನ್ನು ಒದಗಿಸುತ್ತವೆ, ಮತ್ತು ದೃಶ್ಯ ಚಾರ್ಟ್ ಸಂರಕ್ಷಕರಿಗೆ ಅನುಸರಣೆ ಪ್ರವೃತ್ತಿಗಳನ್ನು ತ್ವರಿತವಾಗಿ ಅರ್ಥಮಾಡಲು ಸಹಾಯ ಮಾಡುತ್ತದೆ. ವಿಶೇಷ ವರದಿ ಪ್ಯಾನೆಲ್ ಮೂರು-ಬಿಂದುವಿನ ಪರಿಶೀಲನೆಯನ್ನು ಅನುಮತಿಸುತ್ತದೆ, ರೋಗಿಯ ಡೇಟಾ, ಔಷಧಿ ವೇಳಾಪಟ್ಟಿ ಮತ್ತು ಸಂರಕ್ಷಕರ ಸಂಪರ್ಕ ವಿವರಗಳನ್ನು ಸುಲಭವಾಗಿ ಓದುಗೊಳ್ಳಬಹುದಾದ ಪಟ್ಟಿಯಾಗಿ ನೀಡುತ್ತದೆ. ಪ್ರತಿಕ್ರಿಯೆ ಮತ್ತು ರೇಟಿಂಗ್ ಸಾಧನಗಳು ಬಳಕೆದಾರರ ಅನುಭವವನ್ನು ಹಂಚಿಕೊಳ್ಳಲು ಮತ್ತು ಭವಿಷ್ಯದ ಸುಧಾರಣೆಗೆ ಆದ್ಯತೆಯನ್ನು ನಿರ್ಧರಿಸಲು ಸಹಾಯ ಮಾಡುತ್ತವೆ.',
    'AboutPara4': 'ಕುರಿತ ಮತ್ತು ಗೌಪ್ಯತೆ ವಿನ್ಯಾಸದ ಕೇಂದ್ರವಾಗಿವೆ. ಸಂವೇದನಾಧರಿತ ಮಾಹಿತಿ ಅಪ್ಲಿಕೇಶನ್ ಡೇಟಾಬೇಸಿನಲ್ಲಿ ಸಂಗ್ರಹಿಸಲಾಗುತ್ತದೆ; ಇಮೇಲ್ ವಿತರಣೆ ಸಂರಚನೆ ಮಾಡಬಹುದಾದ SMTP ಸೆಟ್ಟಿಂಗ್ಗಳ ಮೂಲಕ ಮಾರ್ಗಸೂಚಿಸಲಾಗುತ್ತದೆ ಮತ್ತು ಹೊರಗಿನ ಮೇಲ್ ಪೂರೈಕೆದಾರ ನಿಯೋಜಿತಗೊಳ್ಳದಿದ್ದಾಗ ಸಂದೇಶಗಳನ್ನು ಉಳಿಸಲು outbox ಬ್ಯಾಕ್ಅಪ್ ಲಭ್ಯವಿದೆ. ವ್ಯವಸ್ಥೆ ಅಗತ್ಯವಿಲ್ಲದ ವೈಯಕ್ತಿಕ ಮಾಹಿತಿಯನ್ನು ಬಹಿರಂಗಪಡಿಸದು ಮತ್ತು ಪಾತ್ರಾಧಾರಿತ ಪ್ರವೇಶವನ್ನು ಬೆಂಬಲಿಸುತ್ತದೆ, ಹೀಗಾಗಿ ಮಾತ್ರ ಮಾನ್ಯತೆ ಪಡೆದ ಸಂರಕ್ಷಕರು ರೋಗಿಯ ವಿವರಗಳನ್ನು ವೀಕ್ಷಿಸಬಹುದು.',
    'AboutPara5': 'ನಮ್ಮ ದ್ಯೇಯವೆಂದರೆ ತಡೆಯಬಹುದಾದ ಔಷಧಿ ದೋಷಗಳನ್ನು ಕಡಿಮೆ ಮಾಡುವುದು ಮತ್ತು ಕುಟುಂಬಗಳಿಗೆ ನಂಬಿಕೆಯುಳ್ಳ, ಕಡಿಮೆ ಜಟಿಲತೆಯಿರುವ ಉಪಕರಣವನ್ನು ಒದಗಿಸುವುದು. MediAlert ಉದ್ದೇಶಪೂರ್ವಕವಾಗಿ ತೂಕವಿಲ್ಲದ ಮತ್ತು ಬಳಸಲು ಸರಳವಾಗಿದೆ: ಇದು ಮನೆ ಬಳಕೆಗೆ ಸೂಕ್ತವಾಗಿದೆ, ಕನಿಷ್ಟರೀತಿಯ ಸೆಟ್‌ಅಪ್‌ ಬೇಕಾಗುತ್ತದೆ ಮತ್ತು ಸಾಮಾನ್ಯ ಸೂಚನಾ ಚಾನಲ್‌ಗಳನ್ನು ಜೊತೆಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ. ನಾವು ಪ್ರತಿಕ್ರಿಯೆಯನ್ನು ಸ್ವಾಗತಿಸುತ್ತೇವೆ ಮತ್ತು ನಿರಂತರವಾಗಿ ಸಂರಕ್ಷಕರ ಮತ್ತು ರೋಗಿಗಳ ಅಗತ್ಯದ ಆಧಾರದ ಮೇಲೆ ಉತ್ಪನ್ನವನ್ನು ಸುಧಾರಿಸುತ್ತಿದ್ದೇವೆ.',
    'AboutPara6': 'ಪ್ರಶ್ನೆಗಳಿಗಾಗಿ, ಸೆಟ್‌ಅಪ್ ಸಹಾಯಕ್ಕಾಗಿ ಅಥವಾ ವೈಶಿಷ್ಟ್ಯಗಳನ್ನು ಸಲಹೆ ಮಾಡಲು, ದಯವಿಟ್ಟು Feedback ಪುಟವನ್ನು ಬಳಸಿ ಅಥವಾ ಖಾತೆ ನಿರ್ವಾಹಕನನ್ನು ಸಂಪರ್ಕಿಸಿ. ತುರ್ತು ಪರಿಸ್ಥಿತಿಗಳಲ್ಲಿ, ನಿಯೋಜಿತ ಸಂರಕ್ಷಕರನ್ನು ತಕ್ಷಣ ಮಾಹಿತಿ ನೀಡಲು Emergency ಪುಟವನ್ನು ಬಳಸಿ.'
})

# Login instruction translations
TRANSLATIONS['en'].update({
    'Instruction1': 'Keep your account details secure and share login only with trusted caretakers.',
    'Instruction2': 'Ensure your medication schedule (time and dose) is accurate when adding medicines.',
    'Instruction3': 'Allow browser audio and notifications for reliable voice and on-screen alerts.',
    'Instruction4': 'Use the Emergency page to instantly notify assigned caretakers in urgent situations.'
})

TRANSLATIONS['kn'].update({
    'Instruction1': 'ನಿಮ್ಮ ಖಾತೆ ವಿವರಗಳನ್ನು ಸುರಕ್ಷಿತವಾಗಿಟ್ಟುಕೊಳ್ಳಿ ಮತ್ತು ಲಾಗಿನ್ ಅನ್ನು ನಂಬಿಗಸ್ತ ಸಂರಕ್ಷಕರೊಂದಿಗೆ ಮಾತ್ರ ಹಂಚಿಕೊಳ್ಳಿ.',
    'Instruction2': 'ಔಷಧಿ ವೇಳಾಪಟ್ಟಿ (ಸಮಯ ಮತ್ತು ಡೋಸ್) ಸರಿಯಾಗಿ ಸೇರಿಸಲಾಗಿದೆ ಎಂದು ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ.',
    'Instruction3': 'ನಂಬಿಕೆಯೋಗ್ಯ ಧ್ವನಿ ಮತ್ತು ಆನ್-ಸ್ಕ್ರೀನ್ ಎಚ್ಚರಿಕೆಗಳಿಗಾಗಿ ಬ್ರೌಸರ್ ಶ್ರವಣ ಮತ್ತು ಸೂಚನೆಗಳನ್ನು ಅನುಮತಿಸಿ.',
    'Instruction4': 'ತುರ್ತು ಸ್ಥಿತಿಗಳಲ್ಲಿ ನಿಯೋಜಿತ ಸಂರಕ್ಷಕರಿಗೆ ತಕ್ಷಣ ತಿಳಿಸಲು Emergency ಪುಟವನ್ನು ಬಳಸಿ.'
})

def t(key):
    lang = session.get("lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

# ---------- DB helpers ----------
def get_db():
    conn = connect(DB_PATH, check_same_thread=False)
    conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT UNIQUE,
        name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        age INTEGER,
        gender TEXT,
        password TEXT
    );
    CREATE TABLE IF NOT EXISTS caretakers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caretaker_id TEXT UNIQUE,
        name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        assigned_patient TEXT,
        age INTEGER,
        gender TEXT,
        password TEXT
    );
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id TEXT UNIQUE,
        patient_id TEXT,
        name TEXT,
        dose TEXT,
        start_date TEXT,
        end_date TEXT,
        time TEXT,
        frequency TEXT,
        days TEXT
    );
    CREATE TABLE IF NOT EXISTS medicine_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id TEXT,
        patient_id TEXT,
        status TEXT,
        actor TEXT,
        ts TEXT
    );
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT,
        patient_id TEXT,
        taken_meds INTEGER,
        missed_meds INTEGER,
        date TEXT,
        caretaker_id TEXT
    );
    CREATE TABLE IF NOT EXISTS emergency_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id TEXT,
        sender_name TEXT,
        sender_email TEXT,
        patient_id TEXT,
        message TEXT,
        ts TEXT,
        success INTEGER,
        failures TEXT
    );
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        message TEXT,
        ts TEXT
    );
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page TEXT,
        rating INTEGER,
        comment TEXT,
        user_email TEXT,
        ts TEXT
    );
    CREATE TABLE IF NOT EXISTS alert_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id TEXT,
        patient_id TEXT,
        when_iso TEXT,
        alert_type TEXT,
        sent INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS full_screen_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id TEXT,
        patient_id TEXT,
        body TEXT,
        ts TEXT,
        shown INTEGER DEFAULT 0
    );
    """)
    conn.commit()
    conn.close()

def ensure_feedback_email_column():
    """Ensure the `feedback` table contains an `email` column. Safe to run multiple times."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(feedback)")
        cols = [r[1] for r in cur.fetchall()]
        if 'email' not in cols:
            cur.execute("ALTER TABLE feedback ADD COLUMN email TEXT")
            conn.commit()
        try:
            conn.close()
        except Exception:
            pass
    except Exception as e:
        # don't crash startup for migration hiccups; print for diagnostics
        print('Feedback column migration error:', e)

# initialize DB and ensure migrations
init_db()
ensure_feedback_email_column()

# ---------- utilities ----------
def gen_code(prefix, digits=4):
    return prefix + ''.join(random.choices(string.digits, k=digits))

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_email(to_email, subject, body):
    """Send email; if SMTP not configured, write to outbox file and return False."""
    if not SENDER_EMAIL or not APP_PASSWORD:
        outdir = os.path.join(BASE_DIR, "outbox")
        os.makedirs(outdir, exist_ok=True)
        fname = f"email_fallback_{int(time.time())}.txt"
        with open(os.path.join(outdir, fname), "w", encoding="utf-8") as f:
            f.write(f"TO: {to_email}\nSUBJECT: {subject}\n\n{body}")
        return False, "Saved to outbox"
    try:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15)
        server.login(SENDER_EMAIL, APP_PASSWORD)
        msg = MIMEText(body)
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())
        server.quit()
        return True, "Sent"
    except Exception as e:
        # fallback write
        outdir = os.path.join(BASE_DIR, "outbox")
        os.makedirs(outdir, exist_ok=True)
        fname = f"email_error_{int(time.time())}.txt"
        with open(os.path.join(outdir, fname), "w", encoding="utf-8") as f:
            f.write(f"ERROR: {e}\nTO: {to_email}\nSUBJECT: {subject}\n\n{body}")
        return False, str(e)

def send_text_as_email(to_number_or_email, body):
    """Send text by email (preferred). If number provided and SMS_TO_EMAIL_DOMAIN set, use it."""
    if "@" in str(to_number_or_email):
        return send_email(to_number_or_email, "MediAlert: Text Notification", body)
    else:
        if SMS_TO_EMAIL_DOMAIN:
            return send_email(f"{to_number_or_email}@{SMS_TO_EMAIL_DOMAIN}", "MediAlert SMS", body)
        # fallback: write file
        outdir = os.path.join(BASE_DIR, "outbox")
        os.makedirs(outdir, exist_ok=True)
        fname = f"sms_out_{int(time.time())}.txt"
        with open(os.path.join(outdir, fname), "w", encoding="utf-8") as f:
            f.write(f"To: {to_number_or_email}\n\n{body}")
        return False, "Saved to outbox"


# ---------- scheduling worker ----------
def _parse_hhmm(hhmm):
    try:
        parts = hhmm.split(":")
        h = int(parts[0]); m = int(parts[1])
        return h, m
    except Exception:
        return None

def _format_hhmm_ampm(hhmm):
    """Convert 'HH:MM' 24-hour to 'h:MM AM/PM'"""
    try:
        p = hhmm.split(":")
        h = int(p[0]); m = int(p[1])
        suffix = 'AM'
        if h >= 12:
            suffix = 'PM'
        hh = h % 12
        if hh == 0:
            hh = 12
        return f"{hh}:{m:02d} {suffix}"
    except Exception:
        return hhmm

def schedule_worker_loop():
    """Background loop: checks medicines and sends reminder emails at 5,1,0 minutes before scheduled time (UTC)."""
    while True:
        try:
            now = datetime.datetime.utcnow()
            conn = get_db()
            meds = conn.execute("SELECT * FROM medicines").fetchall()
            for med in meds:
                # check active date range
                try:
                    today = now.date()
                    sd = datetime.date.fromisoformat(med.get('start_date')) if med.get('start_date') else today
                    ed = datetime.date.fromisoformat(med.get('end_date')) if med.get('end_date') else today
                    if not (sd <= today <= ed):
                        continue
                except Exception:
                    pass
                if not med.get('time'):
                    continue
                parsed = _parse_hhmm(med.get('time'))
                if not parsed:
                    continue
                h,m = parsed
                sched_dt = datetime.datetime(now.year, now.month, now.day, h, m)
                # if scheduled for next day (time already passed), skip
                # compute three trigger times
                triggers = [ (sched_dt - datetime.timedelta(minutes=5), '5min'), (sched_dt - datetime.timedelta(minutes=1), '1min'), (sched_dt, 'ontime') ]
                for trig_time, atype in triggers:
                    # if now is within the last 35 seconds of trigger (to avoid duplicates)
                    if (now >= trig_time) and (now - trig_time <= datetime.timedelta(seconds=40)):
                        # check alert_logs to avoid duplicate send
                        exists = conn.execute('SELECT * FROM alert_logs WHERE med_id=? AND when_iso=? AND alert_type=?', (med.get('med_id'), trig_time.isoformat(), atype)).fetchone()
                        if exists:
                            continue
                        # send emails to patient and caretakers
                        patient = conn.execute('SELECT * FROM patients WHERE patient_id=?', (med.get('patient_id'),)).fetchone()
                        caretakers = conn.execute('SELECT * FROM caretakers WHERE assigned_patient=?', (med.get('patient_id'),)).fetchall()
                        # build plain text email
                        ct_names = ", ".join([ct.get('name') for ct in caretakers]) if caretakers else ''
                        sched_str = med.get('time')
                        sched_display = _format_hhmm_ampm(sched_str) if sched_str else ''
                        lines = []
                        lines.append(f"Patient ID: {patient.get('patient_id') if patient else med.get('patient_id')}")
                        lines.append(f"Patient Name: {patient.get('name') if patient else ''}")
                        lines.append(f"Caretaker(s): {ct_names}")
                        lines.append(f"Medicine: {med.get('name')}")
                        lines.append(f"Dose: {med.get('dose')}")
                        lines.append(f"Scheduled Time: {sched_display}")
                        # three instruction lines
                        lines.append("Instruction: Take medicine as prescribed.")
                        lines.append("Instruction: If you experience adverse effects, contact a caregiver or doctor immediately.")
                        lines.append("Instruction: Keep medicines in a safe place away from children.")
                        body = "\n".join(lines)
                        subject = f"MediAlert Reminder: {med.get('name')} at {sched_str} ({atype})"
                        # send to patient
                        if patient and patient.get('email'):
                            send_email(patient.get('email'), subject, body)
                        # send to caretakers
                        for ct in caretakers:
                            if ct.get('email'):
                                send_email(ct.get('email'), subject, body)
                            elif ct.get('phone'):
                                send_text_as_email(ct.get('phone'), body)
                        # log alert
                        conn.execute('INSERT INTO alert_logs (med_id,patient_id,when_iso,alert_type,sent) VALUES (?,?,?,?,?)', (med.get('med_id'), med.get('patient_id'), trig_time.isoformat(), atype, 1))
                        conn.commit()
                        # for ontime alerts, also create a full_screen_alerts entry so client can show it
                        if atype == 'ontime':
                            fs_body = f"{patient.get('name') if patient else ''} ({med.get('patient_id')}) - {med.get('name')} - {med.get('dose')} at {sched_display}"
                            conn.execute('INSERT INTO full_screen_alerts (med_id,patient_id,body,ts,shown) VALUES (?,?,?,?,?)', (med.get('med_id'), med.get('patient_id'), fs_body, datetime.datetime.utcnow().isoformat(), 0))
                            conn.commit()
            # close conn
            try:
                conn.close()
            except Exception:
                pass
        except Exception as e:
            print('Scheduler error', e)
        time.sleep(30)

def start_scheduler():
    t = threading.Thread(target=schedule_worker_loop, daemon=True)
    t.start()
# start scheduler at import so it runs in background for server processes
try:
    start_scheduler()
except Exception:
    pass

# ---------- context & language ----------
@app.context_processor
def inject_t():
    return dict(t=t, current_lang=session.get("lang", "en"))

@app.route("/set_lang/<lang>")
def set_lang(lang):
    if lang not in TRANSLATIONS:
        lang = "en"
    session["lang"] = lang
    return redirect(request.referrer or url_for("index"))

# ---------- routes ----------
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "patient")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        if role == "patient":
            user = conn.execute("SELECT * FROM patients WHERE email=?", (email,)).fetchone()
        else:
            user = conn.execute("SELECT * FROM caretakers WHERE email=?", (email,)).fetchone()
        if not user:
            flash("Invalid credentials", "danger")
            return render_template("login.html")
        stored = user.get("password")
        try:
            ok = check_password_hash(stored, password)
        except Exception:
            ok = (stored == password)
        if not ok:
            flash("Invalid credentials", "danger")
            return render_template("login.html")
        otp = generate_otp()
        session["login_attempt"] = {
            "role": role, "db_id": user.get("id"), "email": user.get("email"),
            "name": user.get("name"), "otp": otp
        }
        send_email(user.get("email"), "MediAlert Login OTP", f"Your login OTP is: {otp}")
        return render_template("verify_otp.html", role="login", email=user.get("email"))
    return render_template("login.html")

@app.route("/register_patient", methods=["GET", "POST"])
def register_patient():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "")
        age = request.form.get("age")
        gender = request.form.get("gender")
        pid = gen_code("P", 4)
        otp = generate_otp()
        session["reg_patient"] = {"name": name, "email": email, "password": password,
                                  "phone": phone, "age": age, "gender": gender,
                                  "patient_id": pid, "otp": otp}
        send_email(email, "MediAlert Registration OTP", f"Your OTP: {otp}\nProvisional Patient ID: {pid}")
        return render_template("verify_otp.html", role="patient", email=email)
    return render_template("register_patient.html")

@app.route("/register_caretaker", methods=["GET", "POST"])
def register_caretaker():
    conn = get_db()
    patients = conn.execute("SELECT patient_id,name FROM patients").fetchall()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "")
        assigned_patient = request.form.get("assigned_patient")
        age = request.form.get("age")
        gender = request.form.get("gender")
        cid = gen_code("C", 4)
        otp = generate_otp()
        session["reg_caretaker"] = {"name": name, "email": email, "password": password,
                                    "phone": phone, "assigned_patient": assigned_patient,
                                    "age": age, "gender": gender, "caretaker_id": cid, "otp": otp}
        send_email(email, "MediAlert Caretaker OTP", f"Your OTP: {otp}\nProvisional Caretaker ID: {cid}")
        return render_template("verify_otp.html", role="caretaker", email=email)
    return render_template("register_caretaker.html", patients=patients)

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    role = request.form.get("role")
    entered = request.form.get("otp", "").strip()
    if role == "patient" and "reg_patient" in session:
        data = session.get("reg_patient")
        if entered != data.get("otp"):
            flash("Invalid OTP", "danger")
            return redirect(url_for("register_patient"))
        conn = get_db()
        conn.execute(
            "INSERT INTO patients (patient_id,name,email,phone,age,gender,password) VALUES (?,?,?,?,?,?,?)",
            (data["patient_id"], data["name"], data["email"], data["phone"], data["age"], data["gender"],
             generate_password_hash(data["password"]))
        )
        conn.commit()
        session.pop("reg_patient", None)
        send_email(data["email"], "MediAlert Registration Complete", f"Welcome {data['name']}. Your Patient ID: {data['patient_id']}")
        flash(f"Registered. Patient ID: {data['patient_id']}", "success")
        return redirect(url_for("login"))
    if role == "caretaker" and "reg_caretaker" in session:
        data = session.get("reg_caretaker")
        if entered != data.get("otp"):
            flash("Invalid OTP", "danger")
            return redirect(url_for("register_caretaker"))
        conn = get_db()
        conn.execute(
            "INSERT INTO caretakers (caretaker_id,name,email,phone,assigned_patient,age,gender,password) VALUES (?,?,?,?,?,?,?,?)",
            (data["caretaker_id"], data["name"], data["email"], data["phone"], data["assigned_patient"], data["age"], data["gender"], generate_password_hash(data["password"]))
        )
        conn.commit()
        session.pop("reg_caretaker", None)
        send_email(data["email"], "MediAlert Caretaker Registration", f"Welcome {data['name']}. Your Caretaker ID: {data['caretaker_id']}")
        flash(f"Caretaker registered. ID: {data['caretaker_id']}", "success")
        return redirect(url_for("login"))
    if role == "login" and "login_attempt" in session:
        attempt = session.get("login_attempt")
        if entered != attempt.get("otp"):
            flash("Invalid OTP", "danger")
            return redirect(url_for("login"))
        session.pop("login_attempt", None)
        session["user"] = {"id": attempt.get("db_id"), "email": attempt.get("email"), "name": attempt.get("name"), "role": attempt.get("role")}
        if attempt.get("role") == "patient":
            return redirect(url_for("patient_dashboard"))
        else:
            return redirect(url_for("caretaker_dashboard"))
    flash("OTP session expired or invalid", "danger")
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# ---------- dashboards ----------
@app.route("/patient_dashboard")
def patient_dashboard():
    user = session.get("user")
    if not user or user.get("role") != "patient":
        return redirect(url_for("login"))
    conn = get_db()
    patient = conn.execute("SELECT * FROM patients WHERE id=?", (user.get("id"),)).fetchone()
    meds = conn.execute("SELECT * FROM medicines WHERE patient_id=?", (patient.get("patient_id"),)).fetchall()
    caretakers = conn.execute("SELECT * FROM caretakers WHERE assigned_patient=?", (patient.get("patient_id"),)).fetchall()
    return render_template("patient_dashboard.html", patient=patient, meds=meds, caretakers=caretakers)

@app.route("/caretaker_dashboard")
def caretaker_dashboard():
    user = session.get("user")
    if not user or user.get("role") != "caretaker":
        return redirect(url_for("login"))
    conn = get_db()
    ct = conn.execute("SELECT * FROM caretakers WHERE id=?", (user.get("id"),)).fetchone()
    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (ct.get("assigned_patient"),)).fetchone()
    meds = conn.execute("SELECT * FROM medicines WHERE patient_id=?", (ct.get("assigned_patient"),)).fetchall()
    taken = conn.execute("SELECT COUNT(*) as c FROM medicine_logs WHERE patient_id=? AND status='taken'", (ct.get("assigned_patient"),)).fetchone().get("c") or 0
    missed = conn.execute("SELECT COUNT(*) as c FROM medicine_logs WHERE patient_id=? AND status='missed'", (ct.get("assigned_patient"),)).fetchone().get("c") or 0
    total = len(meds)
    future = max(total - taken - missed, 0)
    chart = {"taken": taken, "missed": missed, "future": future}
    return render_template("caretaker_dashboard.html", caretaker=ct, patient=patient, meds=meds, chart=chart)

# ---------- medicines ----------
@app.route("/add_medicine", methods=["GET", "POST"])
def add_medicine():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        mid = gen_code("M", 4)
        patient_id = request.form.get("patient_id")
        # normalize time and optional AM/PM
        time_val = request.form.get("time")
        ampm = request.form.get("ampm")
        if time_val and ampm:
            try:
                hh, mm = map(int, time_val.split(':'))
                if ampm.upper() == 'PM' and hh < 12:
                    hh = hh + 12
                if ampm.upper() == 'AM' and hh == 12:
                    hh = 0
                time_val = f"{hh:02d}:{mm:02d}"
            except Exception:
                pass
        conn.execute("""INSERT INTO medicines (med_id,patient_id,name,dose,start_date,end_date,time,frequency,days)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                     (mid, patient_id, request.form.get("name"), request.form.get("dose"),
                      request.form.get("start_date"), request.form.get("end_date"),
                      time_val or request.form.get("time"), request.form.get("frequency"), ",".join(request.form.getlist("days"))))
        conn.commit()
        flash("Medicine added", "success")
        return redirect(url_for("patient_dashboard") if user.get("role") == "patient" else url_for("caretaker_dashboard"))
    patients = conn.execute("SELECT patient_id,name FROM patients").fetchall()
    return render_template("medicine_form.html", patients=patients)

@app.route("/medicine_action", methods=["POST"])
def medicine_action():
    data = request.form or request.json or {}
    med_id = data.get("med_id")
    action = data.get("action")
    actor = session.get("user", {}).get("name", "system")
    if not med_id or not action:
        return jsonify({"ok": False, "error": "missing params"}), 400
    conn = get_db()
    if action == "delete":
        conn.execute("DELETE FROM medicines WHERE med_id=?", (med_id,))
        conn.commit()
        return jsonify({"ok": True})
    if action in ("taken", "missed"):
        ts = datetime.datetime.utcnow().isoformat()
        med = conn.execute("SELECT * FROM medicines WHERE med_id=?", (med_id,)).fetchone()
        patient_id = med.get("patient_id") if med else None
        conn.execute("INSERT INTO medicine_logs (med_id,patient_id,status,actor,ts) VALUES (?,?,?,?,?)",
                     (med_id, patient_id, action, actor, ts))
        conn.commit()

        # Build text-email (10 lines + 3 lines instructions)
        patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
        caretakers = conn.execute("SELECT * FROM caretakers WHERE assigned_patient=?", (patient_id,)).fetchall()

        # Server-side validation: ensure required attributes exist before sending emails
        missing = []
        if not patient or not patient.get('patient_id'):
            missing.append('patient_id')
        if not patient or not patient.get('name'):
            missing.append('patient_name')
        if not caretakers or len(caretakers) == 0:
            missing.append('caretakers')
        if not med or not med.get('name'):
            missing.append('medicine_name')
        if not med or not med.get('med_id'):
            missing.append('medicine_id')
        if not med or not med.get('dose'):
            missing.append('dose')
        if not med or not med.get('time'):
            missing.append('time')

        if missing:
            # rollback the inserted log since required info is missing
            conn.execute('DELETE FROM medicine_logs WHERE med_id=? AND ts=?', (med_id, ts))
            conn.commit()
            err = {"ok": False, "error": "missing_fields", "missing": missing}
            return jsonify(err), 400
        # day name from date if available
        dayname = ""
        try:
            if med.get("start_date"):
                d = datetime.datetime.fromisoformat(med.get("start_date"))
                dayname = d.strftime("%A")
        except Exception:
            dayname = ""

        lines = []
        lines.append(f"Patient ID: {patient.get('patient_id')}")
        lines.append(f"Patient Name: {patient.get('name')}")
        ct_names = ", ".join([ct.get("name") for ct in caretakers]) if caretakers else ""
        lines.append(f"Caretaker(s): {ct_names}")
        # include acting user (who pressed the button) when available
        if actor:
            lines.append(f"Actioned By: {actor}")
        lines.append(f"Medicine: {med.get('name')}")
        lines.append(f"Medicine ID: {med.get('med_id')}")
        lines.append(f"Dose: {med.get('dose')}")
        lines.append(f"Date: {med.get('start_date') or ''}")
        lines.append(f"Time: {med.get('time') or ''}")
        lines.append(f"Day: {dayname}")
        lines.append(f"Status: {action.upper()}")
        # three instruction lines
        lines.append("Instruction: If missed, contact caretaker immediately.")
        lines.append("Instruction: Store medicines safely and follow schedule.")
        lines.append("Instruction: For emergencies call provided numbers on Emergency page.")

        body = "\n".join(lines)
        subject = f"MediAlert: {patient.get('name')} - {med.get('name')} - {action.upper()}"

        # Send to patient email
        if patient.get("email"):
            send_email(patient.get("email"), subject, body)
        # Send to caretakers (text as email preferred)
        for ct in caretakers:
            if ct.get("email"):
                send_email(ct.get("email"), subject, body)
            elif ct.get("phone"):
                send_text_as_email(ct.get("phone"), body)

        # return med details so client can show on-screen/voice alert immediately
        med_info = {"med_id": med.get("med_id"), "name": med.get("name"), "dose": med.get("dose"), "time": med.get("time")}
        ct_emails = [ct.get("email") or ct.get("phone") for ct in caretakers]
        return jsonify({"ok": True, "med": med_info, "patient_email": patient.get("email"), "caretaker_contacts": ct_emails})
    return jsonify({"ok": False, "error": "unknown action"}), 400

# ---------- reports ----------
@app.route("/report", methods=["GET", "POST"])
def report():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        pid = request.form.get("patient_id")
        recipient_name = request.form.get("recipient_name")
        recipient_email = request.form.get("recipient_email")
        period = request.form.get("period", "daily")
        if not recipient_email or not recipient_name:
            # For AJAX requests return JSON
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"ok": False, "error": "missing_recipient"}), 400
            flash("Please provide recipient name and email", "danger")
            return redirect(url_for("report"))
        now = datetime.datetime.utcnow()
        since = now - datetime.timedelta(days=1 if period == "daily" else 7)
        logs = conn.execute("SELECT l.*, m.name AS med_name, m.dose FROM medicine_logs l LEFT JOIN medicines m ON m.med_id=l.med_id WHERE l.patient_id=? AND l.ts>=?", (pid, since.isoformat())).fetchall()
        meds = conn.execute("SELECT * FROM medicines WHERE patient_id=?", (pid,)).fetchall()
        caretakers = conn.execute("SELECT * FROM caretakers WHERE assigned_patient=?", (pid,)).fetchall()
        patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
        # Server-side validation: required attributes for a meaningful report
        missing = []
        if not patient or not patient.get('patient_id'):
            missing.append('patient_id')
        if not patient or not patient.get('name'):
            missing.append('patient_name')
        if not caretakers or len(caretakers) == 0:
            missing.append('caretakers')
        if not meds or len(meds) == 0:
            missing.append('medicines')

        # check each medicine for required fields
        med_missing = []
        for m in meds:
            if not m.get('name'):
                med_missing.append('medicine_name')
            if not m.get('med_id'):
                med_missing.append('medicine_id')
            if not m.get('dose'):
                med_missing.append('dose')
            if not m.get('time'):
                med_missing.append('time')
        if med_missing:
            missing.extend(list(set(med_missing)))

        if missing:
            # If AJAX, return JSON describing missing fields
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"ok": False, "error": "missing_fields", "missing": missing}), 400
            flash(f"Cannot send report - missing data: {', '.join(missing)}", "danger")
            return redirect(url_for('report'))
        # Build 10-line report
        lines = []
        lines.append(f"{patient.get('name')} ({patient.get('patient_id')})")
        lines.append(f"Email: {patient.get('email')}, Phone: {patient.get('phone')}")
        # list up to 5 medicines
        for m in meds[:5]:
            lines.append(f"Med: {m.get('name')} (ID:{m.get('med_id')}) dose {m.get('dose')} at {m.get('time')}")
        taken = len([l for l in logs if l.get("status") == "taken"])
        missed = len([l for l in logs if l.get("status") == "missed"])
        lines.append(f"Taken: {taken}")
        lines.append(f"Missed: {missed}")
        lines.append("Notes: Follow schedule. Contact caretaker when in doubt.")
        while len(lines) < 10:
            lines.append("")
        body = "\n".join(lines)
        # send to provided recipient
        ok_rec, info_rec = send_email(recipient_email, f"MediAlert Report ({pid})", f"Dear {recipient_name},\n\n{body}\n\nRegards,\nMediAlert")
        # also send to patient and caretakers
        if patient and patient.get('email'):
            send_email(patient.get('email'), f"MediAlert Report ({pid})", f"Dear {patient.get('name')},\n\n{body}\n\nRegards,\nMediAlert")
        for ct in caretakers:
            if ct.get('email'):
                send_email(ct.get('email'), f"MediAlert Report ({pid})", f"Dear {ct.get('name')},\n\n{body}\n\nRegards,\nMediAlert")
            elif ct.get('phone'):
                send_text_as_email(ct.get('phone'), body)

        # If AJAX request, return JSON success so client can show on-screen/voice alert immediately
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"ok": True, "message": f"Report sent to {recipient_email}", "recipient": recipient_email})
        # persist
        rpt_id = gen_code("R", 4)
        conn.execute("INSERT INTO reports (report_id,patient_id,taken_meds,missed_meds,date) VALUES (?,?,?,?,?)",
                     (rpt_id, pid, taken, missed, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        flash(f"Report sent to {recipient_email}", "report")
        return redirect(url_for("patient_dashboard") if user.get("role") == "patient" else url_for("caretaker_dashboard"))
    patients = conn.execute("SELECT patient_id,name FROM patients").fetchall()
    return render_template("report.html", patients=patients)

@app.route("/reports_list")
def reports_list():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    conn = get_db()
    rows = conn.execute("SELECT * FROM reports ORDER BY date DESC LIMIT 50").fetchall()
    return render_template("reports_list.html", reports=rows)


@app.route("/rate", methods=["POST"])
def rate():
    page = request.form.get("page") or request.json.get("page") if request.json else None
    rating = int(request.form.get("rating") or (request.json.get("rating") if request.json else 0))
    comment = request.form.get("comment") or (request.json.get("comment") if request.json else "")
    user_email = request.form.get("email") or (request.json.get("email") if request.json else "")
    if not page or not rating:
        return jsonify({"ok": False, "error": "missing"}), 400
    conn = get_db()
    conn.execute("INSERT INTO ratings (page,rating,comment,user_email,ts) VALUES (?,?,?,?,?)",
                 (page, rating, comment, user_email, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    return jsonify({"ok": True})


@app.route("/api/report_details/<patient_id>")
def api_report_details(patient_id):
    conn = get_db()
    patient = conn.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
    caretakers = conn.execute("SELECT * FROM caretakers WHERE assigned_patient=?", (patient_id,)).fetchall()
    meds = conn.execute("SELECT * FROM medicines WHERE patient_id=?", (patient_id,)).fetchall()
    return jsonify({"patient": patient, "caretakers": caretakers, "medicines": meds})

# ---------- emergency & feedback ----------
@app.route("/emergency", methods=["GET", "POST"])
def emergency():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        msg = request.form.get("message") or "Emergency: please contact patient immediately."
        if user.get("role") == "patient":
            p = conn.execute("SELECT * FROM patients WHERE id=?", (user.get("id"),)).fetchone()
            pid = p.get("patient_id")
            pname = p.get("name")
        else:
            ct = conn.execute("SELECT * FROM caretakers WHERE id=?", (user.get("id"),)).fetchone()
            pid = ct.get("assigned_patient")
            p = conn.execute("SELECT * FROM patients WHERE patient_id=?", (pid,)).fetchone()
            pname = p.get("name") if p else None
        caretakers = conn.execute("SELECT * FROM caretakers WHERE assigned_patient=?", (pid,)).fetchall()
        subject = f"MediAlert EMERGENCY for {pname} (ID:{pid})"
        body = f"Emergency for patient {pname} (ID:{pid}).\nMessage: {msg}\nSent by: {user.get('name') or user.get('email')}"
        failed = []
        for ct in caretakers:
            ok, _ = send_email(ct.get("email"), subject, body) if ct.get("email") else send_text_as_email(ct.get("phone"), body)
            if not ok:
                failed.append(ct.get("email") or ct.get("phone"))
        conn.execute("INSERT INTO emergency_logs (sender_id,sender_name,sender_email,patient_id,message,ts,success,failures) VALUES (?,?,?,?,?,?,?,?)",
                     (user.get("id"), user.get("name"), user.get("email"), pid, msg, datetime.datetime.utcnow().isoformat(), 0 if failed else 1, ",".join(failed)))
        conn.commit()
        if failed:
            flash("Emergency attempted; some sends failed and were saved to outbox.", "warning")
        else:
            flash("Emergency sent to caretakers.", "success")
        return redirect(url_for("patient_dashboard") if user.get("role") == "patient" else url_for("caretaker_dashboard"))
    important = [
        {"name": "108 Ambulance", "phone": "108", "href": "tel:108"},
        {"name": "Local Health Officer", "phone": "+911234567890", "href": "tel:+911234567890"},
        {"name": "City Hospital", "phone": "+911112223334", "href": "tel:+911112223334"}
    ]
    return render_template("emergency.html", important=important)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")
        rating = request.form.get("rating")
        conn = get_db()
        conn.execute("INSERT INTO feedback (name,email,phone,message,ts) VALUES (?,?,?,?,?)",
                     (name, email, phone, message, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        # store rating if present
        try:
            if rating:
                conn.execute("INSERT INTO ratings (page,rating,comment,user_email,ts) VALUES (?,?,?,?,?)",
                             ('feedback', int(rating), message or '', email or '', datetime.datetime.utcnow().isoformat()))
                conn.commit()
        except Exception:
            pass
        if email:
            send_email(email, "Thank you for feedback", "Thanks for your feedback. We appreciate it.")
        flash("Thanks for your feedback", "success")
        return redirect(url_for("index"))
    return render_template("feedback.html")

# ---------- API for alerts ----------
@app.route("/api/medicines_now")
def medicines_now():
    """Return medicine due now (minute precision). Called by client JS repeatedly."""
    conn = get_db()
    now = datetime.datetime.utcnow()
    # compare times in HH:MM, check for medicines scheduled for today and matching current HH:MM
    hhmm = now.strftime("%H:%M")
    rows = conn.execute("SELECT m.*, p.name AS patient_name, p.patient_id AS pid, p.email AS patient_email FROM medicines m LEFT JOIN patients p ON p.patient_id=m.patient_id WHERE m.time=?",(hhmm,)).fetchall()
    # Also ensure start_date <= today <= end_date when present
    def active(m):
        try:
            today = now.date()
            sd = datetime.date.fromisoformat(m.get("start_date")) if m.get("start_date") else today
            ed = datetime.date.fromisoformat(m.get("end_date")) if m.get("end_date") else today
            return sd <= today <= ed
        except Exception:
            return True
    rows = [r for r in rows if active(r)]
    if rows:
        # return first due med
        m = rows[0]
        return jsonify({"alert": True, "medicine": m})
    return jsonify({"alert": False})

# ---------- chart api ----------
@app.route("/api/chart/<patient_id>")
def api_chart(patient_id):
    conn = get_db()
    taken = conn.execute("SELECT COUNT(*) as c FROM medicine_logs WHERE patient_id=? AND status='taken'", (patient_id,)).fetchone().get("c") or 0
    missed = conn.execute("SELECT COUNT(*) as c FROM medicine_logs WHERE patient_id=? AND status='missed'", (patient_id,)).fetchone().get("c") or 0
    total = conn.execute("SELECT COUNT(*) as c FROM medicines WHERE patient_id=?", (patient_id,)).fetchone().get("c") or 0
    future = max(total - taken - missed, 0)
    return jsonify({"taken": taken, "missed": missed, "future": future})


# ---------- alerts endpoints ----------
@app.route('/api/alerts_pending')
def api_alerts_pending():
    conn = get_db()
    # return alerts with joined medicine and patient details for richer client display
    rows = conn.execute("""
        SELECT f.id, f.med_id, f.patient_id, f.body, f.ts,
               m.name AS med_name, m.dose AS med_dose, m.time AS med_time, m.days AS med_days,
               p.name AS patient_name, p.patient_id AS pid, p.email AS patient_email
        FROM full_screen_alerts f
        LEFT JOIN medicines m ON m.med_id = f.med_id
        LEFT JOIN patients p ON p.patient_id = f.patient_id
        WHERE f.shown = 0
        ORDER BY f.ts ASC
    """).fetchall()
    return jsonify({'alerts': rows})


@app.route('/api/alerts_mark_shown', methods=['POST'])
def api_alerts_mark_shown():
    data = request.json or {}
    aid = data.get('id')
    if not aid:
        return jsonify({'ok': False}), 400
    conn = get_db()
    conn.execute('UPDATE full_screen_alerts SET shown=1 WHERE id=?', (aid,))
    conn.commit()
    return jsonify({'ok': True})

# ---------- static audio route ----------
@app.route("/static/audio/<path:filename>")
def audio(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static", "audio"), filename)

# ---------- about ----------
@app.route("/about")
def about():
    return render_template("about.html")


@app.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    conn = get_db()
    if user.get('role') == 'patient':
        profile = conn.execute('SELECT * FROM patients WHERE id=?', (user.get('id'),)).fetchone()
    else:
        profile = conn.execute('SELECT * FROM caretakers WHERE id=?', (user.get('id'),)).fetchone()
    return render_template('profile.html', profile=profile)

# ---------- run ----------
if __name__ == "__main__":
    # In development Flask restarts when it detects file changes (useful while editing).
    # To avoid repeated automatic restarts (for example when files are being modified by the app or editor),
    # set use_reloader=False. Keep debug=True to keep the interactive debugger when needed.
    # start background scheduler for reminders (best-effort)
    try:
        start_scheduler()
    except NameError:
        pass
    app.run(debug=True, use_reloader=False, port=5000)
