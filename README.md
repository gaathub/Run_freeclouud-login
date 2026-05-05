# Freeclouud 自动登录与签到脚本

🤖 一个功能强大的自动化脚本，用于自动登录 Freeclouud 账户、完成每日签到、自动续费云服务器。

## 功能特性

✨ **核心功能：**

- 🔐 **自动登录** - 自动填充用户名、密码并识别验证码
- 📋 **每日签到** - 自动完成数学验证，获取积分奖励
- 💻 **云服务器续费** - 当积分充足时自动续费云服务器
- 🛡️ **反爬虫对抗** - 内置 Cloudflare 5秒盾和 Turnstile 验证绕过
- 📸 **截图记录** - 自动保存每步操作的截图用于调试
- 🔄 **多账号支持** - 支持批量处理多个账号
- 🌐 **代理支持** - 支持通过环境变量配置 HTTP 代理

## 技术栈

- **Python 3.7+**
- **SeleniumBase** - 浏览器自动化框架
- **ddddocr** - 验证码识别
- **Chrome/Chromium** - 浏览器引擎

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/kystor/freeclouud-login.git
cd freeclouud-login
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

如果没有 requirements.txt，请手动安装：

```bash
pip install seleniumbase ddddocr
```

### 3. 初始化 SeleniumBase

```bash
seleniumbase install chromedriver
```

## 使用方法

### 基础用法

通过环境变量传入账户信息运行脚本：

```bash
export acount="user1@example.com:password1,user2@example.com:password2"
python auto_login.py
```

### 支持代理

如需使用代理，设置 `HTTP_PROXY` 环境变量：

```bash
export HTTP_PROXY="http://proxy-server:port"
export acount="user@example.com:password"
python auto_login.py
```

### 账户格式

环境变量 `acount` 的格式为：
- **单个账户**：`email@example.com:password`
- **多个账户**：`email1@example.com:password1,email2@example.com:password2`

**示例：**

```bash
export acount="test1@mail.com:pass123,test2@mail.com:pass456"
python auto_login.py
```

## 工作流程

脚本执行的完整流程：

```
1. 访问登录页面
   ├─ 检测并绕过 Cloudflare 5秒盾
   └─ 检测并通过 Turnstile 验证

2. 自动登录
   ├─ 获取验证码图片
   ├─ OCR 识别验证码
   ├─ 填充用户名、密码、验证码
   └─ 点击登录

3. 每日签到
   ├─ 导航至签到页面
   ├─ 点击签到按钮
   ├─ 自动解答数学问题
   ├─ 提交答案
   └─ 提取并记录积分余额

4. 积分判断
   ├─ 若积分 >= 0.01 元
   │  ├─ 导航至云服务器列表
   │  ├─ 勾选待续费服务器
   │  ├─ 生成续费订单
   │  ├─ 完成支付
   │  └─ 返回签到中心查看最新积分
   └─ 若积分 < 0.01 元，安全退出

5. 脚本完成
   └─ 输出所有账户的处理结果
```

## 配置说明

脚本在 `auto_login.py` 中的 `CONFIG` 字典包含所有网页元素选择器配置。无需修改即可使用，但若网站更新样式，请根据以下说明调整：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `target_url` | 登录页面URL | `https://nat.freecloud.ltd/login` |
| `username_selector` | 用户名输入框选择器 | `#emailInp` |
| `password_selector` | 密码输入框选择器 | `#emailPwdInp` |
| `captcha_img_selector` | 验证码图片选择器 | `#allow_login_email_captcha` |
| `captcha_input_selector` | 验证码输入框选择器 | `#captcha_allow_login_email_captcha` |
| `login_btn_selector` | 登录按钮选择器 | `button[type="submit"]` |
| `sign_in_url` | 签到页面URL | `https://nat.freecloud.ltd/addons...` |
| `server_list_url` | 云服务器列表URL | `https://nat.freecloud.ltd/service?groupid=305` |

## 截图输出

脚本会在 `screenshots/` 目录下自动保存每个步骤的截图，文件命名格式：

```
screenshots/{username}_{step_name}.png
```

**示例：**
```
screenshots/test_email_com_1_初始访问页面.png
screenshots/test_email_com_2_准备填写表单.png
screenshots/test_email_com_8_云服务器列表页.png
```

这些截图可用于：
- 🐛 调试问题
- ✅ 验证执行结果
- 📋 操作记录备份

## 常见问题

### Q: 脚本卡在 Cloudflare 验证？

**A:** 这是正常的。脚本会自动检测并尝试绕过 CF 5秒盾，最多重试 4 次。若多次失败可能是：
- 代理 IP 被封禁（提示 `Error 1005`）
- 网络连接问题

### Q: 验证码识别失败？

**A:** `ddddocr` 的识别率约 90%。如识别失败，脚本会捕获截图供调试，可检查 `screenshots/` 目录下的验证码图片。

### Q: 如何修改网站配置？

**A:** 编辑 `auto_login.py` 中的 `CONFIG` 字典。使用浏览器开发者工具（F12）检查网页元素，获取正确的 CSS 选择器。

### Q: 支持 Python 2 吗？

**A:** 不支持，需要 **Python 3.7+**。

### Q: 脚本如何处理账户密码安全？

**A:** 
- ⚠️ **不要**在代码中硬编码密码
- 使用环境变量传入敏感信息
- 在 CI/CD 中使用 Secrets 管理

## 环境变量参考

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `acount` | 账户列表（必需） | `user@mail.com:pass123` |
| `HTTP_PROXY` | HTTP代理地址（可选） | `http://proxy:8080` |

## 日志输出示例

```
🚀 自动化任务启动...
📋 共检测到 2 个账号。

==========================================
➡️ 开始处理账号: user1@example.com
==========================================
🌐 正在访问目标网站: https://nat.freecloud.ltd/login
📸 已截图保存: screenshots/user1_example_com_1_初始访问页面.png
🛡️ 检测到 CF 5秒盾，准备破除...
✅ CF 5秒盾已通过！
📄 登录成功，当前页面: FreeCloud - Dashboard

>>> 🎁 准备执行每日签到任务...
✅ 计算结果为整数: 42，正在提交...
🔔 签到系统提示: 【今天已经签到过了】
💰 当前账户原始信息: 可用积分: 5.26
🔍 提取并转换可用积分为: 5.26

🏁 所有队列任务已全部执行完成！
```

## 故障排查

### 1. 导入错误

```
ModuleNotFoundError: No module named 'seleniumbase'
```

**解决：** 运行 `pip install seleniumbase ddddocr`

### 2. 浏览器无法启动

```
Error: ChromeDriver not found
```

**解决：** 运行 `seleniumbase install chromedriver`

### 3. 验证码无法识别

脚本会在 `screenshots/` 中保存验证码图片，可手动检查识别效果。

### 4. 账户无法登录

- 检查用户名和密码是否正确
- 查看 `screenshots/` 中的登录页面截图
- 确认账户未被锁定或限制

## 声明

⚠️ **仅供学习和研究使用**

此脚本仅用于个人账户的自动化操作。使用本脚本需遵守 Freeclouud 服务条款。

用户对脚本的使用承担全部责任。开发者不对任何损失负责。

## 许可证

MIT License

## 作者

[@kystor](https://github.com/kystor)

---

**最后更新：** 2026年5月5日

如有问题，欢迎提交 Issue 或 PR！