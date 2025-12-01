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

# CSS Dosyasını Yükleme Fonksiyonu
def load_css(is_dark_mode=True):
    css_path = os.path.join(BASE_DIR, "assets", "style.css")
    with open(css_path) as f:
        base_css = f.read()
    
    # Gece/Gündüz Modu İçin Dinamik CSS
    if is_dark_mode:
        theme_css = """
        <style>
            .stApp { background-color: #0E1117; color: #FAFAFA; }
            .stSidebar { background-color: #262730; }
            div[data-testid="stExpander"] { background-color: #262730; border: 1px solid #444; }
            p, h1, h2, h3 { color: #FAFAFA !important; }
        </style>
        """
    else:
        theme_css = """
        <style>
            .stApp { background-color: #FFFFFF; color: #31333F; }
            .stSidebar { background-color: #F0F2F6; }
            div[data-testid="stExpander"] { background-color: #FFFFFF; border: 1px solid #ddd; }
            p, h1, h2, h3 { color: #31333F !important; }
        </style>
        """
    
    st.markdown(theme_css, unsafe_allow_html=True)
    st.markdown(f"<style>{base_css}</style>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE YÖNETİMİ
# -----------------------------------------------------------------------------
if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True  # Varsayılan Gece Modu

# -----------------------------------------------------------------------------
# FONKSİYONLAR
# -----------------------------------------------------------------------------
def load_data():
    """Tüm chapterları yükler."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        st.error(f"Lütfen soru dosyalarını '{DATA_DIR}' klasörüne atın.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.docx')]
    if not files:
        st.warning(f"'{DATA_DIR}' klasöründe dosya bulunamadı.")
        return

    all_loaded = []
    # İlerleme çubuğu (Main alanda görünür)
    progress_text = "Sorular analiz ediliyor. Lütfen bekleyin..."
    my_bar = st.progress(0, text=progress_text)

    for idx, file_name in enumerate(files):
        ch_name = file_name.split('.')[0]
        file_path = os.path.join(DATA_DIR, file_name)
        qs = parse_docx(file_path, ch_name)
        all_loaded.extend(qs)
        my_bar.progress((idx + 1) / len(files), text=f"İşleniyor: {file_name}")
    
    my_bar.empty()
    st.session_state.all_questions = all_loaded
    st.session_state.data_loaded = True
    st.toast(f"✅ Başarıyla {len(all_loaded)} soru yüklendi!", icon="🎉")
    st.rerun()

# -----------------------------------------------------------------------------
# KENAR ÇUBUĞU & AYARLAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2232/2232688.png", width=50)
    st.title("ekoTestBank")
    
    # 1. Gece/Gündüz Modu Butonu
    st.write("---")
    st.write("🎨 **Görünüm**")
    mode_toggle = st.toggle("🌙 Gece Modu", value=st.session_state.dark_mode)
    if mode_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = mode_toggle
        st.rerun()
    
    # CSS'i uygula (Toggle durumuna göre)
    load_css(st.session_state.dark_mode)

    st.write("---")
    
    # 2. Navigasyon
    menu = st.radio("Menü", ["📝 Quiz Çöz", "❌ Hatalarım", "📊 Ders Slaytları"])
    st.markdown("---")

    # 3. İstatistik ve Durum
    if st.session_state.data_loaded:
        st.success(f"📚 {len(st.session_state.all_questions)} soru yüklü.")
        if st.button("🔄 Verileri Sıfırla/Yenile"):
            st.session_state.data_loaded = False
            st.session_state.all_questions = []
            st.session_state.current_quiz = []
            st.rerun()

# -----------------------------------------------------------------------------
# SAYFA: QUIZ ÇÖZ & HATALARIM
# -----------------------------------------------------------------------------
if menu in ["📝 Quiz Çöz", "❌ Hatalarım"]:
    
    # Header
    col1, col2 = st.columns([8, 1])
    with col1:
        st.header(menu)
    
    # --- VERİ YÜKLEME EKRANI (LAZY LOADING) ---
    if not st.session_state.data_loaded:
        st.info("👋 Hoşgeldiniz! Başlamak için soru havuzunu yüklemeniz gerekiyor.")
        
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("🚀 Soruları Yükle", type="primary", use_container_width=True):
                load_data()
        st.stop() # Veri yüklenene kadar aşağıyı çalıştırma

    # --- QUIZ MANTIĞI ---
    quiz_pool = []
    
    # A) HATALARIM MODU
    if menu == "❌ Hatalarım":
        mistake_ids = [m[0] for m in get_mistakes()] 
        quiz_pool = [q for q in st.session_state.all_questions if q['id'] in mistake_ids]
        if not quiz_pool:
            st.success("🎉 Hiç kayıtlı hatanız yok! Harika gidiyorsunuz.")
            st.stop()
        st.info(f"Geçmişte hata yaptığınız {len(quiz_pool)} soru listeleniyor.")
    
    # B) QUIZ ÇÖZ MODU (Chapter & Karma)
    else: 
        # Mod Seçimi (Eskisi gibi)
        quiz_mode = st.radio("Çalışma Modu Seçin:", ["📚 Chapter Bazlı", "🔀 Karma Test"], horizontal=True)
        st.markdown("---")

        with st.expander("🛠️ Test Ayarları", expanded=True):
            
            # 1. CHAPTER BAZLI
            if quiz_mode == "📚 Chapter Bazlı":
                chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
                selected_chap = st.selectbox("Hangi Chapter çalışılacak?", chapters)
                
                # Seçim değiştiğinde veya butonla başlatıldığında
                if st.button("Chapter Testini Başlat", type="primary"):
                    quiz_pool = [q for q in st.session_state.all_questions if q['chapter'] == selected_chap]
                    st.session_state.current_quiz = quiz_pool
                    st.rerun()

            # 2. KARMA TEST
            else:
                chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
                selected_chaps = st.multiselect("Hangi Chapter'lar dahil olsun?", chapters, default=chapters)
                
                col_x, col_y = st.columns(2)
                with col_x:
                    q_count = st.number_input("Soru Sayısı:", 5, 200, 20)
                with col_y:
                    is_random = st.checkbox("Soruları Karıştır", value=True)
                
                if st.button("Karma Test Oluştur", type="primary"):
                    filtered = [q for q in st.session_state.all_questions if q['chapter'] in selected_chaps]
                    if not filtered:
                        st.error("Lütfen en az bir chapter seçin.")
                    else:
                        if is_random:
                            quiz_pool = random.sample(filtered, min(q_count, len(filtered)))
                        else:
                            quiz_pool = filtered[:q_count]
                        st.session_state.current_quiz = quiz_pool
                        st.rerun()

    # --- SORULARI GÖSTERME ALANI ---
    # Eğer Hatalarım modundaysak havuz direkt gelir, Quiz modundaysak session'dan gelir
    current_qs = quiz_pool if menu == "❌ Hatalarım" else st.session_state.current_quiz
    
    if not current_qs and menu == "📝 Quiz Çöz":
        st.info("👈 Yukarıdaki ayarlardan bir test oluşturun.")
    elif current_qs:
        # Soruya Git (Jump) Özelliği
        with st.sidebar:
            st.write("---")
            st.write("🔎 **Hızlı Git**")
            question_map = {f"{i+1}. {q['id']}": i for i, q in enumerate(current_qs)}
            selected_jump = st.selectbox("Soru Seç:", list(question_map.keys()), index=None, placeholder="Soru no seç...")
            if selected_jump:
                idx = question_map[selected_jump]
                st.markdown(f"<script>location.href = '#q-{idx}';</script>", unsafe_allow_html=True)
                st.markdown(f"[Soruya Git](#q-{idx})")

        # Liste
        for i, q in enumerate(current_qs):
            # Anchor (Çapa) noktası
            st.markdown(f"<div id='q-{i}'></div>", unsafe_allow_html=True)
            
            # Soru Kartı
            with st.expander(f"Soru {i+1} 🔹 {q['id']}", expanded=True):
                # Soru Metni
                st.markdown(q['body_html'], unsafe_allow_html=True)
                
                # Şıklar
                opts = list(q['options'].keys())
                fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
                
                key = f"ans_{menu}_{i}_{q['id']}" # Unique key
                user_choice = st.radio("Cevabınız:", fmt_opts, key=key, index=None)
                
                # Cevap Kontrolü
                if user_choice:
                    sel = user_choice.split(')')[0]
                    corr = q['answer']
                    
                    if sel == corr:
                        st.success("✅ Doğru! Tebrikler.")
                        if menu == "❌ Hatalarım":
                            remove_mistake(q['id']) 
                    else:
                        st.error(f"❌ Yanlış. Doğru Cevap: **{corr.upper()}**")
                        log_mistake(q['id'], q['chapter'])
                    
                    # Detay Bilgiler (Cevaplandıktan sonra)
                    st.divider()
                    c1, c2, c3 = st.columns(3)
                    if q.get('ref'): c1.caption(f"📌 **Ref:** {q['ref']}")
                    if q.get('top'): c2.caption(f"📚 **Konu:** {q['top']}")
                    if q.get('msc'): c3.caption(f"🧠 **Tip:** {q['msc']}")

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
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            selected_pdf = st.selectbox("Slayt Seç:", pdf_files)
        
        pdf_path = os.path.join(SLIDES_DIR, selected_pdf)
        
        with col_s2:
            st.write("") # Boşluk
            st.write("") 
            # İndirme Butonu
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(label="📥 İndir", 
                                   data=pdf_file, 
                                   file_name=selected_pdf, 
                                   mime='application/pdf',
                                   use_container_width=True)
        
        # Görüntüleme
        pdf_viewer(pdf_path, height=850)

# -----------------------------------------------------------------------------
# ALT BİLGİ & SCROLL TO TOP
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown('<button class="thank-btn">✨ Teşekkür etmek tamamen ücretsiz ✨</button>', unsafe_allow_html=True)

# Scroll to Top Butonu (HTML/JS)
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
