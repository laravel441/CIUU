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

def obtener_datos_claro():
    """Función auxiliar para obtener los datos de la API de Claro sin depender del objeto Request"""
    # 1. Obtenemos el token
    url_auth = "https://apim-calidad.claro.com.co/MsCommunicatAuthToken/User/authenticate"
    datos_auth = {
        "client_id": "usaccoinfo",
        "client_secret": "757fb7ee-55cc-4311-9b11-e97616d24689",
        "grant_type": "client_credentials"
    }
    
    try:
        # Intentamos primero con data= (form-urlencoded) que es el estándar OAuth2
        respuesta_auth = requests.post(url_auth, data=datos_auth, verify=False, timeout=10)
        
        # Si falla con 4xx o 5xx, intentamos con json= por si la API lo requiere
        if respuesta_auth.status_code != 200:
            print(f"DEBUG: Auth con form-data falló ({respuesta_auth.status_code}). Intentando con JSON...")
            respuesta_auth_json = requests.post(url_auth, json=datos_auth, verify=False, timeout=10)
            if respuesta_auth_json.status_code == 200:
                respuesta_auth = respuesta_auth_json
        
        respuesta_auth.raise_for_status()
        
        token_data = respuesta_auth.json()
        access_token = token_data.get("access_token", token_data.get("token", None))
        
        if not access_token:
            print(f"DEBUG: Respuesta auth sin token: {token_data}")
            raise HTTPException(status_code=500, detail="No se encontró 'access_token' en la respuesta.")
            
    except requests.exceptions.RequestException as e:
         error_detail = ""
         if hasattr(e, 'response') and e.response is not None:
             error_detail = f" | Body: {e.response.text[:200]}"
         print(f"DEBUG: Error en auth: {str(e)}{error_detail}")
         raise HTTPException(status_code=502, detail=f"Error al conectar con servidor de auth: {str(e)}{error_detail}")
    
    # 2. Hacemos la consulta a la API con ese token
    url_api = "https://apim-calidad.claro.com.co/APIMCusAccoInfoQuery/MS/CUS/CustomerBill/RSCusAccoInfoQuery/V1/GET/InfoQuery"
    parametros = {
        "fieldId": "31",
        "valueRelated": "",
        "fieldRelationship": ""
    }
    cabeceras = {
        "Authorization": f"Bearer {access_token}"
    }

    try:
        respuesta_api = requests.get(
            url_api, 
            params=parametros, 
            headers=cabeceras, 
            verify=False 
        )
        respuesta_api.raise_for_status()
        
        return respuesta_api.json()

    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Error en consulta API: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Error al consultar la API: {str(e)}")


@app.get("/api/data")
def get_api_data():
    """Endpoint HTTP para el frontend"""
    return obtener_datos_claro()


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

