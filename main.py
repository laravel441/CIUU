from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from twilio.twiml.messaging_response import MessagingResponse
import requests
import os
import urllib3

# Desactivar advertencias de SSL inseguro (InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


app = FastAPI()

# Montemos la carpeta 'static' en la ruta '/static'
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return FileResponse("static/index.html")

def obtener_datos_respaldo():
    """Carga los datos desde el archivo cache local como respaldo."""
    cache_file = "data/api_cache.json"
    if os.path.exists(cache_file):
        print(f"DEBUG: Cargando datos de respaldo desde {cache_file}")
        try:
            import json
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data["source"] = "cache"
                return data
        except Exception as e_cache:
            print(f"DEBUG: Error cargando cache: {e_cache}")
    return None

def obtener_datos_claro():
    """Función auxiliar para obtener los datos de la API de Claro sin depender del objeto Request"""
    # 1. Obtenemos el token
    url_auth = "https://apim-calidad.claro.com.co/MsCommunicatAuthToken/User/authenticate"
    datos_auth = {
        "client_id": "usaccoinfo",
        "client_secret": "757fb7ee-55cc-4311-9b11-e97616d24689",
        "grant_type": "client_credentials"
    }
    
    headers_auth = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9"
    }

    # Configuración de Certificados Cliente (mTLS)
    cert_path = os.environ.get("CERT_PATH")
    key_path = os.environ.get("KEY_PATH")
    
    cliente_cert = None
    if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
        cliente_cert = (cert_path, key_path)
        print(f"DEBUG: Usando certificado cliente mTLS: {cert_path}")

    try:
        # 1. Intentamos Autenticación
        respuesta_auth = requests.post(url_auth, data=datos_auth, headers=headers_auth, cert=cliente_cert, verify=False, timeout=10)
        
        if respuesta_auth.status_code != 200:
            print(f"DEBUG: Auth con form-data falló ({respuesta_auth.status_code}). Intentando con JSON...")
            respuesta_auth_json = requests.post(url_auth, json=datos_auth, headers=headers_auth, cert=cliente_cert, verify=False, timeout=10)
            if respuesta_auth_json.status_code == 200:
                respuesta_auth = respuesta_auth_json
        
        respuesta_auth.raise_for_status()
        
        token_data = respuesta_auth.json()
        access_token = token_data.get("access_token", token_data.get("token", None))
        
        if not access_token:
            raise Exception("No se encontró token en respuesta")

        # 2. Hacemos la consulta a la API con ese token
        url_api = "https://apim-calidad.claro.com.co/APIMCusAccoInfoQuery/MS/CUS/CustomerBill/RSCusAccoInfoQuery/V1/GET/InfoQuery"
        parametros = {"fieldId": "31", "valueRelated": "", "fieldRelationship": ""}
        cabeceras = {"Authorization": f"Bearer {access_token}"}

        respuesta_api = requests.get(url_api, params=parametros, headers=cabeceras, cert=cliente_cert, verify=False, timeout=10)
        respuesta_api.raise_for_status()
        
        return respuesta_api.json()

    except Exception as e:
        print(f"DEBUG: Fallo en flujo API ({type(e).__name__}): {str(e)}")
        
        # Fallback a datos locales
        respaldo = obtener_datos_respaldo()
        if respaldo:
            return respaldo
        
        # Si ni siquiera hay respaldo, lanzamos error
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             error_msg += f" | Body: {e.response.text[:100]}"
             
        raise HTTPException(status_code=502, detail=f"API falló y no hay respaldo: {error_msg}")


@app.get("/api/data")
def get_api_data():
    """Endpoint HTTP para el frontend con señalización de origen"""
    try:
        data = obtener_datos_claro()
        # Si la respuesta ya tiene 'source', la respetamos (viene del fallback)
        if isinstance(data, dict) and "source" not in data:
            data["source"] = "live"
        return data
    except Exception as e:
        # Esto no debería ocurrir mucho ahora con el fallback interno, 
        # pero por si acaso devolvemos error estructurado
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/client/{nit}")
def get_client_by_nit(nit: str):
    """Consulta de cliente por NIT con Modo Demo para Render"""
    
    # 1. Verificar si estamos en modo Demo (Render sin certificados)
    cert_path = os.environ.get("CERT_PATH")
    if os.environ.get("PORT") and not (cert_path and os.path.exists(cert_path)):
        # ESCENARIOS DE DEMO
        print(f"DEBUG: Modo Demo NIT activado para: {nit}")
        
        # Simulación de NIT encontrado
        if "9595" in nit or "1098702048-3" in nit:
             return {
                "source": "demo_found",
                "status": "success",
                "data": {
                    "nit": nit,
                    "nombre": "CLIENTE FIDELIZADO CLARO S.A.S",
                    "estado": "Activo",
                    "segmento": "Corporativo / VIP",
                    "direccion": "Avenida 68 # 45-12, Bogotá",
                    "fecha_vinculacion": "2018-11-22"
                }
            }
        
        # Simulación de NIT con error de API
        if "error" in nit.lower() or "500" in nit:
             return {
                "source": "demo_error",
                "status": "error",
                "message": "Error interno del servidor APIM (Simulado)",
                "detail": "Error en el conector backend de Claro"
            }
            
        # Simulación de NIT no encontrado
        return {
            "source": "demo_not_found",
            "status": "not_found",
            "message": f"No se encontró cliente con el NIT {nit}"
        }

    # 2. Lógica real (para local o Render con certificados)
    try:
        # Reutilizamos el flujo de auth
        datos_auth = {
            "client_id": "usaccoinfo",
            "client_secret": "757fb7ee-55cc-4311-9b11-e97616d24689",
            "grant_type": "client_credentials"
        }
        url_auth = "https://apim-calidad.claro.com.co/MsCommunicatAuthToken/User/authenticate"
        
        # Usamos los certificados si existen
        key_path = os.environ.get("KEY_PATH")
        cliente_cert = (cert_path, key_path) if cert_path and key_path and os.path.exists(cert_path) else None
        
        # Token
        r_auth = requests.post(url_auth, data=datos_auth, verify=False, cert=cliente_cert, timeout=10)
        r_auth.raise_for_status()
        token = r_auth.json().get("access_token", r_auth.json().get("token"))
        
        # Consulta Cliente
        url_api = f"https://apim-calidad.claro.com.co/APIMCusAccoInfoQuery/MS/CUS/CustomerBill/RSCusAccoInfoQuery/V1/GET/QueryClient"
        params = {"nitClient": nit}
        headers = {"Authorization": f"Bearer {token}"}
        
        r_client = requests.get(url_api, params=params, headers=headers, verify=False, cert=cliente_cert, timeout=10)
        r_client.raise_for_status()
        
        res = r_client.json()
        
        # Normalización: Si el mensaje indica éxito, aseguramos status='success'
        message = res.get("message", "").lower()
        if "exitosa" in message or "exito" in message or "success" in message:
            res["status"] = "success"
            
        # Si no hay status pero hay datos de cliente, asumimos éxito
        if "status" not in res and ("data" in res or "client" in res or "nit" in res):
            res["status"] = "success"

        res["source"] = "live"
        return res

    except Exception as e:
        print(f"DEBUG: Error consulta NIT real: {e}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             error_msg = e.response.text
             
        return {
            "source": "error",
            "status": "error",
            "message": "Error al conectar con la API real",
            "detail": error_msg
        }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Webhook que recibe los mensajes entrantes de WhatsApp vía Twilio.
    Twilio envía los datos como form-urlencoded.
    """
    # Parseamos los datos enviados por Twilio
    form_data = await request.form()
    
    # El mensaje del usuario viene en el campo 'Body'
    incoming_msg = form_data.get('Body', '').strip()
    sender = form_data.get('From', '')
    
    print(f"Mensaje de WhatsApp recibido de {sender}: '{incoming_msg}'")
    
    # Obtenemos los datos de la API de Claro
    try:
        api_data = obtener_datos_claro()
        
        # Extraemos la lista de actividades igual que en el frontend
        actividades = []
        if api_data and api_data.get("data") and isinstance(api_data["data"].get("information"), list):
            actividades = api_data["data"]["information"]
        elif isinstance(api_data, list):
             actividades = api_data
        else:
            # Fallback en caso de que la estructura varíe 
            for key in api_data:
                if isinstance(api_data[key], list):
                    actividades = api_data[key]
                    break
        
        # Buscamos el código enviado por el usuario
        actividad_encontrada = next((item for item in actividades if item.get('dataField') == incoming_msg), None)
        
        # Preparamos la respuesta para WhatsApp
        if actividad_encontrada:
            descripcion = actividad_encontrada.get('descriptionField', '(Sin descripción)')
            respuesta_texto = f"✅ *Actividad Encontrada*\n\n*Código:* {incoming_msg}\n*Descripción:* {descripcion}"
        else:
             respuesta_texto = f"❌ Lo siento, no encontré ninguna actividad económica con el código *{incoming_msg}*. Por favor, verifica el código e intenta nuevamente."

    except Exception as e:
        print(f"Error procesando webhook de WhatsApp: {e}")
        respuesta_texto = "⚠️ Lo siento, en este momento tenemos problemas para consultar la base de datos de actividades. Por favor intenta más tarde."

    # Twilio espera la respuesta en formato TwiML (XML)
    resp = MessagingResponse()
    resp.message(respuesta_texto)
    
    return Response(content=str(resp), media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    # Render proporciona el puerto en la variable de entorno 'PORT'
    port = int(os.environ.get("PORT", 8000))
    # Corremos uvicorn manualmente para facilitar pruebas en algunos entornos
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False if os.environ.get("PORT") else True)

