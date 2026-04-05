document.addEventListener('DOMContentLoaded', () => {
  const sourceText = document.getElementById('sourceText');
  const targetLang = document.getElementById('targetLang');
  const translateBtn = document.getElementById('translateBtn');
  const resultDiv = document.getElementById('result');
  const statusDiv = document.getElementById('status');

  // OCR 相关元素
  const imageFile = document.getElementById('imageFile');
  const ocrBtn = document.getElementById('ocrBtn');
  const ocrStatus = document.getElementById('ocrStatus');
  const ocrApiKeyInput = document.getElementById('ocrApiKey');

  // 加载保存的 API Key
  chrome.storage.local.get(['ocrApiKey'], (result) => {
    if (result.ocrApiKey) {
      ocrApiKeyInput.value = result.ocrApiKey;
    }
  });

  // 保存 API Key
  ocrApiKeyInput.addEventListener('change', () => {
    chrome.storage.local.set({ ocrApiKey: ocrApiKeyInput.value });
  });

  // 翻译功能（保持不变）
  translateBtn.addEventListener('click', async () => {
    const text = sourceText.value.trim();
    if (!text) {
      resultDiv.textContent = '请输入要翻译的文本';
      return;
    }

    const target = targetLang.value;
    const apiUrl = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(text)}&langpair=auto|${target}`;

    statusDiv.textContent = '翻译中...';
    resultDiv.textContent = '';

    try {
      const response = await fetch(apiUrl);
      const data = await response.json();

      if (data.responseData && data.responseData.translatedText) {
        resultDiv.textContent = data.responseData.translatedText;
        statusDiv.textContent = `翻译完成 (来源: ${data.responseData.match || 'MyMemory'})`;
      } else {
        throw new Error('未获取到翻译结果');
      }
    } catch (error) {
      console.error(error);
      resultDiv.textContent = '翻译失败，请检查网络或稍后重试';
      statusDiv.textContent = error.message;
    }
  });

  // OCR 识别图片文字
  ocrBtn.addEventListener('click', async () => {
    const file = imageFile.files[0];
    if (!file) {
      ocrStatus.textContent = '请先选择一张图片';
      return;
    }

    const apiKey = ocrApiKeyInput.value.trim();
    // 如果没有提供 API Key，使用演示 Key（可能每天限制，建议用户注册）
    const finalApiKey = apiKey || 'helloworld'; // OCR.space 官方演示 key

    ocrStatus.textContent = '识别中...';
    ocrBtn.disabled = true;

    try {
      // 使用 FormData 发送文件到 OCR.space
      const formData = new FormData();
      formData.append('apikey', finalApiKey);
      formData.append('file', file);
      formData.append('language', 'eng'); // 可改为 'chs' 支持中文，但免费版可能限制
      formData.append('isOverlayRequired', 'false');
      formData.append('OCREngine', '2'); // 使用较新引擎

      const response = await fetch('https://api.ocr.space/parse/image', {
        method: 'POST',
        body: formData
      });
      const data = await response.json();

      if (data.IsErroredOnProcessing) {
        throw new Error(data.ErrorMessage?.[0] || 'OCR 处理失败');
      }

      const parsedText = data.ParsedResults?.[0]?.ParsedText || '';
      if (!parsedText) {
        ocrStatus.textContent = '未能识别出文字，请换一张图片重试';
        return;
      }

      // 将识别出的文本填入源文本区
      sourceText.value = parsedText;
      ocrStatus.textContent = `识别成功，共 ${parsedText.length} 个字符`;

      // 可选：自动执行翻译
      translateBtn.click();
    } catch (error) {
      console.error(error);
      ocrStatus.textContent = `识别失败: ${error.message}`;
    } finally {
      ocrBtn.disabled = false;
    }
  });
});