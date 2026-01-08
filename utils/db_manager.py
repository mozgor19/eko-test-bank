import psycopg2
import hashlib
import os
import streamlit as st
import json

# Veritabanı URL'sini al (.env veya Secrets)
DATABASE_URL = os.getenv("DATABASE_URL") or (st.secrets["DATABASE_URL"] if "DATABASE_URL" in st.secrets else None)

def get_connection():
    """PostgreSQL veritabanına güvenli bağlantı açar."""
    if not DATABASE_URL:
        st.error("Veritabanı bağlantı adresi (DATABASE_URL) bulunamadı!")
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        st.error(f"Veritabanı Bağlantı Hatası: {e}")
        return None

def init_db():
    """Tabloları oluşturur (Eğer yoksa)."""
    conn = get_connection()
    if conn:
        c = conn.cursor()
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
        conn.commit()
        conn.close()

# --- GÜVENLİK (HASHING) ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hash(password) == hashed_text:
        return hashed_text
    return False

# --- KULLANICI İŞLEMLERİ ---
def add_user(username, email, password):
    conn = get_connection()
    if not conn: return "db_error"
    c = conn.cursor()
    
    # Şifre Uzunluk Kontrolü
    if len(password) < 6:
        conn.close()
        return "pass_len_error"

    # Kullanıcı Adı Var mı?
    c.execute('SELECT * FROM users WHERE username = %s', (username,))
    if c.fetchone():
        conn.close()
        return "user_exist_error"

    # Email Var mı?
    c.execute('SELECT * FROM users WHERE email = %s', (email,))
    if c.fetchone():
        conn.close()
        return "email_exist_error"

    # Kayıt
    hashed_pw = make_hash(password)
    # İlk kullanıcı 'admin' olsun, diğerleri 'user'
    c.execute('SELECT count(*) FROM users')
    count = c.fetchone()[0]
    role = 'admin' if count == 0 else 'user'

    try:
        c.execute('INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)', 
                  (username, email, hashed_pw, role))
        conn.commit()
        conn.close()
        return "success"
    except Exception as e:
        conn.close()
        return str(e)

def login_user(username, password):
    conn = get_connection()
    if not conn: return None
    c = conn.cursor()
    
    c.execute('SELECT password, role FROM users WHERE username = %s', (username,))
    data = c.fetchone()
    conn.close()

    if data:
        stored_hash, role = data
        if check_hashes(password, stored_hash):
            return role
    return None

def get_all_users():
    conn = get_connection()
    if not conn: return []
    c = conn.cursor()
    c.execute('SELECT username FROM users')
    data = c.fetchall()
    conn.close()
    return [user[0] for user in data]

def admin_reset_password(username, new_password):
    conn = get_connection()
    if not conn: return
    c = conn.cursor()
    new_hash = make_hash(new_password)
    c.execute('UPDATE users SET password = %s WHERE username = %s', (new_hash, username))
    conn.commit()
    conn.close()

# --- ŞİFRE SIFIRLAMA ---
def set_reset_code(email):
    """Basitçe 6 haneli kod üretir ve geçici olarak hafızada tutar (Redis yoksa)."""
    # Not: Gerçek prodüksiyonda bu kodları da DB'de tutmak daha iyidir ama şimdilik session state yeterli.
    import random
    code = str(random.randint(100000, 999999))
    
    # Kullanıcı var mı kontrol et
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE email = %s', (email,))
    user = c.fetchone()
    conn.close()
    
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
    conn = get_connection()
    c = conn.cursor()
    
    new_hash = make_hash(new_password)
    c.execute('UPDATE users SET password = %s WHERE email = %s', (new_hash, email))
    conn.commit()
    conn.close()
    
    # Kodu temizle
    if 'reset_codes' in st.session_state:
        del st.session_state.reset_codes[email]

# --- HATA ANALİZİ ---
def log_mistake(username, question_id, chapter):
    conn = get_connection()
    if not conn: return
    c = conn.cursor()
    
    # Hata daha önce yapılmış mı?
    c.execute('SELECT * FROM mistakes WHERE username = %s AND question_id = %s', (username, question_id))
    data = c.fetchone()
    
    if data:
        c.execute('UPDATE mistakes SET mistake_count = mistake_count + 1 WHERE username = %s AND question_id = %s', 
                  (username, question_id))
    else:
        c.execute('INSERT INTO mistakes (username, question_id, chapter) VALUES (%s, %s, %s)', 
                  (username, question_id, chapter))
    
    conn.commit()
    conn.close()

def get_mistakes(username):
    conn = get_connection()
    if not conn: return []
    c = conn.cursor()
    c.execute('SELECT question_id, chapter, mistake_count FROM mistakes WHERE username = %s', (username,))
    data = c.fetchall()
    conn.close()
    return data

def remove_mistake(username, question_id):
    conn = get_connection()
    if not conn: return
    c = conn.cursor()
    c.execute('DELETE FROM mistakes WHERE username = %s AND question_id = %s', (username, question_id))
    conn.commit()
    conn.close()
