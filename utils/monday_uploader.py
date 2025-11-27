import requests
import os
import json

def upload_to_monday(pdf_path, item_name):
    """
    Sube el reporte PDF a Monday.com.
    
    Args:
        pdf_path (str): Ruta al archivo PDF.
        item_name (str): Nombre del item a crear (ej: "Reporte 2025-11-27").
    """
    api_key = os.getenv("MONDAY_API_TOKEN")
    board_id = os.getenv("MONDAY_BOARD_ID")
    
    if not all([api_key, board_id]):
        print("⚠️  Credenciales de Monday.com no configuradas. Saltando subida.")
        return False

    url = "https://api.monday.com/v2"
    headers = {"Authorization": api_key}

    # 1. Crear un nuevo item
    query_create = """
    mutation ($board_id: ID!, $item_name: String!) {
        create_item (board_id: $board_id, item_name: $item_name) {
            id
        }
    }
    """
    vars_create = {"board_id": int(board_id), "item_name": item_name}
    
    try:
        response = requests.post(url, json={"query": query_create, "variables": vars_create}, headers=headers)
        response_json = response.json()
        
        if "errors" in response_json:
            print(f"❌ Error creando item en Monday: {response_json['errors']}")
            return False
            
        item_id = response_json['data']['create_item']['id']
        print(f"✅ Item creado en Monday (ID: {item_id})")
        
        # 2. Subir archivo al item
        # Nota: La subida de archivos en Monday usa un endpoint diferente y multipart/form-data
        file_url = "https://api.monday.com/v2/file"
        
        with open(pdf_path, 'rb') as f:
            files = {'query': (None, f'mutation ($item_id: ID!, $file: File!) {{ add_file_to_column (item_id: $item_id, column_id: "files", file: $file) {{ id }} }}'),
                     'variables': (None, json.dumps({"item_id": int(item_id)})),
                     'map': (None, json.dumps({"0": ["variables.file"]})),
                     '0': (os.path.basename(pdf_path), f, 'application/pdf')}
            
            # Nota: Requests maneja el boundary automáticamente si no setteamos Content-Type
            headers_file = {"Authorization": api_key} 
            
            response_file = requests.post(file_url, files=files, headers=headers_file)
            
            if response_file.status_code == 200 and "data" in response_file.json():
                print(f"✅ Archivo subido exitosamente a Monday!")
                return True
            else:
                print(f"❌ Error subiendo archivo a Monday: {response_file.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error en integración con Monday: {e}")
        return False
