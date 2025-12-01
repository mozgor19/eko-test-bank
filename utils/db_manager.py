import sqlite3
import os

DB_PATH = os.path.join("data", "user_data.db")

def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Tabloyu güncelle: artık 'username' alanı da var
    # PRIMARY KEY artık (username, question_id) ikilisi.
    # Yani aynı soruyu farklı kullanıcılar hata listesine ekleyebilir.
    c.execute('''CREATE TABLE IF NOT EXISTS mistakes
                 (username TEXT, question_id TEXT, chapter TEXT, error_count INTEGER, 
                 PRIMARY KEY (username, question_id))''')
    conn.commit()
    conn.close()

def log_mistake(username, question_id, chapter):
    """Bir kullanıcının hatasını kaydeder."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Hata varsa sayısını artır, yoksa yeni ekle (Upsert mantığı)
    c.execute('''INSERT INTO mistakes (username, question_id, chapter, error_count)
                 VALUES (?, ?, ?, 1)
                 ON CONFLICT(username, question_id) 
                 DO UPDATE SET error_count = error_count + 1''', 
                 (username, question_id, chapter))
    conn.commit()
    conn.close()

def remove_mistake(username, question_id):
    """Belirli bir kullanıcının belirli bir hatasını siler."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM mistakes WHERE username = ? AND question_id = ?", (username, question_id))
    conn.commit()
    conn.close()

def get_mistakes(username):
    """Sadece o kullanıcıya ait hataları getirir."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT question_id, chapter, error_count FROM mistakes WHERE username = ?", (username,))
    data = c.fetchall()
    conn.close()
    return data # [(id, chapter, count), ...]
