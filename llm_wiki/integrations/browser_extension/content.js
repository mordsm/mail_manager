// Content script for LLM Wiki Auto-Capture Collector
(function() {
    let lastSentHash = "";

    function extractPageContent() {
        const title = document.title || "Untitled Page";
        const url = window.location.href;

        let content = "";
        
        // Extract main text or conversation elements
        if (url.includes("chatgpt.com")) {
            const turns = Array.from(document.querySelectorAll("[data-message-author-role], .aria-label, article"));
            if (turns.length > 0) {
                content = turns.map(el => el.innerText.trim()).filter(Boolean).join("\n---\n");
            }
        } else if (url.includes("gemini.google.com")) {
            const turns = Array.from(document.querySelectorAll("user-query, model-response, .query-text, .response-text-content"));
            if (turns.length > 0) {
                content = turns.map(el => el.innerText.trim()).filter(Boolean).join("\n---\n");
            }
        }

        if (!content || content.length < 20) {
            content = document.body ? document.body.innerText.substring(0, 3000) : "";
        }

        return { title, url, content };
    }

    function sendCapture() {
        const data = extractPageContent();
        if (!data.content || data.content.length < 10) return;

        const currentHash = data.url + ":" + data.content.substring(0, 100);
        if (currentHash === lastSentHash) return;
        lastSentHash = currentHash;

        chrome.runtime.sendMessage({
            action: "AUTO_CAPTURE",
            payload: {
                source_type: data.url.includes("chatgpt") || data.url.includes("gemini") || data.url.includes("claude") ? "llm_chat" : "browser",
                title: data.title,
                url_or_path: data.url,
                content: data.content.substring(0, 5000),
                domain: "research",
                time_spent_seconds: 30
            }
        });
    }

    // Initial capture after load
    setTimeout(sendCapture, 3000);

    // Periodic capture every 30 seconds if page content changes
    setInterval(sendCapture, 30000);
})();

