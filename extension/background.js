chrome.tabs.onUpdated.addListener((tabId, tab) => {
    if (tab.url && tab.url.includes("futbin.com/squad-builder")) {
    }
})
