# 严格按格式输出

非常抱歉，之前的输出没有严格遵守您要求的格式，尤其是对 `manifest.json` 的修改未能匹配您提供的原文。现在将严格按照格式输出所有需要修改的部分，仅包含 **SEARCH/REPLACE 块**（新增文件仍使用 CREATE）。

## 修改清单

### `manifest.json`（基于您提供的原文添加 `options_ui`）

```aider MODIFY: manifest.json
<<<<<<< SEARCH
  "host_permissions": [
    "https://translate.googleapis.com/*",
    "https://api.ocr.space/*"
  ],
=======
  "host_permissions": [
    "https://translate.googleapis.com/*",
    "https://api.ocr.space/*"
  ],
  "options_ui": {
    "page": "options.html",
    "open_in_tab": false
  },
>>>>>>> REPLACE
```

> **说明**：假设您的 `manifest.json` 中 `host_permissions` 数组后直接是其他字段（如 `background`），此修改会在其后插入 `options_ui` 对象。若您之前已通过 `CREATE` 覆盖了完整文件，此修改依然有效。

---

### `background.js`（添加图片菜单和 OCR 处理）

#### 1. 在创建菜单时增加图片菜单

```aider MODIFY: background.js
<<<<<<< SEARCH
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "translate-selection",
    title: "翻译选中文本",
    contexts: ["selection"]
  });
});
=======
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "translate-selection",
    title: "翻译选中文本",
    contexts: ["selection"]
  });
  chrome.contextMenus.create({
    id: "ocr-translate-image",
    title: "识图翻译",
    contexts: ["image"]
  });
});
>>>>>>> REPLACE
```

#### 2. 在菜单点击处理中添加图片分支

```aider MODIFY: background.js
<<<<<<< SEARCH
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "translate-selection" && info.selectionText) {
    const selectedText = info.selectionText.trim();
    chrome.tabs.sendMessage(tab.id, {
      action: "translate",
      text: selectedText
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn("内容脚本未响应", chrome.runtime.lastError);
      }
    });
  }
});
=======
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "translate-selection" && info.selectionText) {
    const selectedText = info.selectionText.trim();
    chrome.tabs.sendMessage(tab.id, {
      action: "translate",
      text: selectedText
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn("内容脚本未响应", chrome.runtime.lastError);
      }
    });
  } else if (info.menuItemId === "ocr-translate-image" && info.srcUrl) {
    handleImageTranslate(info.srcUrl, tab.id);
  }
});
>>>>>>> REPLACE
```

#### 3. 在文件末尾添加 OCR 处理函数（紧接现有 `translateText` 函数之后）

```aider MODIFY: background.js
<<<<<<< SEARCH
async function translateText(text, targetLang = "zh-CN") {
  const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${targetLang}&dt=t&q=${encodeURIComponent(text)}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`翻译服务响应错误: ${response.status}`);
  }
  const data = await response.json();
  return data[0].map(item => item[0]).join("");
}
=======
async function translateText(text, targetLang = "zh-CN") {
  const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${targetLang}&dt=t&q=${encodeURIComponent(text)}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`翻译服务响应错误: ${response.status}`);
  }
  const data = await response.json();
  return data[0].map(item => item[0]).join("");
}

async function handleImageTranslate(imageUrl, tabId) {
  try {
    chrome.tabs.sendMessage(tabId, {
      action: "showMessage",
      message: "正在识别图片文字...",
      isError: false
    }).catch(() => {});

    const { ocrApiKey } = await chrome.storage.sync.get("ocrApiKey");
    if (!ocrApiKey) {
      throw new Error("请先在插件设置中配置 OCR API Key (https://ocr.space/ocrapi)");
    }

    const ocrText = await ocrImage(imageUrl, ocrApiKey);
    if (!ocrText || ocrText.trim() === "") {
      throw new Error("图片中未识别到文字");
    }

    chrome.tabs.sendMessage(tabId, {
      action: "showMessage",
      message: `识别结果：${ocrText}\n正在翻译...`,
      isError: false
    }).catch(() => {});

    const translation = await translateText(ocrText, "zh-CN");
    
    chrome.tabs.sendMessage(tabId, {
      action: "showTranslateResult",
      original: ocrText,
      translation: translation
    }).catch(() => {});
  } catch (error) {
    console.error("识图翻译失败:", error);
    chrome.tabs.sendMessage(tabId, {
      action: "showMessage",
      message: `识图翻译失败：${error.message}`,
      isError: true
    }).catch(() => {});
  }
}

async function ocrImage(imageUrl, apiKey) {
  const formData = new FormData();
  formData.append("apikey", apiKey);
  formData.append("url", imageUrl);
  formData.append("language", "eng");
  formData.append("isOverlayRequired", "false");
  formData.append("detectOrientation", "true");

  const response = await fetch("https://api.ocr.space/parse/image", {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    throw new Error(`OCR API 响应错误: ${response.status}`);
  }
  const data = await response.json();
  if (data.IsErroredOnProcessing) {
    throw new Error(data.ErrorMessage[0] || "OCR 识别失败");
  }
  const parsedTexts = data.ParsedResults.map(result => result.ParsedText).filter(t => t);
  return parsedTexts.join("\n").trim();
}
>>>>>>> REPLACE
```

---

### `content.js`（增加对新消息类型的处理）

```aider MODIFY: content.js
<<<<<<< SEARCH
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "translate") {
    const text = request.text;
    const toast = createToast();
    toast.innerHTML = `<strong>翻译中...</strong> ${escapeHtml(text)}`;
    toast.style.opacity = "1";

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
=======
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "translate") {
    const text = request.text;
    const toast = createToast();
    toast.innerHTML = `<strong>翻译中...</strong> ${escapeHtml(text)}`;
    toast.style.opacity = "1";

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
  } else if (request.action === "showMessage") {
    const toast = createToast();
    toast.innerHTML = escapeHtml(request.message);
    toast.style.opacity = "1";
    const timeout = request.isError ? 3000 : 5000;
    clearTimeout(window.toastTimeout);
    window.toastTimeout = setTimeout(() => {
      toast.style.opacity = "0";
    }, timeout);
    sendResponse({ received: true });
  } else if (request.action === "showTranslateResult") {
    const toast = createToast();
    toast.innerHTML = `
      <strong>识别文字：</strong> ${escapeHtml(request.original)}<br>
      <strong>翻译结果：</strong> ${escapeHtml(request.translation)}
    `;
    toast.style.opacity = "1";
    clearTimeout(window.toastTimeout);
    window.toastTimeout = setTimeout(() => {
      toast.style.opacity = "0";
    }, 8000);
    sendResponse({ received: true });
  }
  return true;
});
>>>>>>> REPLACE
```

---

### 新增文件

#### `options.html`
```html CREATE: options.html
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>翻译插件设置</title></head>
<body>
<div style="padding:20px;min-width:300px">
  <h3>OCR API Key</h3>
  <input type="text" id="apiKey" style="width:100%" placeholder="输入 OCR.space API Key">
  <button id="save" style="margin-top:10px">保存</button>
  <p style="font-size:12px;color:#666">申请地址：<a href="https://ocr.space/ocrapi" target="_blank">https://ocr.space/ocrapi</a></p>
  <div id="status"></div>
</div>
<script src="options.js"></script>
</body>
</html>
```

#### `options.js`
```javascript CREATE: options.js
document.addEventListener("DOMContentLoaded", () => {
  const apiKeyInput = document.getElementById("apiKey");
  const saveBtn = document.getElementById("save");
  const statusDiv = document.getElementById("status");

  chrome.storage.sync.get("ocrApiKey", (data) => {
    if (data.ocrApiKey) apiKeyInput.value = data.ocrApiKey;
  });

  saveBtn.addEventListener("click", () => {
    const key = apiKeyInput.value.trim();
    if (!key) {
      statusDiv.textContent = "请输入 API Key";
      statusDiv.style.color = "red";
      return;
    }
    chrome.storage.sync.set({ ocrApiKey: key }, () => {
      statusDiv.textContent = "保存成功";
      statusDiv.style.color = "green";
      setTimeout(() => statusDiv.textContent = "", 2000);
    });
  });
});
```

---

以上所有修改均严格遵守输出格式：只输出修改块（SEARCH/REPLACE）和新增文件（CREATE）。请检查。