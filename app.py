import streamlit as st
import mammoth
from bs4 import BeautifulSoup
import re
import random
import os

# -----------------------------------------------------------------------------
# 1. DOCX -> HTML -> AKILLI AYRIŞTIRMA (Geliştirilmiş Mantık)
# -----------------------------------------------------------------------------
def parse_docx_smart(file_obj, chapter_name):
    """
    Soruları, şıkları, cevabı ve aradaki yetim kalan (orphaned) resimleri
    doğru soruya atayan akıllı fonksiyon.
    """
    # 1. Mammoth ile HTML'e çevir (Resimler Base64 olarak gömülür)
    result = mammoth.convert_to_html(file_obj)
    html = result.value
    
    soup = BeautifulSoup(html, "html.parser")
    
    questions = []
    
    # Durum değişkenleri
    current_q = None        # Şu an işlenen soru verisi
    question_active = False # Şu an bir soru bloğunun içinde miyiz?
    
    # Tamponlar
    buffer_html = ""        # Sorunun metni için tampon
    preamble_html = ""      # İki soru arasındaki "yetim" içerikler (Resimler buraya düşer)
    options = {}
    answer = None
    ref = None
    q_id = None

    # Regexler
    # Soru başlangıcı: "73." veya "1." gibi
    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') 
    # Şıklar: "a." veya "a)"
    opt_pattern = re.compile(r'^\s*([a-d])[\.\)]\s+(.*)', re.IGNORECASE)
    # Cevap: "ANS: C" veya "Answer: C"
    ans_pattern = re.compile(r'(?:ANS|Answer):\s+([A-D])', re.IGNORECASE)
    ref_pattern = re.compile(r'REF:\s+(.*)')

    # HTML içindeki tüm elementleri (P, Table, vs.) sırayla gez
    elements = soup.find_all(['p', 'table']) 
    
    for elem in elements:
        text = elem.get_text().strip()
        # raw_html: Resimler (<img src...>) bunun içindedir
        raw_html = str(elem) 

        # --- SENARYO 1: YENİ SORU BAŞLANGICI MI? ---
        match_q = q_start_pattern.match(text)
        if match_q:
            # Eğer önceki bir soru varsa ve tamamlandıysa listeye kaydet
            if current_q and len(options) >= 2 and answer:
                questions.append({
                    'id': q_id,
                    'chapter': chapter_name,
                    # preamble_html (önceki sorudan artan resimler) + buffer_html (soru metni)
                    'body_html': buffer_html, 
                    'options': options,
                    'answer': answer.lower(),
                    'ref': ref
                })

            # Yeni soruyu başlat
            question_active = True
            
            q_num = match_q.group(1)
            q_text_content = match_q.group(2)
            q_id = f"{chapter_name} - Q{q_num}"
            
            # --- KRİTİK DÜZELTME ---
            # Eğer preamble_html doluysa (yani önceki soru bittikten sonra bir resim/figür geldiyse),
            # bu resim ASLINDA BU YENİ SORUYA AİTTİR.
            # O yüzden preamble'ı bu sorunun başı yapıyoruz.
            
            # Soru metnini kalın yapalım
            q_text_html = f"<p><b>{q_text_content}</b></p>"
            
            # Önce resim (preamble), sonra soru metni
            buffer_html = preamble_html + q_text_html
            
            # Değişkenleri sıfırla
            preamble_html = "" # Artık kullandık, temizle
            options = {}
            answer = None
            ref = None
            continue

        # --- SENARYO 2: CEVAP SATIRI MI? ---
        match_ans = ans_pattern.search(text)
        if match_ans:
            answer = match_ans.group(1)
            # Cevabı bulduğumuz an soruyu "pasif" yapalım.
            # Böylece bundan sonra gelen resimler bu soruya değil, 
            # bir sonraki sorunun (preamble) tamponuna gider.
            question_active = False 
            
            # Aynı satırda REF var mı bakalım
            match_ref = ref_pattern.search(text)
            if match_ref:
                ref = match_ref.group(1)
            continue
        
        # --- SENARYO 3: ŞIK MI? ---
        if question_active: # Şıklar sadece soru aktifken aranır
            match_opt = opt_pattern.match(text)
            if match_opt:
                opt_char = match_opt.group(1).lower()
                opt_text = match_opt.group(2)
                options[opt_char] = opt_text
                continue

        # --- SENARYO 4: GENEL İÇERİK (RESİM, TABLO, METİN) ---
        # Eğer yukarıdakiler değilse, bu bir içeriktir.
        if "REF:" not in text and "ANS:" not in text:
            if question_active:
                # Soru hala aktif (henüz cevap gelmedi), o zaman bu sorunun parçasıdır.
                buffer_html += raw_html
            else:
                # Soru bitti (cevap geldi) ama yeni soru numarası daha gelmedi.
                # Demek ki bu arada kalan şey (Figür 4-1 vs.) BİR SONRAKİ SORUNUN parçası.
                preamble_html += raw_html

    # Döngü bittiğinde son soruyu da eklemeyi unutma
    if len(options) >= 2 and answer:
        questions.append({
            'id': q_id,
            'chapter': chapter_name,
            'body_html': preamble_html + buffer_html, # Varsa son preamble'ı da ekle
            'options': options,
            'answer': answer.lower(),
            'ref': ref
        })

    return questions

# -----------------------------------------------------------------------------
# 2. UYGULAMA ARAYÜZÜ
# -----------------------------------------------------------------------------

st.set_page_config(page_title="ekoTestBank Pro", layout="wide")

# CSS İLE RESİM BOYUTLANDIRMA VE STİL
st.markdown("""
<style>
    /* Resimlerin maksimum boyutunu ayarla */
    img {
        max-width: 100%;       /* Ekran dışına taşmasın */
        max-height: 350px;     /* Çok uzun olmasın */
        width: auto;           /* Oranı bozma */
        display: block;
        margin-bottom: 10px;
        border-radius: 5px;
        border: 1px solid #ddd;
        cursor: pointer;       /* Tıklanabilir hissi ver (browser zoom için) */
    }
    /* Soru metni daha okunaklı olsun */
    .stMarkdown p {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎓 ekoTestBank - Görsel Destekli Pro")
st.markdown("---")

if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    if st.button("📂 Klasördeki .docx Dosyalarını Tara"):
        local_files = [f for f in os.listdir('.') if f.endswith('.docx')]
        if local_files:
            all_loaded = []
            bar = st.progress(0)
            for idx, file_name in enumerate(local_files):
                ch_name = file_name.split('.')[0]
                with open(file_name, "rb") as f:
                    # YENİ FONKSİYONU KULLANIYORUZ
                    qs = parse_docx_smart(f, ch_name)
                    all_loaded.extend(qs)
                bar.progress((idx + 1) / len(local_files))
            st.session_state.all_questions = all_loaded
            st.success(f"{len(all_loaded)} soru yüklendi.")
        else:
            st.warning("Klasörde .docx dosyası yok.")

    if st.session_state.all_questions:
        st.markdown("---")
        mode = st.radio("Mod Seç", ["Chapter Bazlı", "Karma Test"])
        all_qs = st.session_state.all_questions
        
        if mode == "Chapter Bazlı":
            chapters = sorted(list(set(q['chapter'] for q in all_qs)))
            sel_chap = st.selectbox("Chapter:", chapters)
            # Seçim değişirse quizi sıfırla
            if st.button("Bu Chapter'ı Çöz"):
                st.session_state.current_quiz = [q for q in all_qs if q['chapter'] == sel_chap]
                st.session_state.user_answers = {}
                st.rerun()
            
        else:
            chapters = sorted(list(set(q['chapter'] for q in all_qs)))
            target_chaps = st.multiselect("Chapterlar:", chapters)
            count = st.number_input("Soru Sayısı:", 5, 200, 20)
            if st.button("Karma Test Oluştur"):
                pool = [q for q in all_qs if q['chapter'] in target_chaps]
                if pool:
                    st.session_state.current_quiz = random.sample(pool, min(count, len(pool)))
                    st.session_state.user_answers = {}
                    st.rerun()

# --- ANA EKRAN ---
if not st.session_state.current_quiz:
    st.info("👈 Soldan dosya yükleyin veya klasörü taratın.")
else:
    st.subheader(f"📝 Quiz ({len(st.session_state.current_quiz)} Soru)")
    
    for i, q in enumerate(st.session_state.current_quiz):
        with st.expander(f"Soru {i+1} ({q['id']})", expanded=True):
            
            # 1. HTML Render (Resimler + Metin)
            st.markdown(q['body_html'], unsafe_allow_html=True)
            
            # 2. Şıklar
            opts = list(q['options'].keys())
            fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
            
            key = f"ans_{i}_{q['id']}"
            user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
            
            # 3. Kontrol
            if user_choice:
                sel = user_choice.split(')')[0]
                corr = q['answer']
                if sel == corr:
                    st.success("✅ Doğru")
                else:
                    st.error(f"❌ Yanlış. Cevap: {corr.upper()}")
                
                if q.get('ref'):
                    st.caption(f"Ref: {q['ref']}")