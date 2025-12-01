import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr  # <--- BU EKSİKTİ, EKLENDİ
import os
import streamlit as st

def send_reset_code(to_email, code):
    """Kullanıcıya 6 haneli doğrulama kodunu mail atar."""
    
    # Bilgileri çek (Hem .env hem Streamlit Secrets uyumlu)
    sender_email = os.getenv("EMAIL_SENDER") or st.secrets.get("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD") or st.secrets.get("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        return False, "Mail ayarları (Secrets) yapılmamış."

    subject = "ekoTestBank - Şifre Sıfırlama Kodu"
    body = f"""
    Merhaba,
    
    Şifrenizi sıfırlamak için doğrulama kodunuz:
    
    <h2>{code}</h2>
    
    Bu kodu kimseyle paylaşmayın.
    
    Sevgiler,
    ekoTestBank Ekibi
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        # Gmail SMTP Sunucusu
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True, "Kod gönderildi"
    except Exception as e:
        return False, str(e)

def get_mail_creds():
    """Mail bilgilerini .env veya secrets'tan çeker."""
    sender = os.getenv("EMAIL_SENDER") or st.secrets.get("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD") or st.secrets.get("EMAIL_PASSWORD")
    return sender, password

def send_admin_notification(subject, message, user_info="Misafir"):
    """
    Admine (Sana) bildirim maili atar.
    Kullanıcı teşekkür ederse veya yorum yazarsa bu çalışır.
    """
    sender_email, sender_password = get_mail_creds()
    if not sender_email or not sender_password: return False

    # Kendine gönderiyorsun
    to_email = sender_email 

    msg = MIMEMultipart()
    msg['From'] = formataddr(("ekoTestBank Bildirim", sender_email))
    msg['To'] = to_email
    msg['Subject'] = f"🔔 {subject}"
    
    body = f"""
    <h3>Yeni Bildirim</h3>
    <p><strong>Kimden:</strong> {user_info}</p>
    <p><strong>Mesaj:</strong></p>
    <blockquote style="border-left: 4px solid #ccc; padding-left: 10px;">
    {message}
    </blockquote>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except:
        return False
