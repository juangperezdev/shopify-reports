import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Usar W.Dressroom para la prueba
shop_url = os.getenv("SHOP3_URL")
token = os.getenv("SHOP3_TOKEN")

headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

# Consultar reportes disponibles
url = f"https://{shop_url}/admin/api/2025-10/reports.json"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    reports = data.get('reports', [])
    
    print(f"\n{'='*60}")
    print(f"REPORTES DISPONIBLES EN {shop_url}")
    print(f"{'='*60}\n")
    
    if reports:
        for report in reports:
            print(f"📊 {report['name']}")
            print(f"   ID: {report['id']}")
            print(f"   Categoría: {report.get('category', 'N/A')}")
            print(f"   Actualizado: {report.get('updated_at', 'N/A')}")
            print()
    else:
        print("⚠️  No se encontraron reportes pre-configurados.")
        print("Esto es normal en tiendas nuevas o sin reportes personalizados.")
else:
    print(f"❌ Error: {response.status_code}")
    print(f"Mensaje: {response.text}")
