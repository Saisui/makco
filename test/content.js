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