import requests, os, dotenv, json

dotenv.load_dotenv()

ws_key = os.environ.get('ws_key')
ws_app = os.environ.get('ws_app')



def enviar_mensaje_whatsapp(numero_telefono:str, mensaje:str, id_aplicacion=ws_app, token_acceso=ws_key):
    
    url = f"https://graph.facebook.com/v22.0/{id_aplicacion}/messages"
    headers = {
        "Authorization": f"Bearer {token_acceso}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero_telefono,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": mensaje
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Lanza un error para códigos de estado HTTP 4xx/5xx
        print(f"Mensaje enviado exitosamente.\n{response.json()}")
        
        return response.status_code

    except requests.exceptions.HTTPError as http_err:
        print(f"Error HTTP: {http_err}")
        print(f"Respuesta del servidor: {response.text}")
    except requests.exceptions.RequestException as err:
        print(f"Ocurrió un error al realizar la petición: {err}")
    
    return None
