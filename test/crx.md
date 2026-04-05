# 浏览器翻译插件

实现一个右键菜单划词翻译的浏览器插件，使用 Google Translate 免费 API。

## 文件结构

### `manifest.json`
```json CREATE: manifest.json
{
  "manifest_version": 3,
  "name": "网页翻译助手",
  "version": "1.0",
  "description": "划词翻译插件，支持右键菜单翻译选中文本",
  "permissions": [
    "contextMenus",
    "activeTab",
    "storage"
  ],
  "host_permissions": [
    "https://translate.googleapis.com/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"]
    }
  ],
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

### `background.js`
```javascript CREATE: background.js
// 创建右键菜单
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "translate-selection",
    title: "翻译选中文本",
    contexts: ["selection"]
  });
});

// 监听菜单点击
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "translate-selection" && info.selectionText) {
    const selectedText = info.selectionText.trim();
    // 发送消息给内容脚本，让它显示加载状态并准备接收翻译结果
    chrome.tabs.sendMessage(tab.id, {
      action: "translate",
      text: selectedText
    }, (response) => {
      // 如果内容脚本未加载，尝试注入（实际上已经在 manifest 中声明了 content_scripts，应该没问题）
      if (chrome.runtime.lastError) {
        console.warn("内容脚本未响应", chrome.runtime.lastError);
      }
    });
  }
});

// 监听来自内容脚本的翻译请求（直接调用 API 更可靠）
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "fetchTranslation") {
    translateText(request.text, request.targetLang || "zh-CN")
      .then(translation => sendResponse({ translation }))
      .catch(error => sendResponse({ error: error.message }));
    return true; // 保持通道开放以便异步响应
  }
});

// 调用 Google Translate API
async function translateText(text, targetLang = "zh-CN") {
  // 自动检测源语言，目标语言中文
  const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${targetLang}&dt=t&q=${encodeURIComponent(text)}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`翻译服务响应错误: ${response.status}`);
  }
  const data = await response.json();
  // 返回合并后的翻译文本
  return data[0].map(item => item[0]).join("");
}
```

### `content.js`
```javascript CREATE: content.js
// 创建浮层元素
let toast = null;

function createToast() {
  if (toast) return toast;
  const div = document.createElement("div");
  div.id = "translation-toast";
  div.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    max-width: 400px;
    background: #2c3e50;
    color: #ecf0f1;
    padding: 12px 20px;
    border-radius: 8px;
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
    font-size: 14px;
    line-height: 1.5;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 999999;
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;
  `;
  document.body.appendChild(div);
  toast = div;
  return toast;
}

function showTranslation(text, translation) {
  const toast = createToast();
  toast.innerHTML = `
    <strong>原文：</strong> ${escapeHtml(text)}<br>
    <strong>译文：</strong> ${escapeHtml(translation)}
  `;
  toast.style.opacity = "1";
  // 5秒后自动隐藏
  clearTimeout(window.toastTimeout);
  window.toastTimeout = setTimeout(() => {
    toast.style.opacity = "0";
  }, 5000);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>]/g, function(m) {
    if (m === '&') return '&amp;';
    if (m === '<') return '&lt;';
    if (m === '>') return '&gt;';
    return m;
  }).replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, function(c) {
    return c;
  });
}

// 监听来自后台的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "translate") {
    const text = request.text;
    // 显示加载状态
    const toast = createToast();
    toast.innerHTML = `<strong>翻译中...</strong> ${escapeHtml(text)}`;
    toast.style.opacity = "1";

    // 向后台请求翻译
    chrome.runtime.sendMessage({
      action: "fetchTranslation",
      text: text,
      targetLang: "zh-CN"
    }, (response) => {
      if (response && response.translation) {
        showTranslation(text, response.translation);
      } else if (response && response.error) {
        const toast = createToast();
        toast.innerHTML = `<strong>翻译失败</strong> ${escapeHtml(response.error)}`;
        toast.style.opacity = "1";
        setTimeout(() => { toast.style.opacity = "0"; }, 3000);
      } else {
        const toast = createToast();
        toast.innerHTML = `<strong>翻译失败</strong> 请检查网络连接`;
        toast.style.opacity = "1";
        setTimeout(() => { toast.style.opacity = "0"; }, 3000);
      }
    });
    sendResponse({ received: true });
  }
  return true;
});
```

### 图标文件（占位说明）
插件需要三个尺寸的图标（16x16、48x48、128x128），请自行准备并放置在 `icons/` 目录下。若不需要图标，可将 `manifest.json` 中的 `icons` 字段移除。

## 使用说明
1. 将以上文件放入一个文件夹（如 `translate-extension`）。
2. 打开 Chrome 浏览器，进入 `chrome://extensions/`。
3. 开启“开发者模式”，点击“加载已解压的扩展程序”，选择该文件夹。
4. 安装后，在任意网页选中文本，右键选择“翻译选中文本”，即可在右下角看到翻译结果浮层。

## 注意事项
- 翻译使用 Google Translate 的公开接口，可能会因请求频率过高被限制，建议个人使用。
- 如果目标语言需要修改，可在 `background.js` 中修改 `translateText` 函数的 `targetLang` 参数。
- 该插件仅支持文本翻译，不支持页面整体翻译。