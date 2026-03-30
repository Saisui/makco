# 网站媒体资源下载器浏览器插件

实现一个浏览器扩展，自动检测当前页面中的图片、视频、音频等媒体资源，并提供一键下载功能。

## 文件结构

```
extension/
├── manifest.json
├── background.js
├── content.js
├── popup.html
├── popup.js
└── icon.png (可选，此处省略)
```

## 创建文件

### `manifest.json`
```json CREATE: manifest.json
{
  "manifest_version": 3,
  "name": "媒体资源下载器",
  "version": "1.0",
  "description": "下载当前页面中的图片、视频、音频等媒体资源",
  "permissions": ["downloads", "activeTab", "scripting"],
  "host_permissions": ["<all_urls>"],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icon.png",
      "48": "icon.png",
      "128": "icon.png"
    }
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ]
}
```

### `background.js`
```javascript CREATE: background.js
// 监听来自popup的消息，触发下载
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'download') {
    const url = request.url;
    const filename = request.filename || generateFilename(url);
    chrome.downloads.download({
      url: url,
      filename: filename,
      conflictAction: 'uniquify'
    }, (downloadId) => {
      if (chrome.runtime.lastError) {
        console.error('下载失败:', chrome.runtime.lastError);
        sendResponse({ success: false, error: chrome.runtime.lastError.message });
      } else {
        sendResponse({ success: true, downloadId });
      }
    });
    return true; // 保持消息通道开放，以便异步响应
  }
});

// 从URL生成默认文件名
function generateFilename(url) {
  try {
    const urlObj = new URL(url);
    let pathname = urlObj.pathname;
    let filename = pathname.substring(pathname.lastIndexOf('/') + 1);
    if (!filename || filename === '') {
      filename = 'download_' + Date.now();
    }
    return filename;
  } catch (e) {
    return 'download_' + Date.now();
  }
}
```

### `content.js`
```javascript CREATE: content.js
// 扫描页面中的媒体资源
function scanMediaResources() {
  const resources = {
    images: [],
    videos: [],
    audios: []
  };

  // 图片：img元素，background-image等简单起见只取img src
  document.querySelectorAll('img').forEach(img => {
    if (img.src && img.src.startsWith('http')) {
      resources.images.push(img.src);
    }
  });

  // 视频：video元素及其source
  document.querySelectorAll('video').forEach(video => {
    if (video.src && video.src.startsWith('http')) {
      resources.videos.push(video.src);
    }
    video.querySelectorAll('source').forEach(source => {
      if (source.src && source.src.startsWith('http')) {
        resources.videos.push(source.src);
      }
    });
  });

  // 音频：audio元素及其source
  document.querySelectorAll('audio').forEach(audio => {
    if (audio.src && audio.src.startsWith('http')) {
      resources.audios.push(audio.src);
    }
    audio.querySelectorAll('source').forEach(source => {
      if (source.src && source.src.startsWith('http')) {
        resources.audios.push(source.src);
      }
    });
  });

  // 可选：检测背景图片（简单示例，只检测内联样式，实际可扩展）
  const elementsWithBg = document.querySelectorAll('[style*="background-image"]');
  elementsWithBg.forEach(el => {
    const style = getComputedStyle(el);
    const bgImage = style.backgroundImage;
    if (bgImage && bgImage !== 'none') {
      const urlMatch = bgImage.match(/url\(["']?(.+?)["']?\)/);
      if (urlMatch && urlMatch[1] && urlMatch[1].startsWith('http')) {
        resources.images.push(urlMatch[1]);
      }
    }
  });

  // 去重（简单用Set）
  resources.images = [...new Set(resources.images)];
  resources.videos = [...new Set(resources.videos)];
  resources.audios = [...new Set(resources.audios)];

  return resources;
}

// 监听来自popup的消息，返回扫描结果
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getMedia') {
    const media = scanMediaResources();
    sendResponse(media);
  }
});
```

### `popup.html`
```html CREATE: popup.html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {
      width: 400px;
      max-height: 500px;
      font-family: sans-serif;
      margin: 0;
      padding: 10px;
    }
    h3 {
      margin: 0 0 8px 0;
      font-size: 16px;
    }
    .section {
      margin-bottom: 15px;
      border-bottom: 1px solid #ccc;
      padding-bottom: 10px;
    }
    .resource-list {
      max-height: 200px;
      overflow-y: auto;
      font-size: 12px;
    }
    .resource-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
      padding: 4px;
      background: #f5f5f5;
      border-radius: 4px;
    }
    .resource-url {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-right: 8px;
    }
    button {
      background: #4caf50;
      color: white;
      border: none;
      border-radius: 3px;
      padding: 2px 8px;
      cursor: pointer;
      font-size: 11px;
    }
    button:hover {
      background: #45a049;
    }
    .loading {
      text-align: center;
      color: #666;
    }
    .error {
      color: red;
    }
  </style>
</head>
<body>
  <h3>媒体资源下载器</h3>
  <div id="content">
    <div class="loading">加载中...</div>
  </div>
  <script src="popup.js"></script>
</body>
</html>
```

### `popup.js`
```javascript CREATE: popup.js
document.addEventListener('DOMContentLoaded', () => {
  const contentDiv = document.getElementById('content');
  
  // 获取当前活动标签页
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    if (!tab) {
      contentDiv.innerHTML = '<div class="error">无法获取当前页面</div>';
      return;
    }

    // 向content script发送消息获取媒体资源
    chrome.tabs.sendMessage(tab.id, { action: 'getMedia' }, (response) => {
      if (chrome.runtime.lastError) {
        contentDiv.innerHTML = '<div class="error">无法与页面通信，请刷新页面后重试。</div>';
        console.error(chrome.runtime.lastError);
        return;
      }

      if (!response) {
        contentDiv.innerHTML = '<div class="error">未检测到媒体资源。</div>';
        return;
      }

      renderMedia(response);
    });
  });

  function renderMedia(media) {
    let html = '';

    // 图片
    if (media.images && media.images.length > 0) {
      html += `<div class="section">
        <h3>📷 图片 (${media.images.length})</h3>
        <div class="resource-list">`;
      media.images.forEach(url => {
        html += renderItem(url, 'image');
      });
      html += `</div></div>`;
    }

    // 视频
    if (media.videos && media.videos.length > 0) {
      html += `<div class="section">
        <h3>🎬 视频 (${media.videos.length})</h3>
        <div class="resource-list">`;
      media.videos.forEach(url => {
        html += renderItem(url, 'video');
      });
      html += `</div></div>`;
    }

    // 音频
    if (media.audios && media.audios.length > 0) {
      html += `<div class="section">
        <h3>🎵 音频 (${media.audios.length})</h3>
        <div class="resource-list">`;
      media.audios.forEach(url => {
        html += renderItem(url, 'audio');
      });
      html += `</div></div>`;
    }

    if (!media.images.length && !media.videos.length && !media.audios.length) {
      html = '<div class="loading">未找到媒体资源。</div>';
    }

    contentDiv.innerHTML = html;

    // 绑定下载按钮事件
    document.querySelectorAll('.download-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const url = btn.getAttribute('data-url');
        const type = btn.getAttribute('data-type');
        downloadMedia(url, type);
      });
    });
  }

  function renderItem(url, type) {
    // 提取文件名显示简短部分
    let filename = '';
    try {
      const urlObj = new URL(url);
      let pathname = urlObj.pathname;
      filename = pathname.substring(pathname.lastIndexOf('/') + 1);
      if (!filename) filename = 'file';
    } catch (e) {
      filename = 'file';
    }
    // 截断显示
    const shortUrl = filename.length > 30 ? filename.substring(0, 27) + '...' : filename;
    return `<div class="resource-item">
      <div class="resource-url" title="${url}">${shortUrl}</div>
      <button class="download-btn" data-url="${url}" data-type="${type}">下载</button>
    </div>`;
  }

  function downloadMedia(url, type) {
    // 生成建议文件名
    let filename = '';
    try {
      const urlObj = new URL(url);
      let pathname = urlObj.pathname;
      filename = pathname.substring(pathname.lastIndexOf('/') + 1);
      if (!filename) {
        filename = `download_${Date.now()}`;
      }
    } catch (e) {
      filename = `download_${Date.now()}`;
    }

    // 向background发送下载请求
    chrome.runtime.sendMessage({ action: 'download', url: url, filename: filename }, (response) => {
      if (response && response.success) {
        console.log('下载已开始');
      } else {
        alert('下载失败: ' + (response?.error || '未知错误'));
      }
    });
  }
});
```

## 使用说明

1. 将以上所有文件放入一个文件夹（如 `media_downloader`）。
2. 打开 Chrome 浏览器，进入扩展程序管理页面 (`chrome://extensions/`)。
3. 开启“开发者模式”，点击“加载已解压的扩展程序”，选择该文件夹。
4. 插件安装后，访问任意网页，点击工具栏上的插件图标，弹出窗口将显示当前页面的媒体资源列表，点击“下载”按钮即可保存。

## 注意事项

- 插件需要 `downloads` 和 `activeTab` 权限，仅对当前激活的标签页生效。
- 由于跨域限制，部分资源可能无法直接下载，但大多数公开资源可以正常工作。
- 如果页面内容动态加载（如无限滚动），需要刷新页面或重新打开弹窗以重新扫描。
- 该插件仅检测 `<img>`、`<video>`、`<audio>` 元素及其 `<source>` 子元素，以及部分内联背景图片，不覆盖所有可能的媒体资源（如 data URL、CSS 中的背景图等）。