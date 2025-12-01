import sqlite3
import os
import hashlib
import streamlit as st

DB_PATH = os.path.join("data", "user_data.db")

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hash(password) == hashed_text:
        return True
    return False

def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Hatalar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS mistakes
                 (username TEXT, question_id TEXT, chapter TEXT, error_count INTEGER, 
                 PRIMARY KEY (username, question_id))''')
    
    # Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    conn.commit()
    conn.close()

# --- KULLANICI İŞLEMLERİ ---
def add_user(username, password):
    # Admin ismini kimse alamasın
    if username.lower() == "admin":
        return False
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                  (username, make_hash(password), 'user'))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    # 1. Önce Admin kontrolü (Secrets üzerinden)
    if username.lower() == "admin":
        try:
            # Secrets'tan şifreyi çek
            admin_secret = st.secrets["ADMIN_PASSWORD"]
            if password == admin_secret:
                return "admin"
        except FileNotFoundError:
            # Lokal'de secrets.toml yoksa
            pass
        except KeyError:
            # Secrets tanımlı değilse
            pass

    # 2. Normal Kullanıcı Kontrolü (DB üzerinden)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password, role FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    
    if data:
        stored_password, role = data
        if check_hashes(password, stored_password):
            return role
    return None

# --- ADMIN ÖZEL FONKSİYONLARI ---
def get_all_users():
    """Tüm kullanıcıları listeler (Admin için)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    data = c.fetchall()
    conn.close()
    return [user[0] for user in data]

def admin_reset_password(username, new_password):
    """Adminin bir kullanıcının şifresini sıfırlaması için"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE username = ?", 
              (make_hash(new_password), username))
    conn.commit()
    conn.close()

# --- HATA KAYIT İŞLEMLERİ ---
def log_mistake(username, question_id, chapter):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO mistakes (username, question_id, chapter, error_count)
                 VALUES (?, ?, ?, 1)
                 ON CONFLICT(username, question_id) 
                 DO UPDATE SET error_count = error_count + 1''', 
                 (username, question_id, chapter))
    conn.commit()
    conn.close()

def remove_mistake(username, question_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM mistakes WHERE username = ? AND question_id = ?", (username, question_id))
    conn.commit()
    conn.close()

def get_mistakes(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT question_id, chapter, error_count FROM mistakes WHERE username = ?", (username,))
    data = c.fetchall()
    conn.close()
    return data
