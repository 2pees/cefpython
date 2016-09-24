// Copyright (c) 2016 CEF Python. See the Authors and License files.

#include "download_handler.h"
#include "common/DebugLog.h"


void DownloadHandler::OnBeforeDownload(
                            CefRefPtr<CefBrowser> browser,
                            CefRefPtr<CefDownloadItem> download_item,
                            const CefString& suggested_name,
                            CefRefPtr<CefBeforeDownloadCallback> callback)
{
    REQUIRE_UI_THREAD();
    bool downloads_enabled = ApplicationSettings_GetBool("downloads_enabled");
    if (downloads_enabled) {
        std::string msg = "Browser: About to download file: ";
        msg.append(suggested_name.ToString().c_str());
        DebugLog(msg.c_str());
        callback->Continue(suggested_name, true);
    } else {
        DebugLog("Browser: Tried to download file, but downloads are disabled");
    }
}


void DownloadHandler::OnDownloadUpdated(
                                CefRefPtr<CefBrowser> browser,
                                CefRefPtr<CefDownloadItem> download_item,
                                CefRefPtr<CefDownloadItemCallback> callback)
{
    REQUIRE_UI_THREAD();
    if (download_item->IsComplete()) {
        std::string msg = "Browser: Download completed, saved to: ";
        msg.append(download_item->GetFullPath().ToString().c_str());
        DebugLog(msg.c_str());
    } else if (download_item->IsCanceled()) {
        DebugLog("Browser: Download was cancelled");
    }
}
