import sqlite3
import os
import hashlib
import streamlit as st
import html
import random
import string

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
    
    c.execute('''CREATE TABLE IF NOT EXISTS mistakes
                 (username TEXT, question_id TEXT, chapter TEXT, error_count INTEGER, 
                 PRIMARY KEY (username, question_id))''')
    
    # ARTIK EMAIL DE VAR
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, email TEXT, password TEXT, role TEXT, reset_code TEXT)''')
    conn.commit()
    conn.close()

# --- KULLANICI İŞLEMLERİ ---
def add_user(username, email, password):
    clean_user = html.escape(username)
    clean_email = html.escape(email)
    
    if clean_user.lower() == "admin": return "admin_error"
    if len(password) < 6: return "pass_len_error"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Email kontrolü (Aynı maille iki kayıt olmasın)
        c.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
        if c.fetchone():
            return "email_exist_error"

        c.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", 
                  (clean_user, clean_email, make_hash(password), 'user'))
        conn.commit()
        return "success"
    except sqlite3.IntegrityError:
        return "user_exist_error"
    finally:
        conn.close()

def login_user(username, password):
    clean_user = html.escape(username)
    
    # Admin Kontrolü
    if clean_user.lower() == "admin":
        try:
            # Hem os.getenv hem st.secrets kontrolü
            secret = os.getenv("ADMIN_PASSWORD") or st.secrets["ADMIN_PASSWORD"]
            if password == secret:
                return "admin"
        except:
            pass

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password, role FROM users WHERE username = ?", (clean_user,))
    data = c.fetchone()
    conn.close()
    
    if data and check_hashes(password, data[0]):
        return data[1] # role
    return None

# --- ŞİFRE SIFIRLAMA İŞLEMLERİ ---
def set_reset_code(email):
    """Kullanıcıya rastgele kod atar ve kodu döndürür"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Önce mail var mı kontrol et
    c.execute("SELECT username FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return None # Mail bulunamadı
    
    # 6 haneli kod üret
    code = ''.join(random.choices(string.digits, k=6))
    
    c.execute("UPDATE users SET reset_code = ? WHERE email = ?", (code, email))
    conn.commit()
    conn.close()
    return code

def verify_reset_code(email, input_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT reset_code FROM users WHERE email = ?", (email,))
    data = c.fetchone()
    conn.close()
    
    if data and data[0] == input_code:
        return True
    return False

def reset_password_with_code(email, new_password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Şifreyi güncelle ve kodu sil (tek kullanımlık olsun)
    c.execute("UPDATE users SET password = ?, reset_code = NULL WHERE email = ?", 
              (make_hash(new_password), email))
    conn.commit()
    conn.close()

# --- ADMIN FONKSİYONLARI ---
def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, email FROM users")
    data = c.fetchall()
    conn.close()
    return [f"{u[0]} ({u[1]})" for u in data]

def admin_reset_password(username_with_email, new_password):
    # Gelen format: "Ahmet (ahmet@mail.com)" -> Sadece username'i alalım
    username = username_with_email.split(" (")[0]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE username = ?", 
              (make_hash(new_password), username))
    conn.commit()
    conn.close()

# --- HATA KAYIT FONKSİYONLARI (AYNI) ---
def log_mistake(username, question_id, chapter):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO mistakes (username, question_id, chapter, error_count)
                 VALUES (?, ?, ?, 1)
                 ON CONFLICT(username, question_id) 
                 DO UPDATE SET error_count = error_count + 1''', (username, question_id, chapter))
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
