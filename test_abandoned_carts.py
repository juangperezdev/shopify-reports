"""
Script de prueba para verificar acceso a carritos abandonados
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Usar W.Dressroom para la prueba
shop_url = os.getenv("SHOP3_URL")
token = os.getenv("SHOP3_TOKEN")

headers = {
    "X-Shopify-Access-Token": token,
    "Content-Type": "application/json"
}

# Consultar carritos abandonados de ayer
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
today = datetime.now().strftime('%Y-%m-%d')

url = f"https://{shop_url}/admin/api/2025-10/checkouts.json"
params = {
    "created_at_min": f"{yesterday}T00:00:00-06:00",
    "created_at_max": f"{today}T00:00:00-06:00",
    "status": "open",  # Carritos abandonados
    "limit": 50
}

print(f"\n{'='*60}")
print(f"PROBANDO ACCESO A CARRITOS ABANDONADOS")
print(f"{'='*60}\n")

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    checkouts = data.get('checkouts', [])
    
    print(f"✅ Acceso exitoso!")
    print(f"\nCarritos abandonados de {yesterday}:")
    print(f"  🛒 Total: {len(checkouts)}")
    
    if checkouts:
        total_value = sum(float(c.get('total_price', 0)) for c in checkouts)
        print(f"  💰 Valor total: ${total_value:.2f}")
        print(f"\nPrimeros 3 carritos:")
        for i, cart in enumerate(checkouts[:3], 1):
            email = cart.get('email', 'Sin email')
            value = float(cart.get('total_price', 0))
            created = cart.get('created_at', '')
            print(f"    {i}. {email} - ${value:.2f} - {created}")
    else:
        print("  ⚠️  No hay carritos abandonados para ayer")
        
elif response.status_code == 403:
    print("❌ Error 403: Permiso denegado")
    print("\nNecesitas agregar el permiso 'read_checkouts' a tu Custom App:")
    print("1. Ve a Settings > Apps and sales channels > Develop apps")
    print("2. Selecciona tu app")
    print("3. Configuration > Admin API integration")
    print("4. Marca 'read_checkouts'")
    print("5. Save y reinstala la app")
else:
    print(f"❌ Error: {response.status_code}")
    print(f"Mensaje: {response.text}")
