# https://github.com/AirdropFamilyIDN-V2-0/nodepay
import asyncio
import aiohttp
import time
import uuid
from fake_useragent import UserAgent
import re
from datetime import datetime, timezone, timedelta
import requests
from dateutil import parser
from colorama import init, Fore, Style
import itertools
import sys
import random
import concurrent.futures
init(autoreset=True)

DOMAIN_API_ENDPOINTS = {
    "SESSION": [
        #"http://18.136.143.169/api/auth/session",
        "https://api.nodepay.ai/api/auth/session"
        #"https://nodepay.org/api/auth/session"
    ],
    "PING": [
    #    "https://nw.nodepay.org/api/network/ping",
       "http://52.77.10.116/api/network/ping",
    #    "http://54.255.192.166/api/network/ping",
    #    "http://18.136.143.169/api/network/ping",
        "http://nodepaypantek.dayon.me/api/network/ping",
        "http://13.215.134.222/api/network/ping"
    #    "http://52.74.35.173/api/network/ping",
    #    "http://18.142.214.13/api/network/ping",
    #    "http://18.142.29.174/api/network/ping",
    #    "http://52.74.31.107/api/network/ping"
    ]
}
print(f"{Fore.CYAN}[+]====================[+]")
print(f"{Fore.CYAN}[+]NODEPAY PROXY SCRIPT[+]")
print(f"{Fore.CYAN}[+]====================[+]")


PING_INTERVAL = 1
RETRIES = 60

# OLD Domain API
# PING API: https://nodewars.nodepay.ai / https://nw.nodepay.ai | https://nw2.nodepay.ai | IP: 54.255.192.166
# SESSION API: https://api.nodepay.ai | IP: 18.136.143.169, 52.77.170.182

# NEW HOST DOMAIN
#    "SESSION": "https://api.nodepay.org/api/auth/session",
#    "PING": "https://nw.nodepay.org/api/network/ping"

# Testing | Found nodepay real ip address :P | Cloudflare host bypassed!


CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NONE_CONNECTION": 3
}

status_connect = CONNECTION_STATES["NONE_CONNECTION"]
browser_id = None
account_info = {}
last_ping_time = {}

def uuidv4():
    return str(uuid.uuid4())

def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("Invalid response")
    return resp

async def render_profile_info(proxy, token, token_sr_no):
    global browser_id, account_info
    try:
        np_session_info = load_session_info(proxy)

        if not np_session_info:
            browser_id = uuidv4()

            session_url = random.choice(DOMAIN_API_ENDPOINTS["SESSION"])
            response = await call_api(session_url, {}, proxy, token)
            valid_resp(response)
            account_info = response["data"]
            if account_info.get("uid"):
                save_session_info(proxy, account_info)
                print(
                    f"{get_internet_time()}| Nodepay | -  {Fore.GREEN}Successfully authenticated. Token Sr. No: {token_sr_no}"
                )
                await start_ping(proxy, token, session_url, token_sr_no)
            else:
                handle_logout(proxy)
        else:
            account_info = np_session_info
            print(
                f"{get_internet_time()}| Nodepay | -  {Fore.GREEN}Session loaded. Token Sr. No: {token_sr_no}"
            )
            await start_ping(proxy, token, None, token_sr_no)
    except Exception as e:
        error_message = str(e)
        if any(phrase in error_message for phrase in [
            "sent 1011 (internal error) keepalive ping timeout; no close frame received",
            "500 Internal Server Error"
        ]):
            remove_proxy_from_list(proxy)
            return None
        else:
            print(
                f"{get_internet_time()}{Fore.RED}| Nodepay | -  Error during profile rendering. Token Sr. No: {token_sr_no}"
            )
            return proxy
     
async def call_api(url, data, proxy, token):
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": UserAgent().random,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://app.nodepay.ai",
        }
        try:
            async with session.post(url, json=data, headers=headers, proxy=proxy, timeout=60) as response:
                response.raise_for_status()
                return valid_resp(await response.json())
        except aiohttp.ClientError as e:
            print(f"{get_internet_time()}{Fore.RED}| Nodepay | -  Client error during API call to {url}: {str(e)}")
        except asyncio.TimeoutError:
            print(f"{get_internet_time()}{Fore.RED}| Nodepay | -  Timeout during API call to {url}")
        except Exception as e:
            print(f"{get_internet_time()}{Fore.RED}| Nodepay | -  Failed API call to {url}: {str(e)}")
            raise ValueError(f"Failed API call to {url}")

async def start_ping(proxy, token, session_url, token_sr_no):
    try:
        while True:
            await ping(proxy, token, session_url, token_sr_no)
            await asyncio.sleep(PING_INTERVAL)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        pass

async def ping(proxy, token, session_url, token_sr_no):
    global last_ping_time, RETRIES, status_connect
    last_ping_time[proxy] = time.time()

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,
            "timestamp": int(time.time())
        }

        ping_url = random.choice(DOMAIN_API_ENDPOINTS["PING"])
        response = await call_api(ping_url, data, proxy, token)

        if response["code"] == 0:
            ip_address = re.search(r'(?<=@)[^:]+', proxy)
            if ip_address:
                # Update log to include Token Sr. No
                print(
                    f"{get_internet_time()}| Nodepay | -  {Fore.GREEN}Ping: {response.get('msg')}, "
                    f"Skor IP: {response['data'].get('ip_score')}, Proxy IP: {ip_address.group()}, Token Sr. No: {token_sr_no}, Ping URL: {ping_url}"
                )
            RETRIES = 0
            status_connect = CONNECTION_STATES["CONNECTED"]
        else:
            handle_ping_fail(proxy, response, token_sr_no)
    except asyncio.TimeoutError:
        print(f"{get_internet_time()}{Fore.RED}| Nodepay | -  Timeout during API call to {ping_url}, Token Sr. No: {token_sr_no}")
    except Exception as e:
        handle_ping_fail(proxy, None, token_sr_no)

def handle_ping_fail(proxy, response, token_sr_no):
    global RETRIES, status_connect
    RETRIES += 1
    if response and response.get("code") == 403:
        handle_logout(proxy)
    else:
        ip_address = re.search(r'(?<=@)[^:]+', proxy)
        if ip_address:
            print(
                f"{get_internet_time()}{Fore.RED}| Nodepay | -  Ping failed for proxy. Proxy IP: {ip_address.group()}, Token Sr. No: {token_sr_no}"
            )
        else:
            print(f"{get_internet_time()}{Fore.RED}| Nodepay | -  Ping failed for proxy, Token Sr. No: {token_sr_no}")
        remove_proxy_from_list(proxy)
        status_connect = CONNECTION_STATES["DISCONNECTED"]


def handle_logout(proxy):
    global status_connect, account_info
    status_connect = CONNECTION_STATES["NONE_CONNECTION"]
    account_info = {}
    save_status(proxy, None)

def load_proxies(proxy_file):
    try:
        with open(proxy_file, 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        raise SystemExit("Exiting due to failure in loading proxies")

def save_status(proxy, status):
    pass

def save_session_info(proxy, data):
    data_to_save = {
        "uid": data.get("uid"),
        "browser_id": browser_id
    }
    pass

def load_session_info(proxy):
    return {}

def is_valid_proxy(proxy):
    return True

def remove_proxy_from_list(proxy):
    pass

def get_internet_time():
    try:
        response = requests.get('http://worldtimeapi.org/api/timezone/Asia/Jakarta')
        response.raise_for_status()
        current_time = response.json()['datetime']
        return parser.isoparse(current_time).astimezone(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        return datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M:%S %Z')

def loading_animation():
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if not loading:
            break
        sys.stdout.write(f'\r{Fore.YELLOW}Proses... {c}')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\r')


def process_token_with_proxies(token, proxies, token_sr_no):
    """Function to process a token with its assigned proxies."""
    asyncio.run(run_tasks_for_token(token, proxies, token_sr_no))

async def run_tasks_for_token(token, proxies, token_sr_no):
    """Run async tasks for a token and its proxies."""
    tasks = []
    for proxy in proxies:
        if is_valid_proxy(proxy):
            tasks.append(render_profile_info(proxy, token, token_sr_no))
    await asyncio.gather(*tasks)


def allocate_proxies_to_tokens(tokens, all_proxies, proxies_per_token):
    """Allocate proxies to tokens, ensuring each token gets proxies and the last token gets leftovers."""
    token_proxy_map = {}
    total_tokens = len(tokens)
    total_proxies = len(all_proxies)

    for i, token in enumerate(tokens):
        start_index = i * proxies_per_token
        end_index = start_index + proxies_per_token

        # If running out of proxies, assign leftovers to the last token
        if start_index >= total_proxies:
            token_proxy_map[token] = []  # No proxies left for this token
        elif i == total_tokens - 1:  # Last token gets remaining proxies
            token_proxy_map[token] = all_proxies[start_index:]
        else:  # Normal case
            token_proxy_map[token] = all_proxies[start_index:end_index]

    return token_proxy_map


def main():
    # Settings
    proxies_per_token = 3  # Number of proxies per token
    max_threads = 39  # Set the number of threads to run simultaneously

    # Load proxies and tokens
    all_proxies = load_proxies('local_proxies.txt')
    try:
        with open('tokens.txt', 'r') as token_file:
            tokens = token_file.read().splitlines()
    except FileNotFoundError:
        print(f"{get_internet_time()} - {Fore.RED}File tokens.txt not found.")
        exit()

    if not tokens:
        print(f"{get_internet_time()} - {Fore.RED}No tokens found. Exiting program.")
        exit()

    if len(all_proxies) < len(tokens) * proxies_per_token:
        print(f"{get_internet_time()} - {Fore.YELLOW}Not enough proxies to allocate {proxies_per_token} per token. Proceeding with available proxies.")


    # Allocate proxies to tokens
    token_proxy_map = allocate_proxies_to_tokens(tokens, all_proxies, proxies_per_token)

    # Run threads
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        futures = [
            executor.submit(process_token_with_proxies, token, proxies, idx + 1)
            for idx, (token, proxies) in enumerate(token_proxy_map.items())
        ]

        # Wait for all threads to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Retrieve exceptions if any occurred
            except Exception as e:
                print(f"{get_internet_time()} - {Fore.RED}Error occurred in a thread: {e}")

if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print(f"{get_internet_time()} - {Fore.YELLOW}Program terminated by user.")
