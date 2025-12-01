import unittest
import test_functional
import test_security

# Testleri yükle
loader = unittest.TestLoader()
suite = unittest.TestSuite()

suite.addTests(loader.loadTestsFromModule(test_functional))
suite.addTests(loader.loadTestsFromModule(test_security))

# Çalıştır
runner = unittest.TextTestRunner(verbosity=2)
print("🔍 OTOMATİK TESTLER BAŞLATILIYOR...\n" + "="*40)
result = runner.run(suite)

print("="*40)
if result.wasSuccessful():
    print("✅ TÜM TESTLER BAŞARILI! Sistem Güvenli ve Çalışıyor.")
else:
    print(f"❌ BAZI TESTLER BAŞARISIZ OLDU! ({len(result.failures)} Hata, {len(result.errors)} Sorun)")
