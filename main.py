import os
import requests
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fpdf import FPDF
from collections import defaultdict

# 1. Cargar variables de entorno
load_dotenv()

# Configuración de las tiendas basada en el .env
SHOPS = [
    {
        "name": os.getenv("SHOP1_NAME"),
        "url": os.getenv("SHOP1_URL"),
        "token": os.getenv("SHOP1_TOKEN")
    },
    {
        "name": os.getenv("SHOP2_NAME"),
        "url": os.getenv("SHOP2_URL"),
        "token": os.getenv("SHOP2_TOKEN")
    },
    {
        "name": os.getenv("SHOP3_NAME"),
        "url": os.getenv("SHOP3_URL"),
        "token": os.getenv("SHOP3_TOKEN")
    }
]

class ShopifyFetcher:
    def __init__(self, shop_config):
        self.shop = shop_config
        self.headers = {
            "X-Shopify-Access-Token": self.shop['token'],
            "Content-Type": "application/json"
        }
        self.base_url = f"https://{self.shop['url']}/admin/api/2025-10"
        self.graphql_url = f"{self.base_url}/graphql.json"

    def _get_rest_data(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error en {self.shop['name']} ({endpoint}): {response.status_code} - {response.text}")
            return None
            
    def get_shop_timezone(self):
        """Obtiene la zona horaria de la tienda"""
        data = self._get_rest_data("shop.json")
        if data and 'shop' in data:
            return data['shop']['iana_timezone']
        return 'UTC'
    
    def _execute_graphql(self, query):
        """Ejecuta query GraphQL para Analytics"""
        response = requests.post(self.graphql_url, json={'query': query}, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error GraphQL en {self.shop['name']}: {response.status_code} - {response.text}")
            return None

    def get_orders_for_period(self, target_date):
        """Obtiene todas las órdenes de un día específico
        target_date: datetime object
        Ajusta a la zona horaria de la tienda
        """
        try:
            import pytz
        except ImportError:
            # Fallback si no está instalado pytz, usar UTC
            print("  ⚠️  Librería 'pytz' no instalada. Usando UTC por defecto.")
            timezone_str = 'UTC'
            tz = timezone.utc
        else:
            timezone_str = self.get_shop_timezone()
            try:
                tz = pytz.timezone(timezone_str)
            except:
                tz = timezone.utc
        
        # Calcular fechas en la zona horaria de la tienda
        # Asumimos que target_date ya es la fecha correcta, solo necesitamos asignarle la zona horaria
        # Pero target_date viene sin info de hora, así que construimos el rango del día
        
        # Calcular fechas en la zona horaria de la tienda
        naive_start = datetime.combine(target_date, datetime.min.time())
        naive_end = datetime.combine(target_date, datetime.max.time())
        
        if hasattr(tz, 'localize'):
            # pytz requires localize()
            start_local = tz.localize(naive_start)
            end_local = tz.localize(naive_end)
        else:
            # Standard datetime.timezone uses replace()
            start_local = naive_start.replace(tzinfo=tz)
            end_local = naive_end.replace(tzinfo=tz)
        
        # Convertir a UTC para la API
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        
        # Formato ISO 8601
        params = {
            "created_at_min": start_utc.isoformat(),
            "created_at_max": end_utc.isoformat(),
            "status": "any",
            "limit": 250
        }
        
        print(f"  📅 Consultando {timezone_str}: {start_local.strftime('%Y-%m-%d')} (UTC: {start_utc.strftime('%H:%M')} - {end_utc.strftime('%H:%M')})")
        
        data = self._get_rest_data("orders.json", params)
        if data and 'orders' in data:
            orders_count = len(data['orders'])
            print(f"  ℹ️  Encontradas {orders_count} órdenes para {start_local.strftime('%Y-%m-%d')}")
            return data['orders']
        else:
            print(f"  ⚠️  No se encontraron órdenes para {start_local.strftime('%Y-%m-%d')}")
        return []
    
    def get_orders_for_date(self, date_obj):
        """Obtiene órdenes de una fecha específica"""
        return self.get_orders_for_period(target_date=date_obj)
    
    def get_previous_day_orders(self, date_obj):
        """Obtiene órdenes del día anterior a la fecha dada (para comparación)"""
        previous_day = date_obj - timedelta(days=1)
        return self.get_orders_for_period(target_date=previous_day)
    
    def get_analytics_by_channel(self, days_ago=1):
        """Obtiene sesiones y conversión por canal usando ShopifyQL"""
        # TEMPORALMENTE DESHABILITADO - ShopifyQL no está disponible en plan básico
        print(f"  ℹ️  Analytics por canal no disponible (requiere Shopify Plus)")
        return {}
    
    def get_overall_analytics(self, days_ago=1):
        """Obtiene métricas generales del día"""
        # TEMPORALMENTE DESHABILITADO - ShopifyQL no disponible en plan básico
        print(f"  ℹ️  Analytics generales no disponible (requiere Shopify Plus)")
        return {'sessions': 0, 'sales': 0.0, 'orders': 0, 'conversion_rate': 0.0}

    def process_daily_stats(self, orders):
        """Calcula totales basados en la lista de órdenes"""
        total_sales = 0.0
        total_orders = len(orders)
        
        hourly_counts = [0] * 24
        channels = defaultdict(lambda: {'count': 0, 'sales': 0.0})

        for order in orders:
            # Ventas (usamos total_price)
            try:
                total_sales += float(order.get('total_price', 0))
            except:
                pass

            # Hora del pedido
            created_at = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
            hour = created_at.hour
            if 0 <= hour < 24:
                hourly_counts[hour] += 1

            # Atribución mejorada: usamos referring_site para ver los canales de marketing reales
            referring_site = order.get('referring_site', '')
            source_name = order.get('source_name', '')
            
            # Determinar el canal y tipo basado en referring_site
            channel_type = 'unknown'
            if referring_site:
                # Limpiar y categorizar
                if 'google' in referring_site.lower():
                    channel = 'Google Search'
                    channel_type = 'organic' if 'search' in referring_site.lower() or '/url?' in referring_site else 'unknown'
                elif 'facebook' in referring_site.lower() or 'fb' in referring_site.lower():
                    channel = 'Facebook'
                    channel_type = 'paid'  # Facebook suele ser tráfico pago
                elif 'instagram' in referring_site.lower():
                    channel = 'Instagram'
                    channel_type = 'paid'
                elif 'tiktok' in referring_site.lower():
                    channel = 'TikTok'
                    channel_type = 'paid'
                elif 'pinterest' in referring_site.lower():
                    channel = 'Pinterest'
                    channel_type = 'organic'
                elif 'youtube' in referring_site.lower():
                    channel = 'YouTube'
                    channel_type = 'organic'
                elif 'twitter' in referring_site.lower() or 't.co' in referring_site.lower():
                    channel = 'Twitter/X'
                    channel_type = 'organic'
                else:
                    # Mostrar el dominio limpio
                    channel = referring_site.replace('https://', '').replace('http://', '').split('/')[0]
                    channel_type = 'unknown'
            else:
                # Sin referring_site = tráfico directo o app
                if source_name == 'web':
                    channel = 'Direct'
                    channel_type = 'direct'
                elif source_name in ['iphone', 'android', 'mobile_app']:
                    channel = f'App ({source_name.title()})'
                    channel_type = 'direct'
                else:
                    channel = source_name if source_name else 'Direct'
                    channel_type = 'direct'
            
            # Guardar con tipo
            if channel not in channels:
                channels[channel] = {'count': 0, 'sales': 0.0, 'type': channel_type}
            
            channels[channel]['count'] += 1
            try:
                channels[channel]['sales'] += float(order.get('total_price', 0))
            except:
                pass



        return {
            "summary": {
                "Ventas": f"${total_sales:.2f}",
                "Ordenes": total_orders,
                "Ticket Prom": f"${(total_sales/total_orders):.2f}" if total_orders > 0 else "$0.00"
            },
            "hourly_orders": hourly_counts,
            "attribution": channels
        }
    
    def compare_periods(self, current_stats, previous_stats):
        """Compara dos períodos y calcula % de cambio"""
        def calc_change(current, previous):
            if previous == 0:
                return 0 if current == 0 else 100
            return ((current - previous) / previous) * 100
        
        current_sales = float(current_stats['summary']['Ventas'].replace('$', '').replace(',', ''))
        previous_sales = float(previous_stats['summary']['Ventas'].replace('$', '').replace(',', ''))
        
        current_orders = current_stats['summary']['Ordenes']
        previous_orders = previous_stats['summary']['Ordenes']
        
        sales_change = calc_change(current_sales, previous_sales)
        orders_change = calc_change(current_orders, previous_orders)
        
        return {
            'sales_change': sales_change,
            'orders_change': orders_change
        }

def create_chart(data_points, store_name):
    """Genera y guarda el gráfico PNG de Órdenes por Hora"""
    plt.figure(figsize=(10, 3))
    hours = range(len(data_points))
    plt.bar(hours, data_points, color='#008060', alpha=0.7) # Bar chart es mejor para conteos discretos bajos
    plt.title(f"Órdenes por Hora (Ayer) - {store_name}", fontsize=10)
    plt.xlabel("Hora del día")
    plt.ylabel("Cant. Órdenes")
    plt.grid(True, axis='y', linestyle='--', alpha=0.3)
    plt.xticks(hours[::2]) # Mostrar cada 2 horas
    
    filename = f"temp_chart_{store_name.replace(' ', '_')}.png"
    plt.savefig(filename, dpi=100, bbox_inches='tight')
    plt.close()
    return filename

class PDFReport(FPDF):
    def __init__(self, report_date=None):
        super().__init__()
        self.report_date = report_date
        
    def header(self):
        if self.report_date:
            # Título principal: Fecha del reporte
            self.set_font('Arial', 'B', 16)
            formatted_date = self.report_date.strftime('%B %d, %Y')
            self.cell(0, 10, formatted_date, 0, 1, 'C')
            
            # Subtítulo: Fecha de generación
            self.set_font('Arial', '', 9)
            self.set_text_color(128, 128, 128)
            gen_date = datetime.now().strftime('%B %d, %Y at %H:%M')
            self.cell(0, 5, f'Generated on: {gen_date}', 0, 1, 'C')
            self.set_text_color(0, 0, 0)
            self.ln(5)

    def add_store_section(self, store_data):
        # Título Tienda
        self.set_fill_color(240, 240, 240)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 12, f" {store_data['name']}", 0, 1, 'L', 1)
        self.ln(2)
        
        # Leyenda Narrativa (estilo Shopify)
        if 'narrative' in store_data:
            self.set_font('Arial', '', 10)
            self.set_text_color(80, 80, 80)
            self.multi_cell(0, 5, store_data['narrative'])
            self.set_text_color(0, 0, 0)
            self.ln(3)

        # Métricas Clave con % de Cambio
        self.set_font('Arial', 'B', 11)
        metrics = store_data['stats']['summary']
        comparison = store_data.get('comparison', {})
        
        # Fila 1: Ventas y Órdenes
        col_w = 95
        self.set_fill_color(250, 250, 250)
        
        # Ventas
        self.cell(col_w, 10, f"Total Sales: {metrics['Ventas']}", 1, 0, 'L', 1)
        if 'sales_change' in comparison:
            change = comparison['sales_change']
            sign = '+' if change >= 0 else ''
            self.set_text_color(0, 128, 0) if change >= 0 else self.set_text_color(255, 0, 0)
            self.cell(col_w, 10, f"  {sign}{change:.1f}%", 1, 1, 'L', 1)
            self.set_text_color(0, 0, 0)
        else:
            self.cell(col_w, 10, "", 1, 1)
        
        # Órdenes  
        self.set_fill_color(250, 250, 250)
        self.cell(col_w, 10, f"Orders: {metrics['Ordenes']}", 1, 0, 'L', 1)
        if 'orders_change' in comparison:
            change = comparison['orders_change']
            sign = '+' if change >= 0 else ''
            self.set_text_color(0, 128, 0) if change >= 0 else self.set_text_color(255, 0, 0)
            self.cell(col_w, 10, f"  {sign}{change:.1f}%", 1, 1, 'L', 1)
            self.set_text_color(0, 0, 0)
        else:
            self.cell(col_w, 10, "", 1, 1)
        
        # Ticket Promedio
        self.set_fill_color(250, 250, 250)
        self.cell(col_w, 10, f"Avg Ticket: {metrics['Ticket Prom']}", 1, 0, 'L', 1)
        self.cell(col_w, 10, "", 1, 1)
        
        self.ln(5)

        # Gráfico
        if store_data['chart_file']:
            self.image(store_data['chart_file'], x=10, w=190)
            self.ln(2)

        # Tabla Atribución (Canales de Marketing)
        self.set_font('Arial', 'B', 10)
        self.cell(0, 8, "Attribution - Marketing Channels", 0, 1)
        self.ln(2)
        
        # Header Tabla (estilo Shopify con Sessions)
        self.set_fill_color(245, 245, 245)
        self.set_font('Arial', 'B', 8)
        col_w = [40, 22, 22, 22, 25, 22]  # Channel, Type, Sessions, Orders, Sales, Conv%
        headers = ["Channel", "Type", "Sessions", "Orders", "Sales", "Conv."]
        for i, h in enumerate(headers):
            self.cell(col_w[i], 7, h, 1, 0, 'C', 1)
        self.ln()

        # Filas Tabla
        self.set_font('Arial', '', 8)
        self.set_fill_color(255, 255, 255)
        attribution_data = store_data['stats']['attribution']
        
        if not attribution_data:
            self.cell(sum(col_w), 7, "Sin datos de órdenes", 1, 1, 'C')
        else:
            # Ordenar por ventas (mayor a menor)
            sorted_channels = sorted(attribution_data.items(), key=lambda x: x[1]['sales'], reverse=True)
            
            for channel_name, data in sorted_channels:
                channel_type = data.get('type', 'unknown')
                sessions = data.get('sessions', 0)
                orders = data.get('orders', data.get('count', 0))
                sales = data.get('sales', 0.0)
                conv_rate = data.get('conversion_rate', 0.0)
                
                # Alternar color de fondo
                self.set_fill_color(250, 250, 250)
                
                self.cell(col_w[0], 7, str(channel_name)[:18], 1, 0, 'L', 1)
                self.cell(col_w[1], 7, channel_type[:10], 1, 0, 'C', 1)
                self.cell(col_w[2], 7, str(sessions), 1, 0, 'C', 1)
                self.cell(col_w[3], 7, str(orders), 1, 0, 'C', 1)
                self.cell(col_w[4], 7, f"${sales:.2f}", 1, 0, 'R', 1)
                self.cell(col_w[5], 7, f"{conv_rate:.1f}%", 1, 1, 'C', 1)
        
        self.ln(10)

# --- EJECUCIÓN PRINCIPAL ---

def generate_report_for_date(target_date_str):
    """Genera el reporte para una fecha específica (YYYY-MM-DD)"""
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("Formato de fecha inválido. Use YYYY-MM-DD")
        return None

    print(f"Iniciando generación de reporte para {target_date}...")
    
    collected_data = []
    
    # 1. Obtener datos de cada tienda
    for shop_conf in SHOPS:
        if not shop_conf["token"]: continue 
        
        print(f"Procesando {shop_conf['name']}...")
        fetcher = ShopifyFetcher(shop_conf)
        
        # Obtener órdenes de DOS períodos (fecha seleccionada y día anterior)
        current_orders = fetcher.get_orders_for_date(target_date)
        previous_orders = fetcher.get_previous_day_orders(target_date)
        
        # Procesar estadísticas de órdenes
        current_stats = fetcher.process_daily_stats(current_orders)
        previous_stats = fetcher.process_daily_stats(previous_orders)
        
        # Obtener Analytics (sesiones, conversión)
        # ... (código existente de analytics) ...
        
        # Comparar períodos
        comparison = fetcher.compare_periods(current_stats, previous_stats)
        
        # Generar gráfico de órdenes
        chart_path = create_chart(current_stats['hourly_orders'], shop_conf['name'])
        
        # Generar leyenda narrativa estilo Shopify
        sales_val = current_stats['summary']['Ventas']
        orders_count = current_stats['summary']['Ordenes']
        
        sales_change = comparison['sales_change']
        orders_change = comparison['orders_change']
        
        sales_trend = "an increase" if sales_change >= 0 else "a decrease"
        orders_trend = "showing" if orders_change >= 0 else "with"
        
        narrative = (
            f"{shop_conf['name']} store generated total sales of {sales_val}, "
            f"{sales_trend} of {abs(sales_change):.0f}% compared to the previous day. "
            f"The store fulfilled {orders_count} orders, {orders_trend} "
            f"{'+' if orders_change >= 0 else ''}{orders_change:.0f}% change in order volume."
        )
        
        collected_data.append({
            "name": shop_conf['name'],
            "stats": current_stats,
            "comparison": comparison,
            "chart_file": chart_path,
            "narrative": narrative,
            "analytics": {'sessions': 0, 'conversion_rate': 0} # Placeholder
        })

    # 2. Generar PDF
    if collected_data:
        pdf = PDFReport(report_date=target_date)
        pdf.add_page()
        
        # Título eliminado a petición del usuario
        # pdf.set_font('Arial', 'B', 16)
        # pdf.cell(0, 10, f'Daily Sales Report - {target_date.strftime("%Y-%m-%d")}', 0, 1, 'C')
        # pdf.ln(10)
        
        for idx, data in enumerate(collected_data):
            # Nueva página para cada tienda (excepto la primera)
            if idx > 0:
                pdf.add_page()
                
            pdf.add_store_section(data)
            
            if os.path.exists(data['chart_file']):
                os.remove(data['chart_file'])
            
        filename = f"Reporte_Ventas_{target_date.strftime('%Y-%m-%d')}.pdf"
        pdf.output(filename)
        print(f"\n¡Éxito! Reporte generado: {filename}")
        return filename
    else:
        print("No se obtuvieron datos de ninguna tienda.")
        return None

if __name__ == "__main__":
    # Por defecto genera reporte de ayer si se ejecuta directamente
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    generate_report_for_date(yesterday)