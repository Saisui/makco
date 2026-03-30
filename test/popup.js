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