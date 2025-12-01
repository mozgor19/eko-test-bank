import sqlite3
import os
import hashlib
import streamlit as st
import html  # XSS koruması için

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
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    conn.commit()
    conn.close()

# --- KULLANICI İŞLEMLERİ (GÜVENLİK GÜNCELLEMESİ) ---
def add_user(username, password):
    # 1. XSS Temizliği (Sanitization)
    # <script>alert('hack')</script> -> &lt;script&gt;alert(&#x27;hack&#x27;)&lt;/script&gt;
    clean_username = html.escape(username)
    
    # 2. Admin Kontrolü
    if clean_username.lower() == "admin":
        return "admin_name_error" # Admin ismini alamaz

    # 3. Şifre Politikası (Password Policy)
    if len(password) < 8:
        return "password_length_error"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                  (clean_username, make_hash(password), 'user'))
        conn.commit()
        return "success"
    except sqlite3.IntegrityError:
        return "exists_error" # Kullanıcı adı zaten var
    finally:
        conn.close()

def login_user(username, password):
    # Giriş yaparken de inputu temizleyelim ki eşleşme doğru olsun
    clean_username = html.escape(username)

    # 1. Admin Kontrolü (Secrets)
    if clean_username.lower() == "admin":
        try:
            if password == st.secrets["ADMIN_PASSWORD"]:
                return "admin"
        except:
            pass

    # 2. Normal Kullanıcı
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password, role FROM users WHERE username = ?", (clean_username,))
    data = c.fetchone()
    conn.close()
    
    if data:
        stored_password, role = data
        if check_hashes(password, stored_password):
            return role
    return None

# --- ADMIN FONKSİYONLARI ---
def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    data = c.fetchall()
    conn.close()
    return [user[0] for user in data]

def admin_reset_password(username, new_password):
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
