import unittest
import os
import sys

# Ana dizini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import utils.db_manager as db

class TestSecurity(unittest.TestCase):

    def setUp(self):
        self.test_db_path = os.path.join("tests", "test_sec_db.db")
        db.DB_PATH = self.test_db_path
        db.init_db()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_sql_injection_login(self):
        """TEST 1: SQL Injection ile giriş yapmayı dene."""
        # Hacker ' OR '1'='1 yazarak şifresiz girmeyi dener
        payload = "' OR '1'='1"
        role = db.login_user("admin", payload)
        
        # Sonuç None olmalı (Girememeli)
        self.assertIsNone(role, "GÜVENLİK AÇIĞI: SQL Injection ile giriş yapıldı!")

    def test_sql_injection_bypass_user(self):
        """TEST 2: Yorum satırı (--) ile şifre kontrolünü atlatmayı dene."""
        # Önce geçerli bir kullanıcı oluşturalım
        db.add_user("kurban", "kurban@mail.com", "gucluSifre123")
        
        # 'kurban' --  diyerek şifreyi bypass etmeye çalışır
        payload_user = "kurban' --"
        role = db.login_user(payload_user, "rastgele")
        
        self.assertIsNone(role, "GÜVENLİK AÇIĞI: '--' operatörü ile şifre atlatıldı!")

    def test_xss_protection_register(self):
        """TEST 3: XSS (Script Gömme) Koruması."""
        # Kullanıcı adına script kodu yazıyoruz
        malicious_user = "<script>alert('HACKED')</script>"
        db.add_user(malicious_user, "xss@mail.com", "password123")
        
        # Veritabanına nasıl kaydolduğunu kontrol edelim
        # Doğrudan DB bağlantısı ile ham veriyi çekiyoruz
        import sqlite3
        conn = sqlite3.connect(self.test_db_path)
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE email='xss@mail.com'")
        stored_name = c.fetchone()[0]
        conn.close()

        # Beklenti: < ve > işaretlerinin &lt; ve &gt; olarak değiştirilmiş olması (Sanitization)
        self.assertNotEqual(stored_name, malicious_user, "GÜVENLİK AÇIĞI: XSS kodu temizlenmeden kaydedildi!")
        self.assertIn("&lt;script&gt;", stored_name, "XSS koruması (html escape) çalışmıyor.")

    def test_weak_password_policy(self):
        """TEST 4: Zayıf şifre politikası."""
        # 3 karakterli şifre ile kayıt olmayı dene
        result = db.add_user("zayifuser", "zayif@mail.com", "123")
        
        self.assertEqual(result, "pass_len_error", "GÜVENLİK ZAFİYETİ: Çok kısa şifre kabul edildi!")

if __name__ == '__main__':
    unittest.main()
