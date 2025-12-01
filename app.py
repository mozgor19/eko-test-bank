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

# CSS Yükle (Sadece düzen için, renk ayarı yok)
css_path = os.path.join(BASE_DIR, "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Mobil PWA Meta Etiketleri
st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE
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
    # İlerleme çubuğu
    progress_text = "Sorular analiz ediliyor..."
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
    st.toast(f"✅ {len(all_loaded)} soru hazır!", icon="🎉")
    time.sleep(1) # Kullanıcı görsün diye azıcık bekle
    st.rerun()

# -----------------------------------------------------------------------------
# KENAR ÇUBUĞU
# -----------------------------------------------------------------------------
with st.sidebar:
    # Logo varsa göster (yoksa hata vermez)
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=100)
    else:
        st.title("🎓 ekoTestBank")
    
    # Navigasyon
    menu = st.radio("Menü", ["📝 Quiz Çöz", "❌ Hatalarım", "📊 Ders Slaytları"])
    st.markdown("---")

    # İstatistik
    if st.session_state.data_loaded:
        st.caption(f"📚 Havuz: {len(st.session_state.all_questions)} Soru")
        if st.button("🔄 Verileri Yenile", use_container_width=True):
            st.session_state.data_loaded = False
            st.session_state.all_questions = []
            st.rerun()

# -----------------------------------------------------------------------------
# SAYFA: QUIZ ÇÖZ & HATALARIM
# -----------------------------------------------------------------------------
if menu in ["📝 Quiz Çöz", "❌ Hatalarım"]:
    
    st.header(menu)
    
    # --- VERİ YÜKLEME EKRANI ---
    if not st.session_state.data_loaded:
        st.info("Soru havuzunu yükleyerek başlayın.")
        if st.button("🚀 Soruları Yükle", type="primary"):
            load_data()
        st.stop()

    quiz_pool = []
    
    # A) HATALARIM MODU
    if menu == "❌ Hatalarım":
        mistake_ids = [m[0] for m in get_mistakes()] 
        quiz_pool = [q for q in st.session_state.all_questions if q['id'] in mistake_ids]
        if not quiz_pool:
            st.success("🎉 Hiç kayıtlı hatanız yok!")
            st.stop()
        st.info(f"Hata yapılan {len(quiz_pool)} soru var.")
    
    # B) QUIZ ÇÖZ MODU
    else: 
        quiz_mode = st.radio("Mod Seçimi:", ["📚 Chapter Bazlı", "🔀 Karma Test"], horizontal=True)
        st.divider()

        with st.expander("🛠️ Test Ayarları", expanded=True):
            # 1. CHAPTER BAZLI
            if quiz_mode == "📚 Chapter Bazlı":
                chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
                selected_chap = st.selectbox("Chapter Seç:", chapters)
                
                if st.button("Başlat ▶", type="primary", use_container_width=True):
                    quiz_pool = [q for q in st.session_state.all_questions if q['chapter'] == selected_chap]
                    st.session_state.current_quiz = quiz_pool
                    st.rerun()

            # 2. KARMA TEST
            else:
                chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
                selected_chaps = st.multiselect("Dahil Et:", chapters, default=chapters)
                
                c1, c2 = st.columns(2)
                with c1: q_count = st.number_input("Soru Sayısı:", 5, 200, 20)
                with c2: is_random = st.checkbox("Karıştır", value=True)
                
                if st.button("Test Oluştur ✨", type="primary", use_container_width=True):
                    filtered = [q for q in st.session_state.all_questions if q['chapter'] in selected_chaps]
                    if filtered:
                        if is_random:
                            quiz_pool = random.sample(filtered, min(q_count, len(filtered)))
                        else:
                            quiz_pool = filtered[:q_count]
                        st.session_state.current_quiz = quiz_pool
                        st.rerun()
                    else:
                        st.error("Chapter seçmelisiniz.")

    # --- SORU LİSTESİ ---
    current_qs = quiz_pool if menu == "❌ Hatalarım" else st.session_state.current_quiz
    
    if not current_qs and menu == "📝 Quiz Çöz":
        st.info("👈 Yukarıdan test oluşturun.")
    elif current_qs:
        # Soruya Git
        with st.sidebar:
            st.markdown("---")
            q_map = {f"{i+1}. {q['id']}": i for i, q in enumerate(current_qs)}
            jump = st.selectbox("🔎 Soruya Git:", list(q_map.keys()), index=None)
            if jump:
                idx = q_map[jump]
                st.markdown(f"<script>location.href = '#q-{idx}';</script>", unsafe_allow_html=True)

        for i, q in enumerate(current_qs):
            st.markdown(f"<div id='q-{i}'></div>", unsafe_allow_html=True)
            
            with st.expander(f"Soru {i+1} ({q['id']})", expanded=True):
                st.markdown(q['body_html'], unsafe_allow_html=True)
                
                opts = list(q['options'].keys())
                fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
                
                key = f"ans_{menu}_{i}_{q['id']}"
                user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
                
                if user_choice:
                    sel = user_choice.split(')')[0]
                    corr = q['answer']
                    
                    if sel == corr:
                        st.success("✅ Doğru")
                        if menu == "❌ Hatalarım": remove_mistake(q['id'])
                    else:
                        st.error(f"❌ Yanlış. Cevap: **{corr.upper()}**")
                        log_mistake(q['id'], q['chapter'])
                    
                    st.divider()
                    c1, c2, c3 = st.columns(3)
                    if q.get('ref'): c1.caption(f"Ref: {q['ref']}")
                    if q.get('top'): c2.caption(f"Konu: {q['top']}")
                    if q.get('msc'): c3.caption(f"Tip: {q['msc']}")

# -----------------------------------------------------------------------------
# SAYFA: SLAYTLAR
# -----------------------------------------------------------------------------
elif menu == "📊 Ders Slaytları":
    st.header("📊 Ders Materyalleri")
    
    if not os.path.exists(SLIDES_DIR):
        os.makedirs(SLIDES_DIR)
        st.warning(f"Lütfen PDF'leri '{SLIDES_DIR}' klasörüne atın.")
    
    pdf_files = sorted([f for f in os.listdir(SLIDES_DIR) if f.lower().endswith('.pdf')])
    
    if pdf_files:
        selected_pdf = st.selectbox("Slayt Seç:", pdf_files)
        pdf_path = os.path.join(SLIDES_DIR, selected_pdf)
        
        with open(pdf_path, "rb") as f:
            st.download_button("📥 İndir", f, file_name=selected_pdf)
        
        pdf_viewer(pdf_path, height=800)
    else:
        st.info("Slayt bulunamadı.")

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div class="thank-wrapper">
    <button class="thank-btn">✨ Teşekkür etmek tamamen ücretsiz ✨</button>
</div>
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
