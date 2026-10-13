document.addEventListener("DOMContentLoaded", () => {
  const countEl = document.getElementById("count");
  const captureBtn = document.getElementById("captureBtn");

  chrome.storage.local.get(["captureCount"], (data) => {
    countEl.textContent = data.captureCount || 0;
  });

  captureBtn.addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        const tab = tabs[0];
        chrome.runtime.sendMessage({
          action: "AUTO_CAPTURE",
          payload: {
            source_type: "manual",
            title: tab.title || "Manual Capture",
            url_or_path: tab.url,
            content: `Manual page bookmark/capture: ${tab.title} (${tab.url})`,
            domain: "research"
          }
        }, () => {
          captureBtn.textContent = "✓ Captured!";
          setTimeout(() => { captureBtn.textContent = "📌 Capture Current Page"; }, 2000);
        });
      }
    });
  });
});

