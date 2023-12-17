function injectScript(tabId) {
  chrome.scripting.executeScript({
    target: { tabId: tabId },
    files: ["inject.js"],
  });
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  injectScript(tabId);
});
