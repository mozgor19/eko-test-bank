import streamlit as st
import os
import random
import time
from streamlit_pdf_viewer import pdf_viewer

# Kendi modüllerimiz
from utils.docx_parser import parse_docx
from utils.db_manager import init_db, log_mistake, get_mistakes, remove_mistake

# -----------------------------------------------------------------------------
# AYARLAR VE BAŞLANGIÇ
# -----------------------------------------------------------------------------
st.set_page_config(page_title="ekoTestBank", page_icon="🎓", layout="wide")

# Veritabanını Başlat
init_db()

# Yolları Tanımla
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "questions")
SLIDES_DIR = os.path.join(BASE_DIR, "data", "slides")

# CSS ve Mobil Ayarları Yükle
with open(os.path.join(BASE_DIR, "assets", "style.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Mobil PWA Meta Etiketleri
st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)

# Scroll to Top Butonu (JavaScript)
st.markdown("""
<button onclick="topFunction()" id="myBtn" title="Başa Dön">⬆️</button>
<script>
var mybutton = document.getElementById("myBtn");
window.onscroll = function() {scrollFunction()};
function scrollFunction() {
  if (document.body.scrollTop > 500 || document.documentElement.scrollTop > 500) {
    mybutton.style.display = "block";
  } else {
    mybutton.style.display = "none";
  }
}
function topFunction() {
  document.body.scrollTop = 0;
  document.documentElement.scrollTop = 0;
}
</script>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE YÖNETİMİ
# -----------------------------------------------------------------------------
if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# -----------------------------------------------------------------------------
# FONKSİYONLAR
# -----------------------------------------------------------------------------
def load_data():
    """Tüm chapterları otomatik yükler."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        st.error(f"Lütfen soru dosyalarını '{DATA_DIR}' klasörüne atın.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.docx')]
    if not files:
        st.warning(f"'{DATA_DIR}' klasöründe dosya bulunamadı.")
        return

    all_loaded = []
    bar = st.sidebar.progress(0)
    status = st.sidebar.empty()
    
    for idx, file_name in enumerate(files):
        status.text(f"Yükleniyor: {file_name}...")
        ch_name = file_name.split('.')[0]
        file_path = os.path.join(DATA_DIR, file_name)
        qs = parse_docx(file_path, ch_name)
        all_loaded.extend(qs)
        bar.progress((idx + 1) / len(files))
    
    status.empty()
    bar.empty()
    st.session_state.all_questions = all_loaded
    st.session_state.data_loaded = True
    st.toast(f"✅ Başarıyla {len(all_loaded)} soru yüklendi!", icon="🎉")

# -----------------------------------------------------------------------------
# KENAR ÇUBUĞU & NAVİGASYON
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🎓 ekoTestBank")
    
    # Navigasyon
    menu = st.radio("Menü", ["📝 Quiz Çöz", "❌ Hatalarım", "📊 Ders Slaytları"])
    st.markdown("---")

    # Veri Yükleme (Eğer yüklenmemişse)
    if not st.session_state.data_loaded:
        load_data() # Otomatik yükle
        
    # İstatistik
    if st.session_state.data_loaded:
        st.caption(f"📚 Havuzda {len(st.session_state.all_questions)} soru var.")
        if st.button("🔄 Verileri Yenile"):
            load_data()
            st.rerun()

# -----------------------------------------------------------------------------
# SAYFA: QUIZ ÇÖZ & HATALARIM
# -----------------------------------------------------------------------------
if menu in ["📝 Quiz Çöz", "❌ Hatalarım"]:
    st.header(menu)

    if not st.session_state.data_loaded:
        st.info("Veriler yükleniyor...")
        st.stop()

    quiz_pool = []
    
    # MOD SEÇİMİ
    if menu == "❌ Hatalarım":
        mistake_ids = [m[0] for m in get_mistakes()] # DB'den ID'leri al
        quiz_pool = [q for q in st.session_state.all_questions if q['id'] in mistake_ids]
        if not quiz_pool:
            st.success("🎉 Hiç kayıtlı hatanız yok! Harika gidiyorsunuz.")
            st.stop()
        st.info(f"Geçmişte hata yaptığınız {len(quiz_pool)} soru listeleniyor.")
    
    else: # Quiz Çöz Modu
        # Filtreleme Seçenekleri
        with st.expander("🛠️ Quiz Ayarları", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
                selected_chaps = st.multiselect("Chapter Seçimi:", chapters, default=chapters[0] if chapters else None)
            with col2:
                q_count = st.number_input("Soru Sayısı:", 5, 200, 20)
                is_random = st.checkbox("Rastgele Karıştır", value=True)
            
            if st.button("🚀 Testi Başlat", use_container_width=True):
                filtered = [q for q in st.session_state.all_questions if q['chapter'] in selected_chaps]
                if is_random:
                    quiz_pool = random.sample(filtered, min(q_count, len(filtered)))
                else:
                    quiz_pool = filtered[:q_count]
                
                st.session_state.current_quiz = quiz_pool
                st.rerun()

    # Mevcut Quiz Listesi
    current_qs = quiz_pool if menu == "❌ Hatalarım" else st.session_state.current_quiz
    
    if not current_qs:
        st.info("👈 Başlamak için ayarlardan seçim yapın ve 'Testi Başlat'a basın.")
    else:
        # Soruya Git Özelliği (Jump)
        question_ids = [f"{i+1}. {q['id']}" for i, q in enumerate(current_qs)]
        selected_jump = st.selectbox("🔍 Soruya Git:", question_ids, index=None, placeholder="Soru seçin...")
        
        # Seçim yapıldıysa o soruya scroll yapması için anchor link veriyoruz
        if selected_jump:
            idx = int(selected_jump.split('.')[0]) - 1
            st.markdown(f"<a href='#q-{idx}'>Seçilen soruya gitmek için tıkla</a>", unsafe_allow_html=True)

        st.markdown("---")

        # SORULARI LİSTELE
        for i, q in enumerate(current_qs):
            # Anchor noktası (Soruya gitmek için)
            st.markdown(f"<div id='q-{i}'></div>", unsafe_allow_html=True)
            
            with st.expander(f"Soru {i+1} ({q['id']})", expanded=True):
                # Soru Metni
                st.markdown(q['body_html'], unsafe_allow_html=True)
                
                # Şıklar
                opts = list(q['options'].keys())
                fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
                
                key = f"ans_{menu}_{i}_{q['id']}"
                user_choice = st.radio("Cevabınız:", fmt_opts, key=key, index=None)
                
                # Cevap Kontrolü
                if user_choice:
                    sel = user_choice.split(')')[0]
                    corr = q['answer']
                    
                    if sel == corr:
                        st.success("✅ Doğru! Tebrikler.")
                        if menu == "❌ Hatalarım":
                            remove_mistake(q['id']) # Doğru bilince hatadan sil (opsiyonel)
                    else:
                        st.error(f"❌ Yanlış. Doğru Cevap: **{corr.upper()}**")
                        # Hatayı DB'ye kaydet
                        log_mistake(q['id'], q['chapter'])
                    
                    # Detay Bilgiler (Cevaplandıktan sonra görünür)
                    st.markdown("---")
                    cols = st.columns(3)
                    if q.get('ref'): cols[0].caption(f"**Referans:** {q['ref']}")
                    if q.get('top'): cols[1].caption(f"**Konu:** {q['top']}")
                    if q.get('msc'): cols[2].caption(f"**Tip:** {q['msc']}")

# -----------------------------------------------------------------------------
# SAYFA: SLAYTLAR
# -----------------------------------------------------------------------------
elif menu == "📊 Ders Slaytları":
    st.header("📊 Ders Materyalleri")
    
    if not os.path.exists(SLIDES_DIR):
        os.makedirs(SLIDES_DIR)
        st.warning(f"Lütfen PDF dosyalarını '{SLIDES_DIR}' içine atın.")
        st.stop()
        
    pdf_files = sorted([f for f in os.listdir(SLIDES_DIR) if f.lower().endswith('.pdf')])
    
    if not pdf_files:
        st.info("Henüz slayt yüklenmemiş.")
    else:
        selected_pdf = st.selectbox("Slayt Seç:", pdf_files)
        
        pdf_path = os.path.join(SLIDES_DIR, selected_pdf)
        
        # İndirme Butonu (User Experience +)
        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
            st.download_button(label="📥 Bu Slaytı İndir", 
                               data=pdf_bytes, 
                               file_name=selected_pdf, 
                               mime='application/pdf')
        
        # Görüntüleme
        pdf_viewer(pdf_path, height=800)

# -----------------------------------------------------------------------------
# ALT BİLGİ & BUTON
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown('<button class="thank-btn">✨ Teşekkür etmek tamamen ücretsiz ✨</button>', unsafe_allow_html=True)
