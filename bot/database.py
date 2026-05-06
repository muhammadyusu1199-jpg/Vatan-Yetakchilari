"""
database.py — SQLite ma'lumotlar bazasi (to'liq versiya)
"""

import sqlite3
import hashlib
import os
import sys
from datetime import date, datetime


try:
    from config import DB_NAME
except ImportError:
    # Agar config fayli topilmasa, Railway Variables'dan oladi
    # Standart qiymat sifatida 'database.db' ishlatiladi
    DB_NAME = os.getenv("DB_NAME", "database.db")


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    """Parolni SHA256 bilan xeshlash."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY,
            username      TEXT UNIQUE,
            password_hash TEXT,
            first_name    TEXT NOT NULL,
            last_name     TEXT,
            age           INTEGER,
            phone         TEXT,
            school_grade  INTEGER,
            coins         INTEGER DEFAULT 0,
            registered_at TEXT DEFAULT (date('now')),
            is_active     INTEGER DEFAULT 1,
            last_daily_bonus TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            place_id    TEXT NOT NULL,
            quiz_date   TEXT NOT NULL,
            attempt_num INTEGER DEFAULT 1,
            score       INTEGER DEFAULT 0,
            completed   INTEGER DEFAULT 0,
            coin_earned INTEGER DEFAULT 0,
            bonus_given INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_rewards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            reward_date TEXT NOT NULL,
            coins_earned INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE (user_id, reward_date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS shop_orders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            item_id    TEXT NOT NULL,
            item_name  TEXT NOT NULL,
            cost_coins INTEGER NOT NULL,
            ordered_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_jokers (
            user_id    INTEGER NOT NULL,
            joker_type TEXT NOT NULL,
            count      INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, joker_type),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_joker_usage (
            user_id    INTEGER NOT NULL,
            joker_type TEXT NOT NULL,
            used_date  TEXT NOT NULL,
            used_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, joker_type, used_date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_progress (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            place_id   TEXT NOT NULL,
            learned_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE (user_id, place_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            plan_id    TEXT NOT NULL,
            started_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            coin_spent INTEGER NOT NULL,
            is_active  INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS place_bonus_log (
            user_id  INTEGER NOT NULL,
            place_id TEXT NOT NULL,
            log_date TEXT NOT NULL,
            PRIMARY KEY (user_id, place_id, log_date)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Ma'lumotlar bazasi jadvallari yaratildi.")


# ===================== FOYDALANUVCHI =====================

def register_user(user_id, tg_username, first_name, last_name,
                  age, phone, school_grade, username, password):
    """username + password bilan ro'yxatdan o'tkazish."""
    conn = get_connection()
    c = conn.cursor()
    pw_hash = hash_password(password)
    c.execute("""
        INSERT OR REPLACE INTO users
        (user_id, username, password_hash, first_name, last_name,
         age, phone, school_grade, coins)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?,
            COALESCE((SELECT coins FROM users WHERE user_id = ?), 0))
    """, (user_id, username, pw_hash, first_name, last_name,
          age, phone, school_grade, user_id))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user


def get_user_by_username(username: str):
    """Sayt login uchun — username bo'yicha topish."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def check_login(username: str, password: str):
    """
    username + password tekshiruvi.
    To'g'ri bo'lsa user qaytaradi, yo'q bo'lsa None.
    """
    user = get_user_by_username(username)
    if not user:
        return None
    if user['password_hash'] == hash_password(password):
        return user
    return None


def is_username_taken(username: str, exclude_user_id=None) -> bool:
    conn = get_connection()
    c = conn.cursor()
    if exclude_user_id:
        c.execute("SELECT user_id FROM users WHERE username=? AND user_id!=?",
                  (username, exclude_user_id))
    else:
        c.execute("SELECT user_id FROM users WHERE username=?", (username,))
    taken = c.fetchone() is not None
    conn.close()
    return taken


def is_registered(user_id):
    return get_user(user_id) is not None


def get_user_coins(user_id):
    user = get_user(user_id)
    return user['coins'] if user else 0


def add_coins(user_id, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def deduct_coins(user_id, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row or row['coins'] < amount:
        conn.close()
        return False
    c.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()
    return True


# ===================== KUNLIK BONUS =====================
# Obunasiz: 100 coin/kun
# Pro:      250 coin/kun
# Plus:     250 coin/kun (saytda ko'rsatiladi, plan_id dan olinadi)
# Ultra:    550 coin/kun
# (shared_config.py da belgilangan)

DAILY_BONUS_MAP = {
    None:         100,
    "pro":        250,
    "plus":       250,
    "ultra_plus": 550,
}


def claim_daily_bonus(user_id) -> dict:
    """
    Kunlik bonusni beradi.
    Qaytaradi: {"given": True/False, "amount": int, "already": bool}
    """
    today = str(date.today())
    user  = get_user(user_id)
    if not user:
        return {"given": False, "amount": 0, "already": False}

    if user['last_daily_bonus'] == today:
        return {"given": False, "amount": 0, "already": True}

    sub    = get_active_subscription(user_id)
    plan   = sub['plan_id'] if sub else None
    amount = DAILY_BONUS_MAP.get(plan, 100)

    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET coins=coins+?, last_daily_bonus=? WHERE user_id=?",
              (amount, today, user_id))
    conn.commit()
    conn.close()
    return {"given": True, "amount": amount, "already": False}


# ===================== JOY BONUSI (10/10 uchun) =====================

def give_place_bonus(user_id, place_id) -> dict:
    """
    Birinchi marta 10/10 ball olganda bonus beradi:
    - 2 ta 50/50 joker
    - 1 ta qo'shimcha urinish (extra_retry)
    - 50 coin
    Kuniga 1 marta (bir joy uchun).
    """
    today = str(date.today())
    conn  = get_connection()
    c     = conn.cursor()

    c.execute("""
        SELECT 1 FROM place_bonus_log
        WHERE user_id=? AND place_id=? AND log_date=?
    """, (user_id, place_id, today))
    if c.fetchone():
        conn.close()
        return {"given": False}

    # Bonus berish
    # 1. 2 ta joker qo'shish
    c.execute("""
        INSERT INTO user_jokers (user_id, joker_type, count) VALUES (?,?,2)
        ON CONFLICT(user_id, joker_type) DO UPDATE SET count=count+2
    """, (user_id, "fifty_fifty"))

    # 2. 1 ta qo'shimcha urinish (extra_retry jokeri)
    c.execute("""
        INSERT INTO user_jokers (user_id, joker_type, count) VALUES (?,?,1)
        ON CONFLICT(user_id, joker_type) DO UPDATE SET count=count+1
    """, (user_id, "extra_retry"))

    # 3. 50 coin
    c.execute("UPDATE users SET coins=coins+50 WHERE user_id=?", (user_id,))

    # 4. Log
    c.execute("INSERT OR IGNORE INTO place_bonus_log VALUES (?,?,?)",
              (user_id, place_id, today))

    conn.commit()
    conn.close()
    return {"given": True, "jokers": 2, "retries": 1, "coins": 50}


# ===================== OBUNA =====================

def get_active_subscription(user_id):
    today = str(date.today())
    conn  = get_connection()
    c     = conn.cursor()
    c.execute("""
        SELECT * FROM subscriptions
        WHERE user_id=? AND is_active=1 AND expires_at>=?
        ORDER BY expires_at DESC LIMIT 1
    """, (user_id, today))
    sub = c.fetchone()
    conn.close()
    return sub


def get_plan_limits(user_id):
    try:
        from shared_config import SUBSCRIPTION_PLANS
    except ImportError:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from shared_config import SUBSCRIPTION_PLANS

    sub = get_active_subscription(user_id)
    if not sub:
        return {"joker_daily": 0, "quiz_retry": 1, "bonus_coin": 0, "plan_id": None}
    plan = SUBSCRIPTION_PLANS.get(sub["plan_id"], {})
    return {
        "joker_daily": plan.get("joker_daily", 0),
        "quiz_retry":  plan.get("quiz_retry",  1),
        "bonus_coin":  plan.get("bonus_coin",  0),
        "plan_id":     sub["plan_id"],
    }


# ===================== QUIZ =====================

def get_today_quiz_count(user_id, place_id):
    today = str(date.today())
    conn  = get_connection()
    c     = conn.cursor()
    c.execute("""
        SELECT COUNT(*) as cnt FROM quiz_results
        WHERE user_id=? AND place_id=? AND quiz_date=? AND completed=1
    """, (user_id, place_id, today))
    cnt = c.fetchone()['cnt']
    conn.close()
    return cnt


def get_today_quiz(user_id, place_id):
    today = str(date.today())
    conn  = get_connection()
    c     = conn.cursor()
    c.execute("""
        SELECT * FROM quiz_results
        WHERE user_id=? AND place_id=? AND quiz_date=?
        ORDER BY attempt_num DESC LIMIT 1
    """, (user_id, place_id, today))
    result = c.fetchone()
    conn.close()
    return result


def can_retry_quiz(user_id, place_id):
    """
    extra_retry jokerini ham hisobga oladi.
    Qaytaradi: (can: bool, done: int, limit: int/-1)
    """
    limits      = get_plan_limits(user_id)
    retry_limit = limits["quiz_retry"]
    done_count  = get_today_quiz_count(user_id, place_id)

    if retry_limit == -1:
        return True, done_count, -1

    # extra_retry jokerini tekshirish
    extra = get_joker_count(user_id, "extra_retry")
    effective_limit = retry_limit + extra

    return done_count < effective_limit, done_count, effective_limit


def save_quiz_result(user_id, place_id, score, coin_earned):
    today = str(date.today())
    conn  = get_connection()
    c     = conn.cursor()
    c.execute("""
        SELECT COALESCE(MAX(attempt_num),0)+1 as n
        FROM quiz_results WHERE user_id=? AND place_id=? AND quiz_date=?
    """, (user_id, place_id, today))
    next_num = c.fetchone()['n']
    c.execute("""
        INSERT INTO quiz_results
        (user_id, place_id, quiz_date, attempt_num, score, completed, coin_earned)
        VALUES (?,?,?,?,?,1,?)
    """, (user_id, place_id, today, next_num, score, coin_earned))
    conn.commit()
    conn.close()
    if coin_earned > 0:
        add_coins(user_id, coin_earned)


def check_and_award_daily_coin(user_id):
    from places_data import PLACES
    today = str(date.today())
    conn  = get_connection()
    c     = conn.cursor()
    c.execute("SELECT id FROM daily_rewards WHERE user_id=? AND reward_date=?",
              (user_id, today))
    if c.fetchone():
        conn.close()
        return False
    c.execute("""
        SELECT COUNT(DISTINCT place_id) as cnt FROM quiz_results
        WHERE user_id=? AND quiz_date=? AND score=10
    """, (user_id, today))
    perfect = c.fetchone()['cnt']
    conn.close()
    if perfect >= len(PLACES):
        conn = get_connection()
        c    = conn.cursor()
        c.execute("INSERT OR IGNORE INTO daily_rewards (user_id, reward_date, coins_earned) VALUES (?,?,1000)",
                  (user_id, today))
        conn.commit()
        conn.close()
        add_coins(user_id, 1000)
        return True
    return False


def get_user_quiz_stats(user_id):
    conn = get_connection()
    c    = conn.cursor()
    c.execute("""
        SELECT COUNT(*) as total_quizzes,
               SUM(score) as total_score,
               SUM(coin_earned) as total_coins_from_quiz,
               COUNT(CASE WHEN score=10 THEN 1 END) as perfect_scores
        FROM quiz_results WHERE user_id=?
    """, (user_id,))
    stats = c.fetchone()
    conn.close()
    return stats


# ===================== JOKER =====================

def get_joker_count(user_id, joker_type):
    conn = get_connection()
    c    = conn.cursor()
    c.execute("SELECT count FROM user_jokers WHERE user_id=? AND joker_type=?",
              (user_id, joker_type))
    row = c.fetchone()
    conn.close()
    return row['count'] if row else 0


def use_joker(user_id, joker_type):
    limits     = get_plan_limits(user_id)
    plan_daily = limits["joker_daily"]

    if plan_daily == -1:
        return True

    purchased = get_joker_count(user_id, joker_type)
    if purchased > 0:
        conn = get_connection()
        c    = conn.cursor()
        c.execute("UPDATE user_jokers SET count=count-1 WHERE user_id=? AND joker_type=?",
                  (user_id, joker_type))
        conn.commit()
        conn.close()
        return True

    if plan_daily > 0:
        today = str(date.today())
        conn  = get_connection()
        c     = conn.cursor()
        c.execute("""
            SELECT used_count FROM daily_joker_usage
            WHERE user_id=? AND joker_type=? AND used_date=?
        """, (user_id, joker_type, today))
        row       = c.fetchone()
        used_today = row['used_count'] if row else 0
        if used_today < plan_daily:
            c.execute("""
                INSERT INTO daily_joker_usage (user_id, joker_type, used_date, used_count)
                VALUES (?,?,?,1)
                ON CONFLICT(user_id, joker_type, used_date)
                DO UPDATE SET used_count=used_count+1
            """, (user_id, joker_type, today))
            conn.commit()
            conn.close()
            return True
        conn.close()

    return False


def get_jokers_left_today(user_id, joker_type="fifty_fifty"):
    limits     = get_plan_limits(user_id)
    plan_daily = limits["joker_daily"]
    if plan_daily == -1:
        return -1
    purchased = get_joker_count(user_id, joker_type)
    today = str(date.today())
    conn  = get_connection()
    c     = conn.cursor()
    try:
        c.execute("""
            SELECT used_count FROM daily_joker_usage
            WHERE user_id=? AND joker_type=? AND used_date=?
        """, (user_id, joker_type, today))
        row  = c.fetchone()
        used = row['used_count'] if row else 0
    except Exception:
        used = 0
    conn.close()
    return purchased + max(0, plan_daily - used)


def buy_joker(user_id, joker_type, item_name, cost_coins):
    if not deduct_coins(user_id, cost_coins):
        return False
    conn = get_connection()
    c    = conn.cursor()
    c.execute("""
        INSERT INTO user_jokers (user_id, joker_type, count) VALUES (?,?,1)
        ON CONFLICT(user_id, joker_type) DO UPDATE SET count=count+1
    """, (user_id, joker_type))
    c.execute("INSERT INTO shop_orders (user_id, item_id, item_name, cost_coins) VALUES (?,?,?,?)",
              (user_id, joker_type, item_name, cost_coins))
    conn.commit()
    conn.close()
    return True


# ===================== DO'KON =====================

def buy_item(user_id, item_id, item_name, cost_coins):
    if deduct_coins(user_id, cost_coins):
        conn = get_connection()
        c    = conn.cursor()
        c.execute("INSERT INTO shop_orders (user_id, item_id, item_name, cost_coins) VALUES (?,?,?,?)",
                  (user_id, item_id, item_name, cost_coins))
        conn.commit()
        conn.close()
        return True
    return False


def get_user_purchases(user_id):
    conn = get_connection()
    c    = conn.cursor()
    c.execute("SELECT * FROM shop_orders WHERE user_id=? ORDER BY ordered_at DESC",
              (user_id,))
    p = c.fetchall()
    conn.close()
    return p


# ===================== O'RGANISH =====================

def mark_place_learned(user_id, place_id):
    conn = get_connection()
    c    = conn.cursor()
    c.execute("INSERT OR IGNORE INTO learning_progress (user_id, place_id) VALUES (?,?)",
              (user_id, place_id))
    conn.commit()
    conn.close()


def get_learned_places(user_id):
    conn = get_connection()
    c    = conn.cursor()
    c.execute("SELECT place_id FROM learning_progress WHERE user_id=?", (user_id,))
    places = [row['place_id'] for row in c.fetchall()]
    conn.close()
    return places


# ===================== ADMIN =====================

def get_all_users():
    conn = get_connection()
    c    = conn.cursor()
    c.execute("""
        SELECT u.*,
               COUNT(DISTINCT qr.place_id) as quizzes_done,
               COALESCE(SUM(qr.score),0) as total_score
        FROM users u
        LEFT JOIN quiz_results qr ON u.user_id=qr.user_id
        GROUP BY u.user_id ORDER BY u.coins DESC
    """)
    users = c.fetchall()
    conn.close()
    return users


def get_total_stats():
    conn = get_connection()
    c    = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM users"); total_users = c.fetchone()['cnt']
    c.execute("SELECT COUNT(*) as cnt FROM quiz_results WHERE completed=1"); total_quizzes = c.fetchone()['cnt']
    c.execute("SELECT SUM(coins) as t FROM users"); r = c.fetchone(); total_coins = r['t'] or 0
    c.execute("SELECT COUNT(*) as cnt FROM quiz_results WHERE quiz_date=date('now')"); today_q = c.fetchone()['cnt']
    c.execute("SELECT COUNT(*) as cnt FROM users WHERE registered_at=date('now')"); today_u = c.fetchone()['cnt']
    conn.close()
    return {'total_users': total_users, 'total_quizzes': total_quizzes,
            'total_coins': total_coins, 'today_quizzes': today_q, 'today_new_users': today_u}


def get_top_users(limit=10):
    conn = get_connection()
    c    = conn.cursor()
    c.execute("SELECT first_name, last_name, school_grade, coins FROM users ORDER BY coins DESC LIMIT ?",
              (limit,))
    top = c.fetchall()
    conn.close()
    return top
