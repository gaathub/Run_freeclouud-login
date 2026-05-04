import time
import os
import base64
from seleniumbase import SB
import ddddocr

# ==========================================
# 1. 网站配置区域
# ==========================================
CONFIG = {
    "target_url": "https://nat.freecloud.ltd/login",
    "username_selector": "#emailInp",             
    "password_selector": "#emailPwdInp",          
    "captcha_img_selector": "#allow_login_email_captcha",          
    "captcha_input_selector": "#captcha_allow_login_email_captcha", 
    "login_btn_selector": 'button[type="submit"]'                  
}

# 提前创建一个文件夹，用来专门存放截图，方便后续通过 GitHub Actions 下载查看运行情况
os.makedirs("screenshots", exist_ok=True)

# 截图辅助函数：自动给图片加上账号名和步骤编号
def take_screenshot(sb, step_name, username="system"):
    # 为了防止邮箱里的 @ 或 . 导致文件名异常，替换成下划线
    safe_name = username.replace("@", "_").replace(".", "_")
    filepath = f"screenshots/{safe_name}_{step_name}.png"
    try:
        sb.save_screenshot(filepath)
        print(f"    📸 已截图保存: {filepath}")
    except Exception as e:
        print(f"    ⚠️ 截图失败 ({filepath}): {e}")

# ==========================================
# 2. Cloudflare 绕过辅助函数 
# ==========================================
def is_cloudflare_interstitial(sb) -> bool:
    """检测当前页面是否处于 Cloudflare 5秒盾拦截状态"""
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
    """尝试通过点击绕过 Cloudflare 拦截"""
    print("    🛡️ 检测到 CF 5秒盾，准备破除...")
    for attempt in range(max_attempts):
        print(f"      ▶ 尝试绕过 ({attempt+1}/{max_attempts})...")
        try:
            # 这个函数依赖 PyAutoGUI 进行物理鼠标点击，必须在非无头模式（headless=False）下运行
            sb.uc_gui_click_captcha()
            time.sleep(6)
            if not is_cloudflare_interstitial(sb):
                print("      ✅ CF 5秒盾已通过！")
                return True
        except Exception as e:
            print(f"      ⚠️ 绕过异常: {e}")
        time.sleep(3)
    return False

def handle_turnstile_verification(sb) -> bool:
    """处理页面内嵌的 Cloudflare Turnstile 人机验证控件"""
    try:
        # 清理可能遮挡验证码的 Cookie 同意弹窗
        cookie_btn = 'button[data-cky-tag="accept-button"]'
        if sb.is_element_visible(cookie_btn):
            print("    🍪 清理 Cookie 弹窗干扰...")
            sb.click(cookie_btn)
            time.sleep(1)
    except:
        pass

    # 将页面滚动到验证码区域的中心位置，确保可以被点击到
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
        print(f"      ▶ 点击尝试 ({attempt}/3)...")
        try:
            sb.uc_gui_click_captcha()
        except:
            pass
            
        for _ in range(10):
            # 检查是否成功获取到了用于放行的 Token 令牌
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
        print("    ⏳ 等待验证码自动计算 (最多30秒)...")
        for _ in range(30):
            if sb.is_element_present('input[name="cf-turnstile-response"]'):
                token = sb.get_attribute('input[name="cf-turnstile-response"]', 'value')
                if token and len(token) > 20:
                    print("      ✅ 验证码自动放行，已获取 Token！")
                    verified = True
                    break
            time.sleep(1)

    if not verified:
        print("    ❌ 验证失败，未获取有效 Token。")
        return False
        
    return True

# ==========================================
# 3. 单个账号的处理流程（动态代理 + 虚拟屏幕适配）
# ==========================================
def process_single_account(username, password):
    print(f"\n==========================================")
    print(f"➡️ 开始处理账号: {username}")
    print(f"==========================================")
    
    # 动态代理读取：尝试从系统环境变量中获取代理地址
    env_proxy = os.environ.get("HTTP_PROXY")
    
    if env_proxy:
        print(f"🔌 检测到环境变量代理，已启用: {env_proxy}")
    else:
        print(f"🌐 未检测到代理环境变量，将使用直连模式。")

    # 初始化 SeleniumBase 浏览器对象
    with SB(
        uc=True,            # 开启反检测模式，伪装成真实用户
        test=True,          # 隐藏多余日志
        locale="en",        # 设置浏览器语言为英文
        
        # 🌟 修复报错的关键：必须为 False。配合 GitHub 的 Xvfb 虚拟屏幕，让 PyAutoGUI 能找到鼠标
        headless=False,      
        
        proxy=env_proxy,    # 将获取到的代理地址传递给浏览器
        chromium_arg="--disable-blink-features=AutomationControlled,--window-size=1920,1080"
    ) as sb:
        print(f"🌐 正在访问目标网站: {CONFIG['target_url']}")
        # 打开网页并设置重连时间，防止网络波动导致加载失败
        sb.uc_open_with_reconnect(CONFIG['target_url'], reconnect_time=8)
        time.sleep(4)
        
        # 【截图 1：刚进入网页】
        take_screenshot(sb, "1_初始访问页面", username)

        # 检查是否遇到 Cloudflare 5 秒盾拦截
        if is_cloudflare_interstitial(sb):
            if not bypass_cloudflare_interstitial(sb):
                print(f"❌ 无法绕过 CF 整页拦截，跳过此账号。")
                take_screenshot(sb, "Error_卡在CF盾", username)
                return 
            time.sleep(3) 
            
        print(f"🛡️ 检查并处理页面内的 Turnstile 验证码...")
        handle_turnstile_verification(sb)
        
        print("🎉 CF 验证已处理完毕，即将进入图片验证码环节。")
        time.sleep(3)
        
        # 【截图 2：完成CF验证，进入登录表单】
        take_screenshot(sb, "2_准备填写表单", username)

        try:
            print(">>> 正在提取 Base64 验证码数据...")
            # 等待图片验证码的元素加载出来，最多等 10 秒
            sb.wait_for_element(CONFIG['captcha_img_selector'], timeout=10)
            img_src = sb.get_attribute(CONFIG['captcha_img_selector'], "src")
            
            # 判断获取到的网页元素数据是否包含 base64 格式的图片
            if "base64," in img_src:
                base64_data = img_src.split(',')[1]
                # 将文本格式的 base64 数据解码成图片字节流
                img_bytes = base64.b64decode(base64_data)
                
                # 初始化 ddddocr 识别库进行光学字符识别
                ocr = ddddocr.DdddOcr(show_ad=False)
                captcha_text = ocr.classification(img_bytes)
                print(f">>> 🤖 ddddocr 识别出的验证码为: {captcha_text}")
            else:
                print(">>> ⚠️ 错误：验证码图片的 src 不是 base64 格式，跳过此账号！")
                return

            print(">>> 正在输入账号、密码和验证码...")
            # 自动在对应的输入框里填入信息
            sb.type(CONFIG['username_selector'], username)
            sb.type(CONFIG['password_selector'], password)
            sb.type(CONFIG['captcha_input_selector'], captcha_text)

            # 【截图 3：点击登录前的状态】
            take_screenshot(sb, "3_已填写数据准备登录", username)

            print(">>> 点击登录！")
            sb.click(CONFIG['login_btn_selector'])

            # 等待网站验证跳转
            time.sleep(5)
            print(f"📄 登录后的页面标题是: {sb.get_title()}")
            
            # 【截图 4：点击登录后的最终结果页面】
            take_screenshot(sb, "4_登录后的结果页面", username)
            print(f"✅ 账号 {username} 登录执行完毕！")

        except Exception as e:
            # 捕获错误并截图保留现场
            print(f"❌ 账号 {username} 处理过程中出现错误: {e}")
            take_screenshot(sb, "Error_程序崩溃截图", username)

# ==========================================
# 4. 主程序入口
# ==========================================
def main():
    print("🚀 自动化任务启动...")
    accounts_str = os.environ.get("acount")
    
    if not accounts_str:
        print("⚠️ 未获取到名为 'acount' 的环境变量，请检查 GitHub Secrets 配置！")
        return

    account_list = accounts_str.split(',')
    print(f"📋 共检测到 {len(account_list)} 个账号需要处理。")
    
    for item in account_list:
        item = item.strip()
        if ':' in item:
            parts = item.split(':', 1) 
            username = parts[0].strip()
            password = parts[1].strip()
            process_single_account(username, password)
        else:
            print(f"⚠️ 账号格式不正确（缺少冒号），已跳过: {item}")
            
    print("\n🏁 所有账号的队列任务已全部执行完成！")

if __name__ == "__main__":
    main()
