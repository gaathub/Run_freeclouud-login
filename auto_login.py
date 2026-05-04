import time
import os
import base64
import sys
from seleniumbase import SB
import ddddocr

# ==========================================
# 1. 网站配置区域 (新增了签到相关的选择器)
# ==========================================
CONFIG = {
    "target_url": "https://nat.freecloud.ltd/login",
    "username_selector": "#emailInp",             
    "password_selector": "#emailPwdInp",          
    "captcha_img_selector": "#allow_login_email_captcha",          
    "captcha_input_selector": "#captcha_allow_login_email_captcha", 
    "login_btn_selector": 'button[type="submit"]',
    
    # 🌟 新增：签到页面的元素定位器
    "sign_in_menu_selector": 'a[href*="_plugin=19"]',                # 左侧菜单的“签到中心”链接
    "sign_in_btn_selector": 'button[onclick="showMathVerification()"]', # “我要签到”按钮
    "math_question_selector": '#mathQuestion',                       # 算术题文本标签
    "math_input_selector": '#userAnswer',                            # 答案输入框
    "verify_btn_selector": 'button[onclick="checkAnswer()"]'         # “验证答案”按钮
}

# 提前创建一个文件夹，用来专门存放截图
os.makedirs("screenshots", exist_ok=True)

# 截图辅助函数
def take_screenshot(sb, step_name, username="system"):
    safe_name = username.replace("@", "_").replace(".", "_")
    filepath = f"screenshots/{safe_name}_{step_name}.png"
    try:
        sb.save_screenshot(filepath)
        print(f"    📸 已截图保存: {filepath}")
    except Exception as e:
        print(f"    ⚠️ 截图失败 ({filepath}): {e}")

# ==========================================
# 2. Cloudflare 绕过辅助函数 (保持不变)
# ==========================================
def is_cloudflare_interstitial(sb) -> bool:
    try:
        page_source = sb.get_page_source()
        title = sb.get_title().lower() if sb.get_title() else ""
        indicators = ["Just a moment", "Verify you are human", "Checking your browser", "Checking if the site connection is secure"]
        for ind in indicators:
            if ind in page_source:
                return True
        if "just a moment" in title or "attention required" in title:
            return True
        body_len = sb.execute_script('(function() { return document.body ? document.body.innerText.length : 0; })();')
        if body_len is not None and body_len < 200 and "challenges.cloudflare.com" in page_source:
            return True
        return False
    except:
        return False

def bypass_cloudflare_interstitial(sb, max_attempts=3) -> bool:
    print("    🛡️ 检测到 CF 5秒盾，准备破除...")
    for attempt in range(max_attempts):
        print(f"      ▶ 尝试绕过 ({attempt+1}/{max_attempts})...")
        try:
            sb.uc_gui_click_captcha()
            time.sleep(6)
            if not is_cloudflare_interstitial(sb):
                print("      ✅ CF 5秒盾已通过！")
                return True
        except Exception as e:
            pass
        time.sleep(3)
    return False

def handle_turnstile_verification(sb) -> bool:
    try:
        cookie_btn = 'button[data-cky-tag="accept-button"]'
        if sb.is_element_visible(cookie_btn):
            sb.click(cookie_btn)
            time.sleep(1)
    except:
        pass

    sb.execute_script('''
        try {
            var t = document.querySelector('.cf-turnstile') || 
                    document.querySelector('iframe[src*="challenges.cloudflare"]') || 
                    document.querySelector('iframe[src*="turnstile"]');
            if (t) t.scrollIntoView({behavior:'smooth', block:'center'});
        } catch(e) {}
    ''')
    time.sleep(2)

    has_turnstile = False
    for _ in range(15):
        if (sb.is_element_present('iframe[src*="challenges.cloudflare"]') or 
            sb.is_element_present('iframe[src*="turnstile"]') or 
            sb.is_element_present('.cf-turnstile') or 
            sb.is_element_present('input[name="cf-turnstile-response"]')):
            has_turnstile = True
            break
        time.sleep(1)

    if not has_turnstile:
        print("    🟢 无感验证通过 (未发现 Turnstile)")
        return True

    print("    🧩 发现验证码，执行拟人点击...")
    verified = False
    
    for attempt in range(1, 4):
        try:
            sb.uc_gui_click_captcha()
        except:
            pass
            
        for _ in range(10):
            if sb.is_element_present('input[name="cf-turnstile-response"]'):
                token = sb.get_attribute('input[name="cf-turnstile-response"]', 'value')
                if token and len(token) > 20:
                    print("      ✅ 物理点击成功，已获取 Token！")
                    verified = True
                    break
            time.sleep(1)
            
        if verified:
            break

    if not verified:
        for _ in range(30):
            if sb.is_element_present('input[name="cf-turnstile-response"]'):
                token = sb.get_attribute('input[name="cf-turnstile-response"]', 'value')
                if token and len(token) > 20:
                    print("      ✅ 验证码自动放行，已获取 Token！")
                    verified = True
                    break
            time.sleep(1)

    return verified

# ==========================================
# 3. 单个账号的处理流程（包含登录 + 签到逻辑）
# ==========================================
def process_single_account(username, password):
    print(f"\n==========================================")
    print(f"➡️ 开始处理账号: {username}")
    print(f"==========================================")
    
    env_proxy = os.environ.get("HTTP_PROXY")
    
    with SB(
        uc=True,            
        test=True,          
        locale="en",        
        headless=False,      
        proxy=env_proxy,    
        chromium_arg="--disable-blink-features=AutomationControlled,--window-size=1920,1080"
    ) as sb:
        print(f"🌐 正在访问目标网站: {CONFIG['target_url']}")
        sb.uc_open_with_reconnect(CONFIG['target_url'], reconnect_time=8)
        time.sleep(4)
        
        take_screenshot(sb, "1_初始访问页面", username)

        # 检测 1005 拦截
        page_source = sb.get_page_source()
        if "Error 1005" in page_source or "Access denied" in page_source:
            print("🚨 致命错误：当前代理节点的 IP 被目标网站彻底封锁 (Error 1005)！")
            take_screenshot(sb, "Error_1005_节点被封锁", username)
            sys.exit(1)

        # 过 5秒盾 和 Turnstile
        if is_cloudflare_interstitial(sb):
            if not bypass_cloudflare_interstitial(sb):
                return 
            time.sleep(3) 
            
        handle_turnstile_verification(sb)
        time.sleep(3)
        take_screenshot(sb, "2_准备填写表单", username)

        try:
            # --- 登录模块开始 ---
            print(">>> 正在提取 Base64 验证码数据...")
            sb.wait_for_element(CONFIG['captcha_img_selector'], timeout=10)
            img_src = sb.get_attribute(CONFIG['captcha_img_selector'], "src")
            
            if "base64," in img_src:
                base64_data = img_src.split(',')[1]
                img_bytes = base64.b64decode(base64_data)
                
                ocr = ddddocr.DdddOcr(show_ad=False)
                captcha_text = ocr.classification(img_bytes)
                print(f">>> 🤖 ddddocr 识别出的验证码为: {captcha_text}")
            else:
                print(">>> ⚠️ 错误：验证码格式不对，跳过。")
                return

            print(">>> 正在输入账号、密码和验证码...")
            sb.type(CONFIG['username_selector'], username)
            sb.type(CONFIG['password_selector'], password)
            sb.type(CONFIG['captcha_input_selector'], captcha_text)
            
            take_screenshot(sb, "3_已填写数据准备登录", username)
            sb.click(CONFIG['login_btn_selector'])

            time.sleep(5)
            print(f"📄 登录成功，当前页面: {sb.get_title()}")
            take_screenshot(sb, "4_登录后的结果页面", username)
            # --- 登录模块结束 ---


            # ==========================================
            # 🌟 新增模块：每日签到与算术题处理
            # ==========================================
            print("\n>>> 🎁 准备执行每日签到任务...")
            
            # 1. 点击进入签到中心
            print("    ▶ 正在进入签到中心...")
            sb.click(CONFIG['sign_in_menu_selector'])
            time.sleep(3) # 等待页面跳转加载
            take_screenshot(sb, "5_进入签到中心", username)

            # 设定最多重试 5 次，防止遇到死循环
            max_retries = 5
            for attempt in range(max_retries):
                print(f"    ▶ 点击【我要签到】 (尝试 {attempt + 1}/{max_retries})...")
                sb.click(CONFIG['sign_in_btn_selector'])
                time.sleep(2) # 等待弹窗和题目显示
                
                # 2. 从网页上抓取题目文本，例如 "请计算：10 * 3"
                question_text = sb.get_text(CONFIG['math_question_selector'])
                print(f"    ❓ 提取到题目: {question_text}")
                
                # 3. 剥离中文，留下纯数字和符号："请计算：10 * 3" -> "10 * 3"
                math_expr = question_text.replace("请计算：", "").replace("=", "").strip()
                
                # 4. 让 Python 帮我们算出结果。eval() 是一个很强大的内置函数，能直接执行字符串里的数学运算
                result = eval(math_expr)
                
                # 5. 核心逻辑：判断是不是“除不尽”的小数
                #    isinstance(result, float) 是看结果带不带小数点
                #    not result.is_integer() 是看小数位是不是 0。例如 5.0 是整数，但 3.33 就不是。
                if isinstance(result, float) and not result.is_integer():
                    print(f"    ⚠️ 遇到除不尽的题目 ({math_expr} = {result})，准备刷新...")
                    sb.refresh() # 刷新网页，重新再来一次循环
                    time.sleep(3)
                    continue     # 跳过下面的代码，直接进入下一次 attempt 循环
                
                # 6. 如果代码走到这里，说明是完美的整数，准备提交！
                final_answer = int(result) 
                print(f"    ✅ 计算结果为完美整数: {final_answer}，正在提交...")
                
                sb.type(CONFIG['math_input_selector'], str(final_answer))
                take_screenshot(sb, f"6_填写签到算术题_尝试{attempt+1}", username)
                
                # 点击验证并提交答案
                sb.click(CONFIG['verify_btn_selector'])
                time.sleep(4) 
                
                take_screenshot(sb, "7_签到完成结果", username)
                print("    🎉 签到操作执行完毕！\n")
                break # 签到成功了，跳出循环！
                
            else:
                # 如果 5 次循环跑完了都没 `break`，说明运气太差全是除不尽的
                print("    ❌ 签到失败：连续 5 次刷新都没有遇到可以整除的算术题。")

        except Exception as e:
            print(f"    ❌ 账号处理或签到过程中出现错误(可能今天已签到过): {e}")
            take_screenshot(sb, "Error_程序崩溃截图", username)

# ==========================================
# 4. 主程序入口
# ==========================================
def main():
    print("🚀 自动化任务启动...")
    accounts_str = os.environ.get("acount")
    
    if not accounts_str:
        print("⚠️ 未获取到名为 'acount' 环境变量！")
        return

    account_list = accounts_str.split(',')
    print(f"📋 共检测到 {len(account_list)} 个账号。")
    
    for item in account_list:
        item = item.strip()
        if ':' in item:
            parts = item.split(':', 1) 
            username = parts[0].strip()
            password = parts[1].strip()
            process_single_account(username, password)
        else:
            print(f"⚠️ 账号格式不正确: {item}")
            
    print("\n🏁 所有队列任务已全部执行完成！")

if __name__ == "__main__":
    main()
