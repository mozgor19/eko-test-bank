# 🎓 ekoTestBank

[![Güvenlik ve Fonksiyon Testleri](https://github.com/mozgor19/eko-test-bank/actions/workflows/test_suite.yml/badge.svg)](https://github.com/mozgor19/eko-test-bank/actions/workflows/test_suite.yml)

**ekoTestBank**, İTÜ EKO 201E dersi için geliştirilmiş yeni nesil bir **Soru Yönetim Sistemi**dir. 

Word (.docx) tabanlı soru bankalarını saniyeler içinde analiz eder, görselleri akıllıca eşleştirir ve modern bir arayüzde interaktif testlere dönüştürür. Bu proje, **modern yazılım geliştirme pratikleri** ve **Vibe Coding** yaklaşımıyla, kullanıcı deneyimi odaklı olarak tasarlanmıştır.

## ⚠️ Yasal Uyarı ve Amaç

> **Bu proje tamamen EĞİTİM AMAÇLIDIR.**

* Bu uygulama üzerinden herhangi bir **ticari gelir elde edilmemektedir.**
* Proje, açık kaynak kodlu olup öğrencilerin ders çalışma süreçlerini kolaylaştırmak ve yazılım geliştirme pratiklerini öğrenmek amacıyla geliştirilmiştir.
* İçerikte kullanılan sorular ve materyaller, kullanıcıların kendi yüklediği dosyalardan oluşur; uygulamanın kendisi telifli içerik barındırmaz.
---

## 🌟 Öne Çıkan Özellikler

### 🧠 **Akıllı Soru Ayrıştırma**
* **Format Bağımsız:** `.docx` formatındaki karmaşık dosyaları okur.
* **Otomatik Algılama:** Soruları, şıkları, doğru cevapları ve referansları otomatik ayrıştırır.
* **Akıllı Görsel Eşleştirme:** Soruda *"Refer to Figure 2.1"* gibi bir ifade geçtiğinde, ilgili grafiği bulur ve sorunun hemen üzerine yapıştırır.

### 🔐 **Gelişmiş Güvenlik & Çoklu Kullanıcı**
* **Rol Bazlı Erişim:** Yönetici (Admin) ve Standart Kullanıcı ayrımı.
* **Güçlü Şifreleme:** Şifreler veritabanında `SHA-256` ile kriptolanarak saklanır.
* **Siber Güvenlik:** SQL Injection ve XSS koruması için *Defensive Coding* prensipleri uygulanmıştır.
* **Brute Force Koruması:** Üst üste hatalı girişlerde sistem kendini geçici olarak kilitler.

### 📊 **Kişiselleştirilmiş Deneyim**
* **Hata Takibi:** Her kullanıcının yanlış yaptığı sorular "Hatalarım" havuzuna kaydedilir.
* **İlerleme Yönetimi:** Kullanıcı öğrendiği soruları hata listesinden tek tuşla silebilir.
* **Ders Materyalleri:** PDF formatındaki ders slaytları sistem üzerinden görüntülenebilir ve indirilebilir.

### 🎨 **Modern & Responsive Arayüz**
* **Mobil Uyumlu (PWA):** Telefonunuzun ana ekranına eklendiğinde native bir uygulama gibi çalışır.
* **Karanlık Mod (Dark Mode):** Göz yormayan, modern ve şık tasarım.
* **Etkileşim:** Soruya gitme (Jump), Hızlı geri bildirim ve Teşekkür butonları.

---

## 🚀 Kurulum ve Çalıştırma

Projeyi yerel ortamınızda çalıştırmak için aşağıdaki adımları izleyin.

### 1. Ön Hazırlık
Projeyi bilgisayarınıza indirin:

```bash
git clone [https://github.com/mozgor19/ekoTestBank.git](https://github.com/KULLANICI_ADI/ekoTestBank.git)
cd ekoTestBank
```

### 2. Çevre Değişkenleri (.env)
Proje ana dizininde `.env` adında bir dosya oluşturun ve aşağıdaki ayarları yapıştırın:

```ini
# .env dosyası

# Yönetici Paneli için belirleyeceğiniz şifre
ADMIN_PASSWORD=GucluBirSifreBelirle123!

# (Opsiyonel) Şifre sıfırlama mailleri için Gmail Uygulama Şifresi
EMAIL_SENDER=proje.mailiniz@gmail.com
EMAIL_PASSWORD=abcd1234efgh5678
```

### 3. Çalıştırma Yöntemleri

#### Yöntem A: Docker ile Çalıştırma (Önerilen 🐳)
Docker dosyaları ve detaylı yapılandırma için lütfen DockerSettings.md [https://github.com/mozgor19/eko-test-bank/blob/main/DockerSettings.md] dosyasını inceleyin
Bilgisayarınızda Docker yüklüyse tek komutla sistemi ayağa kaldırabilirsiniz:

```bash
docker-compose up --build
```
Kurulum bittiğinde tarayıcınızdan http://localhost:8501 adresine gidin.

#### Yöntem B: Manuel Kurulum (Python 🐍)
Docker kullanmıyorsanız Python ile çalıştırabilirsiniz:

```bash
# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# Uygulamayı başlatın
streamlit run app.py
```

### 4. Proje Dosyası

```bash
ekoTestBank/
├── .github/workflows/   # Otomatik test senaryoları (CI/CD)
├── .streamlit/          # Streamlit tema ve secrets ayarları
├── assets/              # CSS dosyaları, logolar ve ikonlar
├── data/                # Veri Klasörü
│   ├── questions/       # .docx soru dosyaları buraya yüklenir
│   └── slides/          # .pdf ders slaytları buraya yüklenir
├── utils/               # Yardımcı Modüller
│   ├── db_manager.py    # Veritabanı ve güvenlik işlemleri
│   ├── docx_parser.py   # Word dosyası işleme motoru
│   └── email_helper.py  # Mail gönderme servisleri
├── tests/               # Güvenlik ve fonksiyon test dosyaları
├── app.py               # Ana uygulama dosyası
└── requirements.txt     # Gerekli kütüphaneler
```

## 5. Yönetici (Admin) Paneli Kullanımı

Sistemi yönetmek ve veritabanı işlemleri için:

1. Uygulamaya **Giriş Yap** sekmesinden ulaşın.
2. **Kullanıcı Adı:** `admin` (Sabittir)
3. **Şifre:** `.env` dosyasında belirlediğiniz `ADMIN_PASSWORD`.

**Admin Yetkileri:**
* Kullanıcıların şifrelerini sıfırlama.
* Veritabanını tamamen silip "Fabrika Ayarlarına" döndürme.

---

## 6. Katkıda Bulunma

Bu proje açık kaynaklıdır. Katkıda bulunmak isterseniz:

1. Fork'layın.
2. Branch oluşturun (`git checkout -b ozellik/YeniOzellik`).
3. Commit'leyin (`git commit -m 'Yeni özellik eklendi'`).
4. Push'layın (`git push origin ozellik/YeniOzellik`).
5. Pull Request açın.

---

<div align="center">

**✨ Vibe Coding ile Geliştirilmiştir ✨**

</div>
