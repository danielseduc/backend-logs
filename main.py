from fastapi import FastAPI, Request
import logging
from datetime import datetime
from user_agents import parse
import requests

# Configuração do logger
logging.basicConfig(
    filename='access_logs.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI()

def get_public_ip():
    try:
        response = requests.get('https://httpbin.org/ip')
        return response.json().get('origin')
    except requests.RequestException:
        return None

def get_geolocation(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        return response.json()
    except requests.RequestException:
        return None

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()

    # Coleta informações do acesso
    timestamp = start_time.strftime('%Y-%m-%d %H:%M:%S')
    method = request.method
    url = str(request.url)
    headers = dict(request.headers)
    user_agent = headers.get('user-agent', 'Unknown')
    accept_language = headers.get('accept-language', 'Unknown')
    referer = headers.get('referer', 'None')
    origin = headers.get('origin', 'None')

    x_forwarded_for = headers.get('x-forwarded-for')
    if x_forwarded_for:
        client_host = x_forwarded_for.split(',')[0]
    else:
        client_host = request.client.host

    if client_host == "127.0.0.1" or client_host.startswith("192.168"):
        client_host = get_public_ip()

    geolocation = get_geolocation(client_host)
    if geolocation:
        country = geolocation.get('country', 'Unknown')
        city = geolocation.get('city', 'Unknown')
        loc = geolocation.get('loc', 'Unknown').split(',')
        latitude = loc[0] if len(loc) > 0 else 'Unknown'
        longitude = loc[1] if len(loc) > 1 else 'Unknown'
    else:
        country = city = latitude = longitude = 'Unknown'

    user_agent_parsed = parse(user_agent)
    device = f"{user_agent_parsed.device.family} ({user_agent_parsed.device.brand} {user_agent_parsed.device.model})"
    os = f"{user_agent_parsed.os.family} {user_agent_parsed.os.version_string}"
    browser = f"{user_agent_parsed.browser.family} {user_agent_parsed.browser.version_string}"

    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()

    logging.info(
        f"Timestamp: {timestamp}, "
        f"Client IP: {client_host}, "
        f"Method: {method}, "
        f"URL: {url}, "
        f"User-Agent: {user_agent}, "
        f"Device: {device}, "
        f"OS: {os}, "
        f"Browser: {browser}, "
        f"Country: {country}, "
        f"City: {city}, "
        f"Latitude: {latitude}, "
        f"Longitude: {longitude}, "
        f"Accept-Language: {accept_language}, "
        f"Referer: {referer}, "
        f"Origin: {origin}, "
        f"Processing Time: {process_time:.3f}s"
    )

    return response

@app.get("/logs")
async def get_logs():
    logs = []
    with open('access_logs.log', 'r') as file:
        for line in file:
            log_parts = line.strip().split(' - ', 1)
            if len(log_parts) == 2:
                timestamp, message = log_parts
                log_entry = {
                    "timestamp": timestamp,
                    "message": message
                }
                logs.append(log_entry)
    return logs
