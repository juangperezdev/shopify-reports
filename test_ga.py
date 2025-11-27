"""
Script de prueba para Google Analytics API
Ejecuta esto después de completar la configuración para verificar que funciona
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )
    from google.oauth2 import service_account
except ImportError:
    print("❌ Error: Librería no instalada")
    print("Ejecuta: pip install google-analytics-data")
    exit(1)

load_dotenv()

def test_ga_connection():
    """Prueba la conexión con Google Analytics"""
    
    # Cargar credenciales
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google-credentials.json")
    
    if not os.path.exists(credentials_path):
        print(f"❌ Error: No se encuentra el archivo {credentials_path}")
        print("Descarga las credenciales de Google Cloud y guárdalas como google-credentials.json")
        return
    
    # Property ID de prueba (W.Dressroom)
    property_id = os.getenv("SHOP3_GA_PROPERTY_ID")
    
    if not property_id:
        print("❌ Error: SHOP3_GA_PROPERTY_ID no está configurado en .env")
        return
    
    print(f"\n{'='*60}")
    print("PROBANDO CONEXIÓN CON GOOGLE ANALYTICS")
    print(f"{'='*60}\n")
    
    try:
        # Crear cliente
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        client = BetaAnalyticsDataClient(credentials=credentials)
        
        # Consultar datos de ayer
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="transactions"),
                Metric(name="totalRevenue"),
            ],
        )
        
        response = client.run_report(request)
        
        # Mostrar resultados
        if response.row_count > 0:
            row = response.rows[0]
            sessions = int(row.metric_values[0].value)
            transactions = int(row.metric_values[1].value)
            revenue = float(row.metric_values[2].value)
            conversion_rate = (transactions / sessions * 100) if sessions > 0 else 0
            
            print(f"✅ Conexión exitosa!")
            print(f"\nDatos de {yesterday}:")
            print(f"  📊 Sessions: {sessions}")
            print(f"  🛒 Transactions: {transactions}")
            print(f"  💰 Revenue: ${revenue:.2f}")
            print(f"  📈 Conversion Rate: {conversion_rate:.2f}%")
        else:
            print("⚠️  Conexión exitosa pero no hay datos para ayer")
            print("Esto puede ser normal si la tienda no tuvo tráfico")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nVerifica:")
        print("1. El archivo de credenciales es correcto")
        print("2. El Property ID es correcto")
        print("3. La cuenta de servicio tiene acceso a la propiedad de GA")

if __name__ == "__main__":
    test_ga_connection()
