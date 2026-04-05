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
