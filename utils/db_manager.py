import sqlite3
import os

DB_PATH = os.path.join("data", "user_data.db")

def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Hatalar tablosu: soru_id, chapter, hata_sayisi
    c.execute('''CREATE TABLE IF NOT EXISTS mistakes
                 (question_id TEXT PRIMARY KEY, chapter TEXT, error_count INTEGER)''')
    conn.commit()
    conn.close()

def log_mistake(question_id, chapter):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Eğer kayıt varsa hata sayısını artır, yoksa yeni kayıt oluştur
    c.execute('''INSERT INTO mistakes (question_id, chapter, error_count)
                 VALUES (?, ?, 1)
                 ON CONFLICT(question_id) DO UPDATE SET error_count = error_count + 1''', 
                 (question_id, chapter))
    conn.commit()
    conn.close()

def remove_mistake(question_id):
    """Doğru bilinirse hatayı listeden sil (isteğe bağlı)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM mistakes WHERE question_id = ?", (question_id,))
    conn.commit()
    conn.close()

def get_mistakes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT question_id, chapter FROM mistakes")
    data = c.fetchall()
    conn.close()
    return data # [(id, chapter), ...] listesi döner
