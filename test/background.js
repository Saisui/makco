// 创建右键菜单
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
  } else if (info.menuItemId === "ocr-translate-image" && info.srcUrl) {
    handleImageTranslate(info.srcUrl, tab.id);
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
