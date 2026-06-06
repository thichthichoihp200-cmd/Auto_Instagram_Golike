import requests
import time
import random
import os
import subprocess

TOKEN_FILE = "authorized.txt"

# --- ĐỊNH NGHĨA BỘ MÀU ANSI CHO TERMUX ---
C_RESET  = "\033[0m"
C_RED    = "\033[1;31m"
C_GREEN  = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_BLUE   = "\033[1;34m"
C_CYAN   = "\033[1;36m"
C_WHITE  = "\033[1;37m"

# BỘ HEADER ĐÃ ĐƯỢC ĐỔI SANG USER-AGENT CỦA IPAD (iOS)
HEADERS_GOLIKE = {
    'authority': 'gateway.golike.net',
    'accept': 'application/json, text/plain, */*',
    't-platform': 'ios',                  # Đổi nền tảng nhận diện thành ios
    't-version': '62',
    't-device': 'iPad',                   # Đổi thiết bị nhận diện thành iPad
    't-device-id': 'uuid-' + str(random.randint(111111, 999999)),
    # User-Agent chuẩn của trình duyệt Safari trên thiết bị iPad (iOS mới nhất)
    'user-agent': 'Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1 GoLike/1.1.2',
    'content-type': 'application/json;charset=UTF-8',
    'referer': 'https://app.golike.net/',
}

def load_data(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_data(file_path, data_list):
    with open(file_path, "w", encoding="utf-8") as f:
        for item in data_list: f.write(item + "\n")

def get_authorization():
    tokens = load_data(TOKEN_FILE)
    if tokens:
        short_token = tokens[0][:15]
        print(f"{C_CYAN}[*] Token hiện tại: {short_token}... [ĐÃ ẨN RÚT GỌN]{C_RESET}")
        choice = input(f"{C_YELLOW}[?] Dùng lại (1) hay Thay mới (2): {C_RESET}")
        if choice == '1': return tokens[0]
    
    new_token = input(f"{C_CYAN}[>] Nhập Authorization mới: {C_RESET}").strip()
    if not new_token.startswith("Bearer "): new_token = "Bearer " + new_token
    save_data(TOKEN_FILE, [new_token])
    return new_token

def get_golike_accounts(token):
    headers = HEADERS_GOLIKE.copy()
    headers['authorization'] = token
    try:
        res = requests.get("https://gateway.golike.net/api/instagram-account", headers=headers, timeout=15).json()
        if res.get('status') == 200: 
            return res.get('data', [])
        else:
            print(f"\n{C_RED}[!] GoLike báo lỗi: {res.get('message')}{C_RESET}")
    except Exception as e:
        print(f"{C_RED}[-] Lỗi kết nối lấy tài khoản: {e}{C_RESET}")
    return []

def open_link_with_termux(url):
    try:
        if not url.startswith("http"):
            url = "https://" + url
        subprocess.run(f'termux-open "{url}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"{C_RED}[-] Lỗi kích hoạt termux-open: {e}{C_RESET}")

def run_job_for_account(token, ig_id, username, max_jobs):
    print(f"\n{C_BLUE}[▶️ CHẠY] Bắt đầu nhận job cho nick: {C_WHITE}[{username}]{C_RESET}")
    headers = HEADERS_GOLIKE.copy()
    headers['authorization'] = token
    count = 0
    empty_job_count = 0
    
    while count < max_jobs:
        if empty_job_count >= 3:
            print(f"\n{C_RED}🛑 [THÔNG BÁO] Nick [{username}] đã 3 lần liên tiếp không có job mới.{C_RESET}")
            print(f"{C_YELLOW}👉 Tự động thoát lượt chạy để quay về danh sách chọn nick khác...{C_RESET}")
            break
            
        url = f"https://gateway.golike.net/api/advertising/publishers/instagram/jobs?instagram_account_id={ig_id}&data=null"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            res = response.json()
            
            if res.get('status') == 200 and res.get('data'):
                empty_job_count = 0 
                job_data = res['data']
                lock_data = res.get('lock', {})
                
                ads_id = job_data.get('id')
                log_id = lock_data.get('id')
                object_id = job_data.get('object_id')
                job_type = job_data.get('type', '').lower()
                link_instagram = job_data.get('link')
                price = job_data.get('price_after_cost', 0)
                
                if job_type not in ['like', 'follow']: 
                    print(f"{C_YELLOW}⚠️ Gặp Job {job_type.upper()} -> Đang tự động Skip...{C_RESET}")
                    skip_url = "https://gateway.golike.net/api/advertising/publishers/instagram/skip-jobs"
                    skip_payload = {
                        "instagram_account_id": int(ig_id),
                        "ads_id": int(ads_id) if ads_id else 0,
                        "log_id": int(log_id) if log_id else 0,
                        "object_id": str(object_id),
                        "type": job_type
                    }
                    requests.post(skip_url, json=skip_payload, headers=headers, timeout=10)
                    time.sleep(2)
                    continue
                
                print(f"\n{C_GREEN}⚡ Nhận Job thành công: {job_type.upper()} | Thù lao: {price} xu{C_RESET}")
                print(f"{C_CYAN}👉 [ĐANG MỞ LINK] Vui lòng chọn App Instagram tương ứng trên màn hình...{C_RESET}")
                
                if link_instagram:
                    open_link_with_termux(link_instagram)
                else: 
                    continue
                
                input(f"{C_YELLOW}[ Bấm ENTER sau khi làm xong trên App để nhận tiền... ]{C_RESET}")
                
                comp_url = "https://gateway.golike.net/api/advertising/publishers/instagram/complete-jobs"
                payload = {"instagram_account_id": int(ig_id), "ads_id": int(ads_id), "log_id": int(log_id)}
                done = requests.post(comp_url, json=payload, headers=headers, timeout=10).json()
                
                if done.get('status') == 200:
                    count += 1
                    print(f"{C_GREEN}✅ Thành công: +{price} xu ({count}/{max_jobs}){C_RESET}")
                else:
                    print(f"{C_RED}❌ Thất bại: {done.get('message')}{C_RESET}")
                    
                time.sleep(random.randint(3, 6))
                
            else:
                empty_job_count += 1
                server_message = res.get('message', 'Hiện tại chưa có job mới cho nick này.')
                
                print(f"\n{C_RED}⚠️ [{username}] Lần {empty_job_count}/3 không có job!{C_RESET}")
                print(f"{C_YELLOW}💬 Thông báo GoLike: {server_message}{C_RESET}")
                print(f"{C_CYAN}⏳ Chờ 10 giây để gọi lại API hệ thống...{C_RESET}")
                
                time.sleep(10)
                
        except Exception as e:
            print(f"{C_RED}[-] Lỗi hệ thống khi kết nối GoLike: {e}{C_RESET}")
            time.sleep(10)
        
    time.sleep(2)

def manage_and_run():
    token = get_authorization()
    gl_accounts = get_golike_accounts(token)
    
    if not gl_accounts:
        print(f"\n{C_RED}[-] KHÔNG CÓ DỮ LIỆU TÀI KHOẢN. Vui lòng kiểm tra lại Token!{C_RESET}")
        return
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{C_CYAN}=========================================================={C_RESET}")
        print(f"{C_WHITE}{'STT':<4} | {'USERNAME INSTAGRAM':<25} | {'ID GOLIKE'}{C_RESET}")
        print(f"{C_CYAN}=========================================================={C_RESET}")
        
        for index, acc in enumerate(gl_accounts):
            user_ig = acc.get('instagram_username')
            id_gl = acc.get('id')
            color_row = C_GREEN if index % 2 == 0 else C_WHITE
            print(f"{color_row}{index + 1:<4} | {user_ig:<25} | {id_gl}{C_RESET}")
            
        print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
        print(f"{C_YELLOW}[ HƯỚNG DẪN ĐIỀU KHIỂN ]{C_RESET}")
        print(f"  > Nhập số {C_GREEN}STT{C_RESET} của nick (Ví dụ: 1,4,12...) để chọn làm job.")
        print(f"  > Nhập chữ {C_RED}'E'{C_RESET} để thoát tool.")
        print(f"{C_CYAN}----------------------------------------------------------{C_RESET}")
        
        user_choice = input(f"{C_CYAN}[>] Lựa chọn của bạn: {C_RESET}").strip()
        
        if user_choice.lower() == 'e':
            print(f"{C_RED}[-] Đã đóng chương trình.{C_RESET}")
            break
                
        else:
            try:
                idx = int(user_choice) - 1
                if 0 <= idx < len(gl_accounts):
                    target_acc = gl_accounts[idx]
                    target_user = target_acc.get('instagram_username')
                    target_id = target_acc.get('id')
                    
                    try:
                        max_j = int(input(f"{C_YELLOW}[?] Số lượng job muốn làm cho nick '{target_user}' (Mặc định 10): {C_RESET}"))
                    except:
                        max_j = 10
                        
                    run_job_for_account(token, target_id, target_user, max_j)
                else:
                    print(f"{C_RED}[-] Số thứ tự tài khoản không tồn tại!{C_RESET}")
                    time.sleep(1.5)
            except ValueError:
                print(f"{C_RED}[-] Vui lòng nhập số STT hợp lệ hoặc nhập 'E' để thoát!{C_RESET}")
                time.sleep(1.5)

if __name__ == "__main__":
    manage_and_run()
