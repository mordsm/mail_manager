// Background Service Worker for LLM Wiki Auto-Capture Collector
const API_URL = "http://localhost:8050/api/v1/capture/event";

async function sendToLocalVault(eventPayload) {
    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(eventPayload)
        });

        if (response.ok) {
            const resData = await response.json();
            console.log("[LLM Wiki Capture] Success:", resData);
            
            // Increment badge counter
            chrome.storage.local.get(["captureCount"], (data) => {
                const newCount = (data.captureCount || 0) + 1;
                chrome.storage.local.set({ captureCount: newCount });
                chrome.action.setBadgeText({ text: newCount.toString() });
                chrome.action.setBadgeBackgroundColor({ color: "#22c55e" });
            });
        } else {
            console.warn("[LLM Wiki Capture] Server status:", response.status);
        }
    } catch (err) {
        console.error("[LLM Wiki Capture] Connection error to localhost:8050:", err);
    }
}

// Listen for messages from content scripts or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "AUTO_CAPTURE" && message.payload) {
        sendToLocalVault(message.payload);
        sendResponse({ status: "SENT" });
    }
    return true;
});

// Capture active tab when updated
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === "complete" && tab.url && !tab.url.startsWith("chrome://")) {
        const isSupported = ["chatgpt.com", "gemini.google.com", "claude.ai", "perplexity.ai", "pubmed", "scholar"].some(d => tab.url.includes(d));
        if (isSupported) {
            sendToLocalVault({
                source_type: tab.url.includes("chatgpt") || tab.url.includes("gemini") ? "llm_chat" : "browser",
                title: tab.title || "Web Capture",
                url_or_path: tab.url,
                content: `Visited active tab: ${tab.title} (${tab.url})`,
                domain: "research"
            });
        }
    }
});

