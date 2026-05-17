// Service worker: opens the print page in a new tab on request from the content script.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message && message.type === "open-print" && typeof message.key === "string") {
    const url = chrome.runtime.getURL(`print/print.html#${encodeURIComponent(message.key)}`);
    chrome.tabs.create({ url }, (tab) => {
      sendResponse({ ok: true, tabId: tab && tab.id });
    });
    return true;
  }
  return false;
});
