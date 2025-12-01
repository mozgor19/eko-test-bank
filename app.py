import streamlit as st
import os
import random
import time
from streamlit_pdf_viewer import pdf_viewer

# Kendi modüllerimiz
from utils.docx_parser import parse_docx
from utils.db_manager import init_db, log_mistake, get_mistakes, remove_mistake, login_user, add_user, get_all_users, admin_reset_password

# -----------------------------------------------------------------------------
# AYARLAR VE BAŞLANGIÇ
# -----------------------------------------------------------------------------
st.set_page_config(page_title="ekoTestBank", page_icon="🎓", layout="wide")

# Veritabanını Başlat
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "questions")
SLIDES_DIR = os.path.join(BASE_DIR, "data", "slides")

# CSS Yükle
css_path = os.path.join(BASE_DIR, "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
if 'username' not in st.session_state:
    st.session_state.username = None 
if 'role' not in st.session_state:
    st.session_state.role = None 
# Rate Limiting için Sayaç
if 'login_attempts' not in st.session_state:
    st.session_state.login_attempts = 0

# -----------------------------------------------------------------------------
# FONKSİYONLAR
# -----------------------------------------------------------------------------
def load_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        st.error(f"Lütfen soru dosyalarını '{DATA_DIR}' klasörüne atın.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.docx')]
    if not files:
        st.warning(f"'{DATA_DIR}' klasöründe dosya bulunamadı.")
        return

    all_loaded = []
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
    time.sleep(1)
    st.rerun()

# -----------------------------------------------------------------------------
# KENAR ÇUBUĞU (GİRİŞ VE MENÜ)
# -----------------------------------------------------------------------------
with st.sidebar:
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=100)
    else:
        st.title("🎓 ekoTestBank")
    
    st.write("---")
    
    # --- GİRİŞ SİSTEMİ ---
    if st.session_state.username:
        st.success(f"👤 **{st.session_state.username}**")
        if st.button("Çıkış Yap", type="secondary", use_container_width=True):
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.login_attempts = 0 # Sayacı sıfırla
            st.rerun()
            
        if st.session_state.role == 'admin':
            st.markdown("---")
            st.warning("🔒 **YÖNETİCİ PANELİ**")
            with st.expander("🛠️ Kullanıcı Yönetimi"):
                users_list = get_all_users()
                if users_list:
                    selected_user_to_reset = st.selectbox("Kullanıcı Seç:", users_list)
                    new_pass_admin = st.text_input("Yeni Şifre Ata:", type="password")
                    if st.button("Şifreyi Güncelle"):
                        if new_pass_admin:
                            admin_reset_password(selected_user_to_reset, new_pass_admin)
                            st.success(f"{selected_user_to_reset} güncellendi!")
                        else:
                            st.error("Şifre girin.")
            with st.expander("⚠️ DB Ayarları"):
                if st.button("🧨 Veritabanını Sıfırla"):
                    import os
                    db_path = os.path.join("data", "user_data.db")
                    if os.path.exists(db_path):
                        try:
                            os.remove(db_path)
                            st.toast("Silindi! Yeniden başlatılıyor...", icon="🗑️")
                            time.sleep(2)
                            init_db()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")

    else:
        st.info("Misafir Modu")
        tab1, tab2 = st.tabs(["Giriş", "Kayıt"])
        
        with tab1:
            l_user = st.text_input("Kullanıcı Adı", key="l_user")
            l_pass = st.text_input("Şifre", type="password", key="l_pass")
            
            col_l1, col_l2 = st.columns([1,1])
            with col_l1:
                if st.button("Giriş Yap", use_container_width=True):
                    # RATE LIMITING (Hız Sınırı)
                    if st.session_state.login_attempts > 3:
                        st.error("🛑 Çok fazla deneme! 5 saniye bekleyin.")
                        time.sleep(5) # Ceza süresi
                    
                    role = login_user(l_user, l_pass)
                    if role:
                        st.session_state.username = l_user
                        st.session_state.role = role
                        st.session_state.login_attempts = 0 # Başarılıysa sıfırla
                        st.success("Başarılı!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1 # Hatayı artır
                        st.error(f"Hatalı bilgi. (Deneme: {st.session_state.login_attempts})")
            
            with col_l2:
                if st.button("Şifremi Unuttum", use_container_width=True):
                    st.info("Yönetici ile iletişime geçin.")

        with tab2:
            r_user = st.text_input("Yeni Kullanıcı Adı", key="r_user")
            r_pass = st.text_input("Yeni Şifre (Min 8 karakter)", type="password", key="r_pass")
            if st.button("Kayıt Ol", use_container_width=True):
                if r_user and r_pass:
                    result = add_user(r_user, r_pass)
                    if result == "success":
                        st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                    elif result == "password_length_error":
                        st.error("🔐 Şifre en az 8 karakter olmalıdır!")
                    elif result == "admin_name_error":
                        st.error("⛔ 'Admin' ismini kullanamazsınız.")
                    elif result == "exists_error":
                        st.error("Bu kullanıcı adı zaten alınmış.")
                else:
                    st.warning("Bilgileri doldurun.")

    st.write("---")
    menu = st.radio("Menü", ["📝 Quiz Çöz", "❌ Hatalarım", "📊 Ders Slaytları"])
    st.markdown("---")

    if st.session_state.data_loaded:
        st.caption(f"📚 Havuz: {len(st.session_state.all_questions)} Soru")
        if st.button("🔄 Verileri Yenile", use_container_width=True):
            st.session_state.data_loaded = False
            st.session_state.all_questions = []
            st.rerun()

# -----------------------------------------------------------------------------
# 1. QUIZ ÇÖZ
# -----------------------------------------------------------------------------
if menu == "📝 Quiz Çöz":
    st.header(menu)
    
    if not st.session_state.data_loaded:
        st.info("Soru havuzunu yükleyerek başlayın.")
        if st.button("🚀 Soruları Yükle", type="primary"):
            load_data()
        st.stop()

    quiz_mode = st.radio("Mod Seçimi:", ["📚 Chapter Bazlı", "🔀 Karma Test"], horizontal=True)
    st.divider()

    with st.expander("🛠️ Test Ayarları", expanded=True):
        if quiz_mode == "📚 Chapter Bazlı":
            chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
            selected_chap = st.selectbox("Chapter Seç:", chapters)
            if st.button("Başlat ▶", type="primary", use_container_width=True):
                st.session_state.current_quiz = [q for q in st.session_state.all_questions if q['chapter'] == selected_chap]
                st.rerun()
        else:
            chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
            selected_chaps = st.multiselect("Dahil Et:", chapters, default=chapters)
            c1, c2 = st.columns(2)
            with c1: q_count = st.number_input("Soru Sayısı:", 5, 200, 20)
            with c2: is_random = st.checkbox("Karıştır", value=True)
            
            if st.button("Test Oluştur ✨", type="primary", use_container_width=True):
                filtered = [q for q in st.session_state.all_questions if q['chapter'] in selected_chaps]
                if filtered:
                    sample = random.sample(filtered, min(q_count, len(filtered))) if is_random else filtered[:q_count]
                    st.session_state.current_quiz = sample
                    st.rerun()
                else:
                    st.error("Chapter seçmelisiniz.")

    current_qs = st.session_state.current_quiz
    if not current_qs:
        st.info("👈 Yukarıdan test oluşturun.")
    else:
        # --- SORUYA GİTME (JUMP) DÜZELTMESİ ---
        with st.sidebar:
            st.markdown("---")
            st.write("🔎 **Hızlı Git**")
            q_map = {f"{i+1}. {q['id']}": i for i, q in enumerate(current_qs)}
            
            # Selectbox
            jump_selection = st.selectbox("Soru Seç:", list(q_map.keys()), index=None)
            
            # Seçim yapıldıysa altına HTML Link (Button Görünümlü) koyuyoruz
            if jump_selection:
                idx = q_map[jump_selection]
                # Bu HTML link, sayfayı yeniden yüklemeden direkt scroll yapar
                st.markdown(f"""
                <a href="#q-{idx}" target="_self" style="
                    display: block;
                    text-align: center;
                    background-color: #FF4B4B;
                    color: white;
                    padding: 8px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-weight: bold;
                    margin-top: 5px;">
                    ➡️ Soruya Git
                </a>
                """, unsafe_allow_html=True)

        for i, q in enumerate(current_qs):
            st.markdown(f"<div id='q-{i}'></div>", unsafe_allow_html=True)
            with st.expander(f"Soru {i+1} ({q['id']})", expanded=True):
                st.markdown(q['body_html'], unsafe_allow_html=True)
                opts = list(q['options'].keys())
                fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
                
                key = f"ans_quiz_{i}_{q['id']}"
                user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
                
                if user_choice:
                    sel = user_choice.split(')')[0]
                    corr = q['answer']
                    if sel == corr:
                        st.success("✅ Doğru")
                    else:
                        st.error(f"❌ Yanlış. Cevap: **{corr.upper()}**")
                        if st.session_state.username:
                            log_mistake(st.session_state.username, q['id'], q['chapter'])
                        else:
                            st.warning("⚠️ Giriş yapmadığınız için bu hata kaydedilmedi.")
                    st.divider()
                    c1, c2, c3 = st.columns(3)
                    if q.get('ref'): c1.caption(f"Ref: {q['ref']}")
                    if q.get('top'): c2.caption(f"Konu: {q['top']}")
                    if q.get('msc'): c3.caption(f"Tip: {q['msc']}")

# -----------------------------------------------------------------------------
# 2. HATALARIM
# -----------------------------------------------------------------------------
elif menu == "❌ Hatalarım":
    st.header(menu)
    
    if not st.session_state.username:
        st.warning("🔒 Bu özelliği kullanmak için **Giriş Yapın**.")
        st.stop()

    if not st.session_state.data_loaded:
        st.info("Önce soruları yükleyin.")
        if st.button("🚀 Soruları Yükle", type="primary"):
            load_data()
        st.stop()

    user_mistakes = get_mistakes(st.session_state.username)
    mistake_ids = [m[0] for m in user_mistakes]
    quiz_pool = [q for q in st.session_state.all_questions if q['id'] in mistake_ids]

    if not quiz_pool:
        st.success(f"🎉 Harika {st.session_state.username}! Hiç hata kaydın yok.")
    else:
        st.info(f"Toplam {len(quiz_pool)} hatalı soru var.")
        for i, q in enumerate(quiz_pool):
            with st.expander(f"Soru {i+1} ({q['id']})", expanded=True):
                st.markdown(q['body_html'], unsafe_allow_html=True)
                opts = list(q['options'].keys())
                fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
                
                key = f"ans_mistake_{i}_{q['id']}"
                user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
                
                if user_choice:
                    sel = user_choice.split(')')[0]
                    corr = q['answer']
                    if sel == corr:
                        st.success("✅ Doğru")
                    else:
                        st.error(f"❌ Yanlış. Cevap: **{corr.upper()}**")
                
                if st.button("🗑️ Listeden Sil", key=f"del_{q['id']}"):
                    remove_mistake(st.session_state.username, q['id'])
                    st.toast("Silindi!", icon="🗑️")
                    time.sleep(0.5)
                    st.rerun()

# -----------------------------------------------------------------------------
# 3. DERS SLAYTLARI
# -----------------------------------------------------------------------------
elif menu == "📊 Ders Slaytları":
    st.header("📊 Ders Materyalleri")
    if not os.path.exists(SLIDES_DIR):
        os.makedirs(SLIDES_DIR)
        st.warning("Klasör yok.")
    
    pdf_files = sorted([f for f in os.listdir(SLIDES_DIR) if f.lower().endswith('.pdf')])
    
    if pdf_files:
        selected_pdf = st.selectbox("Slayt Seç:", pdf_files)
        pdf_path = os.path.join(SLIDES_DIR, selected_pdf)
        with open(pdf_path, "rb") as f:
            st.download_button("📥 İndir", f, file_name=selected_pdf)
        pdf_viewer(pdf_path, height=800)
    else:
        st.info("Slayt yok.")

# FOOTER
st.markdown("---")
st.markdown("""
<div class="thank-wrapper"><button class="thank-btn">✨ Teşekkür etmek tamamen ücretsiz ✨</button></div>
<button onclick="topFunction()" id="myBtn" title="Başa Dön">⬆️</button>
<script>
var mybutton = document.getElementById("myBtn");
window.onscroll = function() {scrollFunction()};
function scrollFunction() {if (document.body.scrollTop > 500 || document.documentElement.scrollTop > 500) {mybutton.style.display = "block";} else {mybutton.style.display = "none";}}
function topFunction() {document.body.scrollTop = 0;document.documentElement.scrollTop = 0;}
</script>
""", unsafe_allow_html=True)
