import requests

# ==========================================
# PASO 1: OBTENER EL TOKEN OAUTH 2.0
# ==========================================
url_auth = "https://apim-calidad.claro.com.co/MsCommunicatAuthToken/User/authenticate"

# Credenciales OAuth
datos_auth = {
    "client_id": "usaccoinfo",
    "client_secret": "757fb7ee-55cc-4311-9b11-e97616d24689",
    "grant_type": "client_credentials" # Normalmente en este flujo de API a API se usa client_credentials
}

print("Obteniendo token de autenticación...")

try:
    # Normalmente las peticiones de token OAuth se envían como form-data (data=) y no como JSON puro.
    # Si la API falla aquí, podríamos intentar con json=datos_auth
    respuesta_auth = requests.post(url_auth, data=datos_auth, verify=False)
    respuesta_auth.raise_for_status()
    
    # Extraemos el access_token de la respuesta JSON
    token_data = respuesta_auth.json()
    # Dependiendo de la API, el campo podría llamarse distinto, lo más común es 'access_token' o 'token'
    access_token = token_data.get("access_token", token_data.get("token", None))
    
    if not access_token:
        print("Autenticación exitosa, pero no se encontró 'access_token' en la respuesta.")
        print("Respuesta del servidor:", token_data)
        exit(1)
        
    print("Token obtenido exitosamente.\n")

except requests.exceptions.RequestException as e:
    print(f"Error al intentar obtener el token: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print("Detalle:", e.response.text)
    exit(1)

# ==========================================
# PASO 2: REALIZAR LA CONSULTA A LA API
# ==========================================
url_api = "https://apim-calidad.claro.com.co/APIMCusAccoInfoQuery/MS/CUS/CustomerBill/RSCusAccoInfoQuery/V1/GET/InfoQuery"

parametros = {
    "fieldId": "31",
    "valueRelated": "",
    "fieldRelationship": ""
}

# Usamos el token recién obtenido
cabeceras = {
    "Authorization": f"Bearer {access_token}"
    # Nota: He quitado la Cookie fija por ahora. Normalmente con OAuth 2.0 el Token Bearer es suficiente.
    # Si la API rechaza la petición sin la Cookie, avísame y la volvemos a poner.
}

print("Realizando consulta a la API con el nuevo token...")

try:
    respuesta_api = requests.get(
        url_api, 
        params=parametros, 
        headers=cabeceras, 
        verify=False 
    )
    
    respuesta_api.raise_for_status()
    
    datos_api = respuesta_api.json()
    print("¡Consulta a la API exitosa!\n")
    print(datos_api)

except requests.exceptions.HTTPError as err_http:
    print(f"Error del servidor HTTP en la API: {err_http}")
    print("Detalle:", respuesta_api.text)
except requests.exceptions.RequestException as e:
    print(f"Error de conexión con la API: {e}")
