# 修改文件名格式为“日期 - 标题 - 网址.扩展名”

在现有插件基础上，修改 `popup.js`，使下载文件名按照 `YYYY-MM-DD - 页面标题 - 域名.扩展名` 格式生成，并自动清理非法字符。

## 修改文件

### `popup.js`
```diff MODIFY: popup.js
 document.addEventListener('DOMContentLoaded', () => {
   const contentDiv = document.getElementById('content');
+  let currentTab = null; // 保存当前标签页信息
  
   // 获取当前活动标签页
   chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
     const tab = tabs[0];
     if (!tab) {
       contentDiv.innerHTML = '<div class="error">无法获取当前页面</div>';
       return;
     }
+    currentTab = tab; // 保存以便下载时使用
  
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
     // ... (中间代码保持不变) ...
  
     // 绑定下载按钮事件
     document.querySelectorAll('.download-btn').forEach(btn => {
       btn.addEventListener('click', (e) => {
         const url = btn.getAttribute('data-url');
         const type = btn.getAttribute('data-type');
-        downloadMedia(url, type);
+        downloadMedia(url, type, currentTab);
       });
     });
   }
  
-  function downloadMedia(url, type) {
-    // 生成建议文件名
-    let filename = '';
-    try {
-      const urlObj = new URL(url);
-      let pathname = urlObj.pathname;
-      filename = pathname.substring(pathname.lastIndexOf('/') + 1);
-      if (!filename) {
-        filename = `download_${Date.now()}`;
-      }
-    } catch (e) {
-      filename = `download_${Date.now()}`;
-    }
+  // 生成格式化文件名: 日期 - 标题 - 域名.扩展名
+  function generateFilename(mediaUrl, pageTitle, pageUrl) {
+    // 1. 日期: YYYY-MM-DD
+    const now = new Date();
+    const year = now.getFullYear();
+    const month = String(now.getMonth() + 1).padStart(2, '0');
+    const day = String(now.getDate()).padStart(2, '0');
+    const datePart = `${year}-${month}-${day}`;
+    
+    // 2. 标题: 清理非法字符，过长则截断（可选，这里保留原样但替换非法字符）
+    let titlePart = pageTitle || '无标题';
+    titlePart = titlePart.replace(/[/\\:*?"<>|]/g, '_').trim();
+    if (titlePart.length > 50) titlePart = titlePart.substring(0, 50);
+    
+    // 3. 网址: 提取域名（hostname），清理非法字符（一般安全，但以防万一）
+    let domainPart = '';
+    try {
+      const urlObj = new URL(pageUrl);
+      domainPart = urlObj.hostname;
+    } catch (e) {
+      domainPart = 'unknown';
+    }
+    domainPart = domainPart.replace(/[/\\:*?"<>|]/g, '_');
+    
+    // 4. 扩展名: 从媒体URL中提取
+    let ext = '';
+    try {
+      const urlObj = new URL(mediaUrl);
+      const pathname = urlObj.pathname;
+      const lastDot = pathname.lastIndexOf('.');
+      if (lastDot !== -1 && lastDot < pathname.length - 1) {
+        ext = pathname.substring(lastDot + 1).split('?')[0]; // 去掉查询参数
+        ext = ext.toLowerCase();
+      }
+    } catch (e) {
+      ext = '';
+    }
+    if (!ext) ext = 'bin'; // 默认扩展名
+    
+    // 5. 拼接并清理文件名中的多余空格
+    let filename = `${datePart} - ${titlePart} - ${domainPart}.${ext}`;
+    // 替换多个空格为单个空格，并去除首尾空格
+    filename = filename.replace(/\s+/g, ' ').trim();
+    return filename;
+  }
+  
+  function downloadMedia(url, type, tab) {
+    if (!tab) {
+      alert('无法获取页面信息');
+      return;
+    }
+    const filename = generateFilename(url, tab.title, tab.url);
  
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

## 修改说明

1. **保存当前标签页**：在获取到 `tab` 后将其保存在全局变量 `currentTab` 中，供下载函数使用。
2. **新增 `generateFilename` 函数**：按照指定格式生成文件名，包含日期、页面标题、域名和扩展名，并清理非法字符。
   - 日期格式为 `YYYY-MM-DD`。
   - 标题若超过50字符则截断，并替换 Windows 非法字符。
   - 域名从当前页面 URL 的 `hostname` 提取。
   - 扩展名从媒体 URL 的路径末尾提取，若没有则默认 `bin`。
   - 最终文件名中多余空格会被压缩。
3. **修改 `downloadMedia` 调用**：增加 `tab` 参数，使用新的文件名生成逻辑。

## 使用效果

下载一个图片时，假设页面标题为“示例网站 - 首页”，域名为 `example.com`，媒体 URL 为 `https://example.com/image.jpg`，日期为 2026-03-30，则文件名类似：
```
2026-03-30 - 示例网站 - 首页 - example.com.jpg
```