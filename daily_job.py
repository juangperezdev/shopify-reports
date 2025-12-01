"""
Script de ejecución diaria para automatización.
Este script está diseñado para ser ejecutado por un Cron Job (ej: Render Cron).

Flujo:
1. Genera el reporte de ventas para el día de ayer.
2. Envía el PDF por correo electrónico (si está configurado).
3. Sube el PDF a Monday.com (si está configurado).
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar funciones del proyecto
from main import generate_report_for_date

def run_daily_job():
    print(f"\n{'='*60}")
    print(f"🚀 INICIANDO JOB DIARIO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 1. Calcular fecha (Ayer)
    yesterday = datetime.now() - timedelta(days=1)
    target_date_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"📅 Generando reporte para: {target_date_str}")

    try:
        # 2. Generar PDF
        pdf_filename = generate_report_for_date(target_date_str)
        
        if not pdf_filename or not os.path.exists(pdf_filename):
            print("❌ Error: No se generó el archivo PDF.")
            sys.exit(1)
            
        print(f"✅ PDF generado exitosamente: {pdf_filename}")
        
        # 3. Enviar por Email (si está configurado)
        recipients_str = os.getenv("EMAIL_RECIPIENTS", "")
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        if recipients_str and smtp_user and smtp_password:
            try:
                from utils.email_sender import send_email_report
                recipients = [r.strip() for r in recipients_str.split(",")]
                print(f"\n📧 Enviando correo a {len(recipients)} destinatarios...")
                send_email_report(
                    pdf_filename, 
                    recipients, 
                    subject=f"Shopify Daily Report - {target_date_str}"
                )
            except Exception as e:
                print(f"⚠️  Error enviando email: {e}")
        else:
            print("\n⚠️  Credenciales de email no configuradas. Saltando envío de correo.")
            print("    Configura: EMAIL_RECIPIENTS, SMTP_USER, SMTP_PASSWORD en .env")

        # 4. Subir a Monday.com (si está configurado)
        monday_token = os.getenv("MONDAY_API_TOKEN", "")
        monday_board = os.getenv("MONDAY_BOARD_ID", "")
        
        if monday_token and monday_board:
            try:
                from utils.monday_uploader import upload_to_monday
                print(f"\n📋 Subiendo a Monday.com...")
                item_name = f"Reporte Ventas {target_date_str}"
                upload_to_monday(pdf_filename, item_name)
            except Exception as e:
                print(f"⚠️  Error subiendo a Monday: {e}")
        else:
            print("\n⚠️  Credenciales de Monday.com no configuradas. Saltando subida.")
            print("    Configura: MONDAY_API_TOKEN, MONDAY_BOARD_ID en .env")

        print(f"\n{'='*60}")
        print("🏁 JOB DIARIO COMPLETADO EXITOSAMENTE")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR en daily_job: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_daily_job()
