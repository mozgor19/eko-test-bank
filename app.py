import streamlit as st
import os
import random
import time
from streamlit_pdf_viewer import pdf_viewer
from dotenv import load_dotenv

# Env yükle
load_dotenv()

# Kendi modüllerimiz
from utils.docx_parser import parse_docx
from utils.db_manager import * # Hepsini al
from utils.email_helper import send_reset_code

# -----------------------------------------------------------------------------
# AYARLAR
# -----------------------------------------------------------------------------
st.set_page_config(page_title="ekoTestBank", page_icon="🎓", layout="wide")

# --- GEÇİCİ DÜZELTME KODU BAŞLANGIÇ ---
import os
db_file = os.path.join("data", "user_data.db")
if "db_fixed" not in st.session_state:
    if os.path.exists(db_file):
        os.remove(db_file)
        st.toast("Eski veritabanı tespit edildi ve silindi!", icon="🗑️")
    st.session_state.db_fixed = True
# --- GEÇİCİ DÜZELTME KODU BİTİŞ ---
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "questions")
SLIDES_DIR = os.path.join(BASE_DIR, "data", "slides")

# CSS
css_path = os.path.join(BASE_DIR, "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""<meta name="apple-mobile-web-app-capable" content="yes"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
if 'all_questions' not in st.session_state: st.session_state.all_questions = []
if 'current_quiz' not in st.session_state: st.session_state.current_quiz = []
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'username' not in st.session_state: st.session_state.username = None 
if 'role' not in st.session_state: st.session_state.role = None 
if 'reset_stage' not in st.session_state: st.session_state.reset_stage = 0 # 0: Yok, 1: Kod Gir, 2: Şifre Gir
if 'reset_email' not in st.session_state: st.session_state.reset_email = ""

# -----------------------------------------------------------------------------
# FONKSİYONLAR
# -----------------------------------------------------------------------------
def load_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        st.error(f"'{DATA_DIR}' klasörü yok.")
        return
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.docx')]
    if not files:
        st.warning("Dosya bulunamadı.")
        return
    all_loaded = []
    my_bar = st.progress(0, text="Yükleniyor...")
    for idx, file_name in enumerate(files):
        ch_name = file_name.split('.')[0]
        qs = parse_docx(os.path.join(DATA_DIR, file_name), ch_name)
        all_loaded.extend(qs)
        my_bar.progress((idx + 1) / len(files))
    my_bar.empty()
    st.session_state.all_questions = all_loaded
    st.session_state.data_loaded = True
    st.rerun()

# -----------------------------------------------------------------------------
# SIDEBAR (LOGIN & MENÜ)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# SIDEBAR (LOGIN & MENÜ)
# -----------------------------------------------------------------------------
with st.sidebar:
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path): 
        st.image(logo_path, width=100)
    else: 
        st.title("🎓 ekoTestBank")
    
    st.write("---")
    
    if st.session_state.username:
        # --- GİRİŞ YAPILMIŞ DURUM ---
        st.success(f"👤 **{st.session_state.username}**")
        if st.button("Çıkış Yap", type="secondary", use_container_width=True):
            st.session_state.username = None
            st.session_state.role = None
            st.rerun()
            
        # --- SADECE ADMIN GÖRÜR ---
        if st.session_state.role == 'admin':
            st.markdown("---")
            st.error("🔒 **YÖNETİCİ PANELİ**")
            
            # 1. Kullanıcı Yönetimi
            with st.expander("🛠️ Şifre Yönetimi"):
                users_list = get_all_users() # db_manager'dan gelir
                if users_list:
                    selected_u = st.selectbox("Kullanıcı Seç:", users_list)
                    new_p = st.text_input("Yeni Şifre Ata:", type="password", key="admin_new_pass")
                    if st.button("Şifreyi Güncelle", use_container_width=True):
                        if new_p:
                            admin_reset_password(selected_u, new_p)
                            st.success(f"{selected_u} güncellendi!")
                        else:
                            st.warning("Şifre girmediniz.")
                else: 
                    st.info("Henüz kayıtlı kullanıcı yok.")
            
            # 2. Veritabanı Sıfırlama (İstediğin Özellik)
            with st.expander("💣 Tehlikeli Bölge"):
                st.warning("Tüm kullanıcılar ve hatalar silinir!")
                if st.button("🧨 Fabrika Ayarlarına Dön", type="primary", use_container_width=True):
                    import os
                    db_path = os.path.join("data", "user_data.db")
                    if os.path.exists(db_path):
                        try:
                            os.remove(db_path) # Dosyayı sil
                            st.toast("Veritabanı imha edildi! Yeniden kuruluyor...", icon="🔥")
                            time.sleep(2)
                            init_db() # Yeni ve temiz DB oluştur
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")
                    else:
                        st.warning("Zaten veritabanı yok.")

    else:
        # --- GİRİŞ YAPILMAMIŞ DURUM (Misafir) ---
        st.info("Misafir Modu")
        tab1, tab2, tab3 = st.tabs(["Giriş", "Kayıt", "Unuttum"])
        
        # Giriş Sekmesi
        with tab1:
            l_user = st.text_input("Kullanıcı Adı", key="l_u")
            l_pass = st.text_input("Şifre", type="password", key="l_p")
            if st.button("Giriş Yap", use_container_width=True):
                role = login_user(l_user, l_pass)
                if role:
                    st.session_state.username = l_user
                    st.session_state.role = role
                    st.success("Giriş Başarılı!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Hatalı bilgi.")

        # Kayıt Sekmesi
        with tab2:
            r_user = st.text_input("Kullanıcı Adı", key="r_u")
            r_mail = st.text_input("E-Posta", key="r_m")
            r_pass = st.text_input("Şifre (Min 6)", type="password", key="r_p")
            if st.button("Kayıt Ol", use_container_width=True):
                # Basit Regex Kontrolü
                import re
                if not r_user or not r_mail or not r_pass:
                    st.warning("Alanları doldurun.")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", r_mail):
                    st.error("Geçersiz E-Posta.")
                else:
                    res = add_user(r_user, r_mail, r_pass)
                    if res == "success": st.success("Kayıt Başarılı! Giriş yapınız.")
                    elif res == "email_exist_error": st.error("Bu e-posta kayıtlı.")
                    elif res == "user_exist_error": st.error("Kullanıcı adı alınmış.")
                    else: st.error("Hata oluştu.")

        # Şifremi Unuttum Sekmesi
        with tab3:
            if st.session_state.reset_stage == 0:
                f_mail = st.text_input("Kayıtlı E-Posta:", key="f_m")
                if st.button("Kod Gönder", use_container_width=True):
                    code = set_reset_code(f_mail)
                    if code:
                        sent, msg = send_reset_code(f_mail, code)
                        if sent:
                            st.session_state.reset_email = f_mail
                            st.session_state.reset_stage = 1
                            st.success("Kod gönderildi!")
                            st.rerun()
                        else: st.error(f"Mail hatası: {msg}")
                    else: st.error("Mail bulunamadı.")
            
            elif st.session_state.reset_stage == 1:
                st.info(f"Kod gönderildi: {st.session_state.reset_email}")
                f_code = st.text_input("Doğrulama Kodu:", key="f_c")
                if st.button("Doğrula", use_container_width=True):
                    if verify_reset_code(st.session_state.reset_email, f_code):
                        st.session_state.reset_stage = 2
                        st.rerun()
                    else: st.error("Hatalı kod.")
            
            elif st.session_state.reset_stage == 2:
                new_pass = st.text_input("Yeni Şifre:", type="password", key="n_p")
                if st.button("Değiştir", use_container_width=True):
                    if len(new_pass) >= 6:
                        reset_password_with_code(st.session_state.reset_email, new_pass)
                        st.success("Başarılı! Giriş yapabilirsiniz.")
                        st.session_state.reset_stage = 0
                        time.sleep(2)
                        st.rerun()
                    else: st.error("Şifre çok kısa.")

    st.write("---")
    menu = st.radio("Menü", ["📝 Quiz Çöz", "❌ Hatalarım", "📊 Ders Slaytları"])
    st.markdown("---")
    
    # İstatistik ve Yenileme
    if st.session_state.data_loaded:
        st.caption(f"📊 {len(st.session_state.all_questions)} soru aktif.")
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
        if st.button("🚀 Soruları Yükle", type="primary"): load_data()
        st.stop()

    quiz_mode = st.radio("Mod:", ["📚 Chapter Bazlı", "🔀 Karma Test"], horizontal=True)
    st.divider()

    with st.expander("🛠️ Ayarlar", expanded=True):
        if quiz_mode == "📚 Chapter Bazlı":
            chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
            selected_chap = st.selectbox("Chapter:", chapters)
            if st.button("Başlat ▶", type="primary", use_container_width=True):
                st.session_state.current_quiz = [q for q in st.session_state.all_questions if q['chapter'] == selected_chap]
                st.rerun()
        else:
            chapters = sorted(list(set(q['chapter'] for q in st.session_state.all_questions)))
            selected_chaps = st.multiselect("Dahil Et:", chapters, default=chapters)
            c1, c2 = st.columns(2)
            with c1: q_count = st.number_input("Sayı:", 5, 200, 20)
            with c2: is_random = st.checkbox("Karıştır", value=True)
            if st.button("Oluştur ✨", type="primary", use_container_width=True):
                filtered = [q for q in st.session_state.all_questions if q['chapter'] in selected_chaps]
                if filtered:
                    sample = random.sample(filtered, min(q_count, len(filtered))) if is_random else filtered[:q_count]
                    st.session_state.current_quiz = sample
                    st.rerun()
                else: st.error("Chapter seçin.")

    current_qs = st.session_state.current_quiz
    if not current_qs: st.info("👈 Test oluşturun.")
    else:
        with st.sidebar:
            st.markdown("---")
            q_map = {f"{i+1}. {q['id']}": i for i, q in enumerate(current_qs)}
            jump = st.selectbox("🔎 Git:", list(q_map.keys()), index=None)
            if jump:
                idx = q_map[jump]
                st.markdown(f"<script>location.href = '#q-{idx}';</script>", unsafe_allow_html=True)

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
                    if sel == q['answer']: st.success("✅ Doğru")
                    else:
                        st.error(f"❌ Yanlış. Cevap: **{q['answer'].upper()}**")
                        if st.session_state.username:
                            log_mistake(st.session_state.username, q['id'], q['chapter'])
                        else: st.warning("⚠️ Giriş yapmadınız, hata kaydedilmedi.")
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
        st.warning("🔒 Lütfen giriş yapın.")
        st.stop()
    if not st.session_state.data_loaded:
        if st.button("🚀 Soruları Yükle", type="primary"): load_data()
        st.stop()

    mistakes = get_mistakes(st.session_state.username)
    ids = [m[0] for m in mistakes]
    quiz_pool = [q for q in st.session_state.all_questions if q['id'] in ids]

    if not quiz_pool: st.success("🎉 Hatanız yok!")
    else:
        st.info(f"{len(quiz_pool)} hatalı soru var.")
        for i, q in enumerate(quiz_pool):
            with st.expander(f"Soru {i+1} ({q['id']})", expanded=True):
                st.markdown(q['body_html'], unsafe_allow_html=True)
                opts = list(q['options'].keys())
                fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
                key = f"ans_mistake_{i}_{q['id']}"
                user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
                if user_choice:
                    sel = user_choice.split(')')[0]
                    if sel == q['answer']: st.success("✅ Doğru")
                    else: st.error(f"❌ Yanlış. Cevap: **{q['answer'].upper()}**")
                
                if st.button("🗑️ Sil", key=f"del_{q['id']}"):
                    remove_mistake(st.session_state.username, q['id'])
                    st.toast("Silindi!", icon="🗑️")
                    time.sleep(0.5)
                    st.rerun()

# -----------------------------------------------------------------------------
# 3. SLAYTLAR
# -----------------------------------------------------------------------------
elif menu == "📊 Ders Slaytları":
    st.header("📊 Ders Materyalleri")
    if not os.path.exists(SLIDES_DIR): os.makedirs(SLIDES_DIR)
    pdf_files = sorted([f for f in os.listdir(SLIDES_DIR) if f.lower().endswith('.pdf')])
    if pdf_files:
        selected_pdf = st.selectbox("Dosya:", pdf_files)
        path = os.path.join(SLIDES_DIR, selected_pdf)
        with open(path, "rb") as f:
            st.download_button("📥 İndir", f, file_name=selected_pdf)
        pdf_viewer(path, height=800)
    else: st.info("Dosya yok.")

# FOOTER
st.markdown("---")
st.markdown("""<div class="thank-wrapper"><button class="thank-btn">✨ Teşekkür etmek tamamen ücretsiz ✨</button></div><button onclick="topFunction()" id="myBtn" title="Başa Dön">⬆️</button><script>var mybutton = document.getElementById("myBtn");window.onscroll = function() {scrollFunction()};function scrollFunction() {if (document.body.scrollTop > 500 || document.documentElement.scrollTop > 500) {mybutton.style.display = "block";} else {mybutton.style.display = "none";}}function topFunction() {document.body.scrollTop = 0;document.documentElement.scrollTop = 0;}</script>""", unsafe_allow_html=True)




