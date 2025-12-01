# 🐳 Docker Kurulum ve Yapılandırma Rehberi

Bu proje, **Docker** ve **Docker Compose** kullanılarak herhangi bir bağımlılık sorunu yaşamadan (Dependency Hell) tek komutla çalıştırılabilir.

Aşağıdaki dosyaları projenizin ana dizininde oluşturun.

---

### 1. Dockerfile
*Bu dosya, uygulamanın çalışacağı sanal bilgisayarın (Image) tarifidir.*

`Dockerfile` adında uzantısız bir dosya oluşturun:

```dockerfile
# 1. Hafif ve güvenli Python 3.9 sürümünü baz al
FROM python:3.9-slim

# 2. Çalışma dizinini ayarla
WORKDIR /app

# 3. Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Kalan tüm proje dosyalarını kopyala
COPY . .

# 5. Streamlit portunu dışarı aç
EXPOSE 8501

# 6. Sağlık kontrolü (Opsiyonel - Uygulama çökerse Docker anlasın)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 7. Uygulamayı başlat
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 2. docker-compose.yml
Bu dosya, konteynerin nasıl çalışacağını, hangi portları kullanacağını ve veritabanını nerede saklayacağını belirler.

`docker-compose.yml` adında bir dosya oluşturun:

```YAML

version: '3.8'

services:
  app:
    container_name: ekotestbank_container
    build: .
    restart: unless-stopped  # Hata olursa veya PC yeniden başlarsa otomatik aç
    ports:
      - "8501:8501"
    env_file:
      - .env  # Şifreleri güvenli bir şekilde içeri aktar
    volumes:
      # Bilgisayardaki 'data' klasörünü konteyner ile eşle.
      # Böylece Docker silinse bile sorular ve kullanıcı verileri kaybolmaz.
      - ./data:/app/data
```

3. .dockerignore
Gereksiz dosyaların Docker imajını şişirmesini engeller.

`.dockerignore` adında bir dosya oluşturun:

```Plaintext

__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.git
.gitignore
.dockerignore
data/user_data.db  # Eski DB yanlışlıkla kopyalanmasın, volume ile yöneteceğiz
.env               # .env dosyasını kopyalama, docker-compose ile güvenli aktar
```

