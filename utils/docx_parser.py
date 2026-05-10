import mammoth
from bs4 import BeautifulSoup
import re
from collections import deque

def parse_docx(file_path, chapter_name):
    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value
    except Exception as e:
        return []

    soup = BeautifulSoup(html, "html.parser")
    questions = []
    
    current_q = None
    question_active = False 
    buffer_html = ""        
    attached_visual_html = ""
    visual_history = deque(maxlen=8)
    pending_visual_caption = ""
    options = {}
    answer = None
    ref = None
    q_id = None
    id_counts = {}
    
    # Metadata değişkenleri
    meta_top = None
    meta_msc = None

    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') 
    opt_pattern = re.compile(r'^\s*([a-d])[\.\)]\s+(.*)', re.IGNORECASE)
    ans_pattern = re.compile(r'(?:ANS|Answer):\s+([A-D])', re.IGNORECASE)
    ref_pattern = re.compile(r'REF:\s+(.*)')
    
    # Metadata Regexleri
    top_pattern = re.compile(r'TOP:\s*(.*)')
    msc_pattern = re.compile(r'MSC:\s*(.*)')

    table_ref_pattern = re.compile(r'\b(?:refer to|see|using|use|in)\s+(?:the\s+)?table\b|\btable\s+\d', re.IGNORECASE)
    figure_ref_pattern = re.compile(r'\b(?:refer to|see|using|use|in)\s+(?:the\s+)?figure\b|\bfigure\s+\d', re.IGNORECASE)
    visual_caption_pattern = re.compile(r'^(?:Table|Figure)\s+[\w.-]+', re.IGNORECASE)
    visual_ref_token_pattern = re.compile(r'\b(?:table|figure)\s+([\w.-]+)', re.IGNORECASE)

    def remember_visual(raw_html, text, caption=""):
        searchable_text = f"{caption} {text}".strip().lower()
        if "<table" in raw_html:
            visual_history.append({"kind": "table", "html": raw_html, "text": searchable_text})
        elif "<img" in raw_html:
            visual_history.append({"kind": "figure", "html": raw_html, "text": searchable_text})

    def matching_visual(question_text):
        ref_tokens = [token.strip(" .,:;") for token in visual_ref_token_pattern.findall(question_text)]
        if ref_tokens:
            for item in reversed(visual_history):
                if any(token.lower() in item["text"] for token in ref_tokens):
                    return item["html"]
        if table_ref_pattern.search(question_text):
            for item in reversed(visual_history):
                if item["kind"] == "table":
                    return item["html"]
        if figure_ref_pattern.search(question_text):
            for item in reversed(visual_history):
                if item["kind"] == "figure":
                    return item["html"]
        return ""

    def build_question():
        id_counts[q_id] = id_counts.get(q_id, 0) + 1
        occurrence = id_counts[q_id]
        uid = q_id if occurrence == 1 else f"{q_id}#{occurrence}"
        return {
            'id': q_id, 'uid': uid, 'chapter': chapter_name,
            'body_html': buffer_html, 'options': options,
            'answer': answer.lower(), 'ref': ref,
            'top': meta_top, 'msc': meta_msc
        }

    elements = soup.find_all(['p', 'table']) 
    
    for elem in elements:
        text = elem.get_text().strip()
        raw_html = str(elem) 

        if visual_caption_pattern.match(text):
            pending_visual_caption = text

        # --- METADATA YAKALAMA (TOP/MSC) ---
        # Bunları buffer_html'e eklemeyip değişkene alacağız
        match_top = top_pattern.search(text)
        if match_top:
            meta_top = match_top.group(1)
            continue # HTML'e ekleme
        
        match_msc = msc_pattern.search(text)
        if match_msc:
            meta_msc = match_msc.group(1)
            continue # HTML'e ekleme

        if "<img" in raw_html or "<table" in raw_html:
            remember_visual(raw_html, text, pending_visual_caption)
            pending_visual_caption = ""

        match_q = q_start_pattern.match(text)
        if match_q:
            if current_q and len(options) >= 2 and answer:
                questions.append(build_question())
            
            question_active = True
            current_q = True
            q_num = match_q.group(1)
            q_text_content = match_q.group(2) 
            q_id = f"{chapter_name} - Q{q_num}"
            
            # Metadata sıfırla (yeni soru için)
            meta_top = None
            meta_msc = None
            
            q_text_html = f"<p><b>{q_text_content}</b></p>"
            
            if "<img" in raw_html:
                buffer_html = raw_html 
                attached_visual_html = raw_html
            else:
                visual_html = matching_visual(q_text_content)
                if visual_html:
                    buffer_html = visual_html + q_text_html
                    attached_visual_html = visual_html
                else:
                    buffer_html = q_text_html
                    attached_visual_html = ""

            options = {}
            answer = None
            ref = None
            continue

        match_ans = ans_pattern.search(text)
        if match_ans:
            answer = match_ans.group(1)
            question_active = False 
            match_ref = ref_pattern.search(text)
            if match_ref: ref = match_ref.group(1)
            continue
        
        if question_active: 
            match_opt = opt_pattern.match(text)
            if match_opt:
                options[match_opt.group(1).lower()] = match_opt.group(2)
                continue

        if "REF:" not in text and "ANS:" not in text:
            if question_active: 
                if raw_html != attached_visual_html:
                    buffer_html += raw_html

    if current_q and len(options) >= 2 and answer:
        questions.append(build_question())

    return questions
