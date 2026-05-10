import psycopg2
from psycopg2 import pool
import hashlib
import os
import streamlit as st
from contextlib import contextmanager

# Veritabanı URL'sini al (.env veya Secrets)
def load_database_url():
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    try:
        return st.secrets.get("DATABASE_URL")
    except Exception:
        return None

DATABASE_URL = load_database_url()

@st.cache_resource(show_spinner=False)
def _get_connection_pool(database_url):
    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=database_url,
        sslmode='require',
        connect_timeout=10
    )

def get_connection():
    """PostgreSQL veritabanına güvenli bağlantı açar."""
    if not DATABASE_URL:
        st.error("Veritabanı bağlantı adresi (DATABASE_URL) bulunamadı!")
        return None
    try:
        db_pool = _get_connection_pool(DATABASE_URL)
        conn = db_pool.getconn()
        if conn.closed:
            db_pool.putconn(conn, close=True)
            conn = db_pool.getconn()
        return conn
    except Exception as e:
        st.error(f"Veritabanı Bağlantı Hatası: {e}")
        return None

def release_connection(conn):
    if not conn:
        return
    try:
        _get_connection_pool(DATABASE_URL).putconn(conn)
    except Exception:
        conn.close()

@contextmanager
def db_cursor(commit=False):
    conn = get_connection()
    if not conn:
        yield None
        return

    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_connection(conn)

@st.cache_resource(show_spinner=False)
def _init_db_once(database_url):
    with db_cursor(commit=True) as c:
        if not c:
            return False
        # Kullanıcılar Tablosu
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        ''')
        # Hatalar Tablosu
        c.execute('''
            CREATE TABLE IF NOT EXISTS mistakes (
                username TEXT,
                question_id TEXT,
                chapter TEXT,
                mistake_count INTEGER DEFAULT 1,
                FOREIGN KEY(username) REFERENCES users(username)
            )
        ''')
        # Mevcut veriye dokunmadan sık kullanılan sorguları hızlandırır.
        c.execute('CREATE INDEX IF NOT EXISTS idx_mistakes_username ON mistakes(username)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_mistakes_username_question ON mistakes(username, question_id)')
        return True

def init_db():
    """Tabloları oluşturur (Eğer yoksa)."""
    if not DATABASE_URL:
        st.error("Veritabanı bağlantı adresi (DATABASE_URL) bulunamadı!")
        return False
    try:
        return _init_db_once(DATABASE_URL)
    except Exception as e:
        st.error(f"Veritabanı hazırlama hatası: {e}")
        return False

# --- GÜVENLİK (HASHING) ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hash(password) == hashed_text:
        return hashed_text
    return False

# --- KULLANICI İŞLEMLERİ ---
def add_user(username, email, password):
    # Şifre Uzunluk Kontrolü
    if len(password) < 6:
        return "pass_len_error"

    try:
        with db_cursor(commit=True) as c:
            if not c:
                return "db_error"

            # Kullanıcı Adı Var mı?
            c.execute('SELECT 1 FROM users WHERE username = %s', (username,))
            if c.fetchone():
                return "user_exist_error"

            # Email Var mı?
            c.execute('SELECT 1 FROM users WHERE email = %s', (email,))
            if c.fetchone():
                return "email_exist_error"

            # Kayıt
            hashed_pw = make_hash(password)
            # İlk kullanıcı 'admin' olsun, diğerleri 'user'
            c.execute('SELECT count(*) FROM users')
            count = c.fetchone()[0]
            role = 'admin' if count == 0 else 'user'

            c.execute('INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)',
                      (username, email, hashed_pw, role))
        return "success"
    except Exception as e:
        return str(e)

def login_user(username, password):
    try:
        with db_cursor() as c:
            if not c:
                return None
            c.execute('SELECT password, role FROM users WHERE username = %s', (username,))
            data = c.fetchone()
    except Exception:
        return None

    if data:
        stored_hash, role = data
        if check_hashes(password, stored_hash):
            return role
    return None

def get_all_users():
    try:
        with db_cursor() as c:
            if not c:
                return []
            c.execute('SELECT username FROM users ORDER BY username')
            data = c.fetchall()
    except Exception:
        return []
    return [user[0] for user in data]

def admin_reset_password(username, new_password):
    new_hash = make_hash(new_password)
    with db_cursor(commit=True) as c:
        if not c:
            return
        c.execute('UPDATE users SET password = %s WHERE username = %s', (new_hash, username))

# --- ŞİFRE SIFIRLAMA ---
def set_reset_code(email):
    """Basitçe 6 haneli kod üretir ve geçici olarak hafızada tutar (Redis yoksa)."""
    # Not: Gerçek prodüksiyonda bu kodları da DB'de tutmak daha iyidir ama şimdilik session state yeterli.
    import random
    code = str(random.randint(100000, 999999))
    
    # Kullanıcı var mı kontrol et
    with db_cursor() as c:
        if not c:
            return None
        c.execute('SELECT username FROM users WHERE email = %s', (email,))
        user = c.fetchone()
    
    if user:
        # Streamlit session state kullanarak geçici tutuyoruz
        if 'reset_codes' not in st.session_state: st.session_state.reset_codes = {}
        st.session_state.reset_codes[email] = code
        return code
    return None

def verify_reset_code(email, code):
    if 'reset_codes' in st.session_state and email in st.session_state.reset_codes:
        if st.session_state.reset_codes[email] == code:
            return True
    return False

def reset_password_with_code(email, new_password):
    new_hash = make_hash(new_password)
    with db_cursor(commit=True) as c:
        if not c:
            return
        c.execute('UPDATE users SET password = %s WHERE email = %s', (new_hash, email))
    
    # Kodu temizle
    if 'reset_codes' in st.session_state:
        del st.session_state.reset_codes[email]

# --- HATA ANALİZİ ---
def log_mistake(username, question_id, chapter):
    with db_cursor(commit=True) as c:
        if not c:
            return

        # Önce UPDATE deneyerek SELECT turunu azaltıyoruz.
        c.execute('''
            UPDATE mistakes
               SET mistake_count = mistake_count + 1,
                   chapter = %s
             WHERE username = %s AND question_id = %s
        ''', (chapter, username, question_id))

        if c.rowcount == 0:
            c.execute('''
                INSERT INTO mistakes (username, question_id, chapter)
                VALUES (%s, %s, %s)
            ''', (username, question_id, chapter))

def get_mistakes(username):
    try:
        with db_cursor() as c:
            if not c:
                return []
            c.execute('''
                SELECT question_id, MAX(chapter) AS chapter, SUM(mistake_count) AS mistake_count
                  FROM mistakes
                 WHERE username = %s
                 GROUP BY question_id
                 ORDER BY MAX(chapter), question_id
            ''', (username,))
            return c.fetchall()
    except Exception:
        return []

def remove_mistake(username, question_id):
    with db_cursor(commit=True) as c:
        if not c:
            return
        c.execute('DELETE FROM mistakes WHERE username = %s AND question_id = %s', (username, question_id))
