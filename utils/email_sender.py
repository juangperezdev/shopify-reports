import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

def send_email_report(pdf_path, recipients, subject="Shopify Daily Report"):
    """
    Envía el reporte PDF por correo electrónico.
    
    Args:
        pdf_path (str): Ruta al archivo PDF.
        recipients (list): Lista de correos destinatarios.
        subject (str): Asunto del correo.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not all([smtp_user, smtp_password]):
        print("⚠️  Credenciales SMTP no configuradas. Saltando envío de correo.")
        return False

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject

    body = "Adjunto encontrarás el reporte diario de ventas de Shopify."
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(attach)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {pdf_path}")
        return False

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Correo enviado a: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        return False
