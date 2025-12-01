import unittest
import os
import sys
import shutil

# Ana dizini python yoluna ekle ki utils klasörünü görebilelim
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import utils.db_manager as db

class TestFunctional(unittest.TestCase):

    def setUp(self):
        """Her testten önce çalışır: Geçici bir veritabanı oluştur."""
        self.test_db_path = os.path.join("tests", "test_db.db")
        # db_manager içindeki veritabanı yolunu değiştiriyoruz (Mocking)
        db.DB_PATH = self.test_db_path
        db.init_db()

    def tearDown(self):
        """Her testten sonra çalışır: Veritabanını temizle."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_add_user_success(self):
        """Kullanıcı başarıyla oluşturulabiliyor mu?"""
        result = db.add_user("testuser", "testmail@mail.com", "password123")
        self.assertEqual(result, "success")

    def test_add_user_duplicate(self):
        """Aynı isimle iki kullanıcı oluşturulamamalı."""
        db.add_user("testuser", "mail1@mail.com", "password123")
        result = db.add_user("testuser", "mail2@mail.com", "password123")
        self.assertEqual(result, "user_exist_error")

    def test_login_success(self):
        """Doğru şifre ile giriş yapılabiliyor mu?"""
        db.add_user("loginuser", "login@mail.com", "password123")
        role = db.login_user("loginuser", "password123")
        self.assertEqual(role, "user")

    def test_login_failure(self):
        """Yanlış şifre ile giriş engelleniyor mu?"""
        db.add_user("failuser", "fail@mail.com", "password123")
        role = db.login_user("failuser", "wrongpassword")
        self.assertIsNone(role)

    def test_log_mistake(self):
        """Hata kaydı düzgün çalışıyor mu?"""
        username = "ogrenci1"
        db.log_mistake(username, "Q101", "Chapter 1")
        mistakes = db.get_mistakes(username)
        # [(question_id, chapter, error_count)] döner
        self.assertEqual(len(mistakes), 1)
        self.assertEqual(mistakes[0][0], "Q101")

if __name__ == '__main__':
    unittest.main()
