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