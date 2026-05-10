import streamlit as st
import os
import random
import time
import importlib
from streamlit_pdf_viewer import pdf_viewer
from dotenv import load_dotenv

# Env yükle
load_dotenv()
importlib.invalidate_caches()

from utils.docx_parser import PARSER_CACHE_VERSION, parse_docx
from utils.db_manager import *
from utils.email_helper import send_reset_code, send_admin_notification

# -----------------------------------------------------------------------------
# AYARLAR
# -----------------------------------------------------------------------------
st.set_page_config(page_title="ekoTestBank", page_icon="🎓", layout="wide")
st.markdown("<div id='en-tepe'></div>", unsafe_allow_html=True)
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "questions")
SLIDES_DIR = os.path.join(BASE_DIR, "data", "slides")

st.markdown("""
<style>
    /* Resimler */
    img { max-width: 100%; max-height: 350px; border-radius: 5px; }
    
    /* Soruya Git Butonunun Gideceği Yer için Boşluk (Header'ın altında kalmasın diye) */
    div[id^='q-'] {
        scroll-margin-top: 80px; 
    }

    /* Teşekkür Butonu Stili (Streamlit butonunu eziyoruz) */
    div.stButton > button.thank-btn-style {
        background: linear-gradient(90deg, #FF4B4B, #FF914D);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 50px;
        font-weight: bold;
        transition: transform 0.2s;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    div.stButton > button.thank-btn-style:hover {
        transform: scale(1.02);
        border-color: white;
        color: white;
    }
    div.stButton > button.thank-btn-style:focus {
        color: white;
    }

    /* Scroll to Top Butonu */
    #myBtn {
        display: none;
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 99;
        border: none;
        background-color: #FF4B4B;
        color: white;
        cursor: pointer;
        padding: 10px;
        border-radius: 50%;
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""<meta name="apple-mobile-web-app-capable" content="yes"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
if 'all_questions' not in st.session_state: st.session_state.all_questions = []
if 'current_quiz' not in st.session_state: st.session_state.current_quiz = []
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'username' not in st.session_state: st.session_state.username = None
if 'role' not in st.session_state: st.session_state.role = None
if 'reset_stage' not in st.session_state: st.session_state.reset_stage = 0
if 'reset_email' not in st.session_state: st.session_state.reset_email = ""

@st.cache_data(show_spinner=False)
def parse_docx_cached(file_path, chapter_name, modified_ns, file_size, parser_version):
    return parse_docx(file_path, chapter_name)

def question_storage_id(question):
    return question.get('uid') or question['id']

def mistake_id_for_question(question, mistake_ids):
    storage_id = question_storage_id(question)
    if storage_id in mistake_ids:
        return storage_id
    return question['id']

def fragment(func):
    if hasattr(st, "fragment"):
        return st.fragment(func)
    return func

def show_answer_feedback(question, user_choice, context, index, save_mistake=False):
    selected = user_choice.split(')', 1)[0]
    storage_id = question_storage_id(question)
    answer_state_key = f"checked_{context}_{index}_{storage_id}"
    is_new_selection = st.session_state.get(answer_state_key) != selected
    st.session_state[answer_state_key] = selected

    if selected == question['answer']:
        st.success("✅ Doğru")
    else:
        st.error(f"❌ Yanlış. Cevap: **{question['answer'].upper()}**")
        if save_mistake and is_new_selection:
            if st.session_state.username:
                log_mistake_async(st.session_state.username, storage_id, question['chapter'])
            else:
                st.warning("⚠️ Giriş yapmadınız, hata kaydedilmedi.")
        elif save_mistake and not st.session_state.username:
            st.warning("⚠️ Giriş yapmadınız, hata kaydedilmedi.")

@fragment
def render_question(question, index, context, save_mistake=False, mistake_ids=None):
    mistake_ids = set(mistake_ids or [])
    storage_id = question_storage_id(question)

    with st.expander(f"Soru {index+1} ({question['id']})", expanded=True):
        st.markdown(question['body_html'], unsafe_allow_html=True)
        fmt_opts = [f"{k}) {v}" for k, v in question['options'].items()]
        key = f"ans_{context}_{index}_{storage_id}"
        user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
        if user_choice:
            show_answer_feedback(question, user_choice, context, index, save_mistake=save_mistake)
            if context == "quiz":
                st.divider()
                c1, c2, c3 = st.columns(3)
                if question.get('ref'): c1.caption(f"Ref: {question['ref']}")
                if question.get('top'): c2.caption(f"Konu: {question['top']}")
                if question.get('msc'): c3.caption(f"Tip: {question['msc']}")

        if context == "mistake":
            mistake_id = mistake_id_for_question(question, mistake_ids)
            if st.button("🗑️ Sil", key=f"del_{index}_{storage_id}"):
                remove_mistake(st.session_state.username, mistake_id)
                st.toast("Silindi!", icon="🗑️")
                time.sleep(0.5)
                st.rerun()

# -----------------------------------------------------------------------------
# DİALOG (POPUP) FONKSİYONLARI
# -----------------------------------------------------------------------------
@st.dialog("✨ Bize Ulaşın & Teşekkür Edin")
def feedback_dialog():
    st.write("Uygulamayı beğendiyseniz bir teşekkür bırakabilir veya hata bildirebilirsiniz.")
    
    st.subheader("💖 Hızlı Etkileşim")
    if st.button("🚀 Harika bir uygulama! (Teşekkür Gönder)", use_container_width=True):
        user_display = st.session_state.username if st.session_state.username else "Misafir Kullanıcı"
        send_admin_notification("Teşekkür Mesajı", "Bir kullanıcı uygulamayı beğendi ve teşekkür butonuyla bildirim gönderdi.", user_display)
        st.success("Teşekkürünüz iletildi! İyi çalışmalar 🎓")
        time.sleep(1.5)
        st.rerun()

    st.markdown("---")

    st.subheader("✍️ Detaylı Geri Bildirim")
    if st.session_state.username:
        with st.form("feedback_form"):
            msg = st.text_area("Mesajınız, öneriniz veya hata bildiriminiz:", placeholder="Buraya yazın...")
            submit = st.form_submit_button("Gönder")
            
            if submit and msg:
                send_admin_notification("Kullanıcı Yorumu", msg, st.session_state.username)
                st.success("Mesajınız yöneticiye iletildi.")
                time.sleep(1.5)
                st.rerun()
    else:
        st.info("Detaylı mesaj yazmak için lütfen **Giriş Yapın**.")

# -----------------------------------------------------------------------------
# FONKSİYONLAR
# -----------------------------------------------------------------------------
def load_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        st.error(f"'{DATA_DIR}' klasörü yok.")
        return
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.docx')])
    if not files:
        st.warning("Dosya bulunamadı.")
        return
    all_loaded = []
    my_bar = st.progress(0, text="Yükleniyor...")
    for idx, file_name in enumerate(files):
        ch_name = file_name.split('.')[0]
        file_path = os.path.join(DATA_DIR, file_name)
        stat = os.stat(file_path)
        qs = parse_docx_cached(file_path, ch_name, stat.st_mtime_ns, stat.st_size, PARSER_CACHE_VERSION)
        all_loaded.extend(qs)
        my_bar.progress((idx + 1) / len(files))
    my_bar.empty()
    st.session_state.all_questions = all_loaded
    st.session_state.data_loaded = True
    st.rerun()

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path): st.image(logo_path, width=100)
    else: st.title("🎓 ekoTestBank")
    st.link_button("🔗 İTÜ EKO201E Ders Sayfası", "https://econ.itu.edu.tr/egitim/lisans/havuz-dersi-eko201e", use_container_width=True)
    
    st.write("---")
    
    if st.session_state.username:
        st.success(f"👤 **{st.session_state.username}**")
        if st.button("Çıkış Yap", type="secondary", use_container_width=True):
            st.session_state.username = None
            st.session_state.role = None
            st.rerun()
            
        if st.session_state.role == 'admin':
            st.markdown("---")
            st.warning("🔒 **YÖNETİCİ**")
            with st.expander("🛠️ Kullanıcılar"):
                users_list = get_all_users()
                if users_list:
                    selected_u = st.selectbox("Kullanıcı:", users_list)
                    new_p = st.text_input("Yeni Şifre:", type="password")
                    if st.button("Güncelle"):
                        if new_p:
                            admin_reset_password(selected_u, new_p)
                            st.success("Güncellendi!")
                else: st.info("Kullanıcı yok.")
            
            with st.expander("⚠️ Geliştirici"):
                if st.button("🧨 DB Sıfırla"):
                    import os
                    db_path = os.path.join("data", "user_data.db")
                    if os.path.exists(db_path):
                        os.remove(db_path)
                        st.toast("Silindi!", icon="🗑️")
                        time.sleep(2)
                        init_db()
                        st.rerun()
    else:
        st.info("Misafir Modu")
        tab1, tab2, tab3 = st.tabs(["Giriş", "Kayıt", "Şifremi Unuttum"])
        
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
                else: st.error("Hatalı bilgi.")

        with tab2:
            r_user = st.text_input("Kullanıcı Adı", key="r_u")
            r_mail = st.text_input("E-Posta", key="r_m")
            r_pass = st.text_input("Şifre (Min 6)", type="password", key="r_p")
            if st.button("Kayıt Ol", use_container_width=True):
                if r_user and r_mail and r_pass:
                    res = add_user(r_user, r_mail, r_pass)
                    if res == "success": st.success("Kayıt Başarılı!")
                    elif res == "email_exist_error": st.error("E-posta kayıtlı.")
                    elif res == "user_exist_error": st.error("Kullanıcı adı alınmış.")
                    else: st.error("Hata.")
                else: st.warning("Eksik bilgi.")

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
                        else: st.error(f"Hata: {msg}")
                    else: st.error("Mail bulunamadı.")
            elif st.session_state.reset_stage == 1:
                st.info(f"Kod gönderildi: {st.session_state.reset_email}")
                f_code = st.text_input("Kod:", key="f_c")
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
                        st.success("Şifre değişti!")
                        st.session_state.reset_stage = 0
                        time.sleep(2)
                        st.rerun()
                    else: st.error("Kısa şifre.")

    st.write("---")
    menu = st.radio("Menü", ["📝 Quiz Çöz", "❌ Hatalarım", "📊 Ders Slaytları"])
    st.markdown("---")
    if st.session_state.data_loaded:
        if st.button("🔄 Verileri Yenile", use_container_width=True):
            st.session_state.data_loaded = False
            st.session_state.all_questions = []
            st.rerun()
    
    st.write("---")
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    if st.button("Teşekkür Etmek Tamamen Ücretsiz", type="primary", use_container_width=True):
        feedback_dialog()
        
    st.markdown("""
    <a href="#en-tepe" style="
        display: block;
        text-align: center;
        margin-top: 10px;
        padding: 10px;
        background-color: #262730;
        color: white;
        text-decoration: none;
        border-radius: 8px;
        border: 1px solid #444;
        font-weight: bold;
    ">⬆️ Sayfa Başına Dön</a>
    """, unsafe_allow_html=True)

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
            jump_key = st.selectbox("🔎 Git:", list(q_map.keys()), index=None)
            
            if jump_key:
                idx = q_map[jump_key]
                st.markdown(f"""
                <a href="#q-{idx}" style="
                    display: block;
                    width: 100%;
                    padding: 8px;
                    background-color: #FF4B4B;
                    color: white;
                    text-align: center;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin-top: 5px;
                ">➡️ Soruya Git</a>
                """, unsafe_allow_html=True)

        for i, q in enumerate(current_qs):
            st.markdown(f"<div id='q-{i}'></div>", unsafe_allow_html=True)
            render_question(q, i, "quiz", save_mistake=True)

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
    ids = {m[0] for m in mistakes}
    quiz_pool = [q for q in st.session_state.all_questions if question_storage_id(q) in ids or q['id'] in ids]

    if not quiz_pool: st.success("🎉 Hatanız yok!")
    else:
        st.info(f"{len(quiz_pool)} hatalı soru.")
        for i, q in enumerate(quiz_pool):
            render_question(q, i, "mistake", mistake_ids=tuple(ids))

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
        pdf_viewer(path, width="100%", height=800, zoom_level="auto", key=f"slides_{selected_pdf}")
    else: st.info("Dosya yok.")

# -----------------------------------------------------------------------------
# FOOTER & POPUP
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<script>
const buttons = window.parent.document.querySelectorAll('button');
buttons.forEach(btn => {
    if (btn.innerText.includes("TEŞEKKÜR ET")) {
        btn.style.background = "linear-gradient(90deg, #FF4B4B, #FF914D)";
        btn.style.color = "white";
        btn.style.fontWeight = "bold";
        btn.style.border = "none";
    }
});
</script>
""", unsafe_allow_html=True)







