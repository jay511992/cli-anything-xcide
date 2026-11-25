// Opt-in test adapter for programs built by the agent. Include after XCGUI.h.
// Call xc_cli_test::install(HWINDOW) on the owning UI thread before the message loop.
// No endpoint is installed without the CLI's per-run environment and private desktop.
#pragma once
#include <windows.h>
#include <string>
#pragma comment(lib, "gdi32.lib")

namespace xc_cli_test {
struct Request {
    DWORD version, operation, sequence;
    int x, y;
    DWORD key;
    wchar_t token[33];
    wchar_t text[4097];
};
static_assert(sizeof(Request) == 8284, "Unexpected test protocol packing");
static WNDPROC previous = nullptr;
static HWINDOW window = nullptr;
static HWND nativeWindow = nullptr;
static std::wstring token, directory;
static DWORD ownerThread = 0;
static HDC captureDC = nullptr;
static int captureWidth = 0, captureHeight = 0;
static bool captured = false;

static int CALLBACK paintEnd(HDRAW draw, BOOL*) {
    HDC source = XDraw_GetHDC(draw);
    if(source && captureDC) captured = BitBlt(captureDC, 0, 0, captureWidth, captureHeight, source, 0, 0, SRCCOPY) != FALSE;
    return 0;
}

static std::wstring environment(const wchar_t* name) {
    DWORD size = GetEnvironmentVariableW(name, nullptr, 0);
    if(!size || size > 32768) return {};
    std::wstring value(size, L'\0');
    DWORD written = GetEnvironmentVariableW(name, &value[0], size);
    if(!written || written >= size) return {};
    value.resize(written);
    return value;
}

static bool capture(DWORD sequence) {
    RECT rect{};
    if(!GetClientRect(nativeWindow, &rect)) return false;
    int width = rect.right, height = rect.bottom;
    if(width <= 0 || height <= 0 || width > 8192 || height > 8192 || (long long)width*height > 16777216) return false;
    BITMAPINFO bi{};
    bi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bi.bmiHeader.biWidth = width;
    bi.bmiHeader.biHeight = -height;
    bi.bmiHeader.biPlanes = 1;
    bi.bmiHeader.biBitCount = 32;
    HDC screen = GetDC(nativeWindow), dc = CreateCompatibleDC(screen);
    void* pixels = nullptr;
    HBITMAP bitmap = CreateDIBSection(screen, &bi, DIB_RGB_COLORS, &pixels, nullptr, 0);
    bool ok = false;
    if(bitmap && dc) {
        HGDIOBJ old = SelectObject(dc, bitmap);
        ZeroMemory(pixels, size_t(width)*height*4);
        if(!XC_IsEnableD2D()) {
            captureDC = dc; captureWidth = width; captureHeight = height; captured = false;
            XWnd_RegEventC(window, XWM_PAINT_END, reinterpret_cast<void*>(paintEnd));
            XWnd_Redraw(window, TRUE);
            XWnd_RemoveEventC(window, XWM_PAINT_END, reinterpret_cast<void*>(paintEnd));
            captureDC = nullptr;
            GdiFlush();
            std::wstring path = directory + L"\\capture-" + std::to_wstring(sequence) + L".bmp";
            HANDLE file = captured ? CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr) : INVALID_HANDLE_VALUE;
            if(file != INVALID_HANDLE_VALUE) {
                BITMAPFILEHEADER header{};
                header.bfType = 0x4d42;
                header.bfOffBits = sizeof(header) + sizeof(BITMAPINFOHEADER);
                DWORD bytes = DWORD(width*height*4), written;
                header.bfSize = header.bfOffBits + bytes;
                ok = WriteFile(file, &header, sizeof(header), &written, nullptr) && written == sizeof(header)
                  && WriteFile(file, &bi.bmiHeader, sizeof(BITMAPINFOHEADER), &written, nullptr) && written == sizeof(BITMAPINFOHEADER)
                  && WriteFile(file, pixels, bytes, &written, nullptr) && written == bytes;
                CloseHandle(file);
            }
        }
        SelectObject(dc, old);
    }
    if(bitmap) DeleteObject(bitmap);
    if(dc) DeleteDC(dc);
    if(screen) ReleaseDC(nativeWindow, screen);
    return ok;
}

static LRESULT CALLBACK receive(HWND hwnd, UINT message, WPARAM wp, LPARAM lp) {
    if(message == WM_COPYDATA && GetCurrentThreadId() == ownerThread) {
        auto data = reinterpret_cast<const COPYDATASTRUCT*>(lp);
        if(!data || data->dwData != 0x58435431) return CallWindowProcW(previous, hwnd, message, wp, lp);
        if(data->cbData != sizeof(Request) || !data->lpData) return 0;
        auto request = reinterpret_cast<const Request*>(data->lpData);
        if(request->version != 1 || request->token[32] != 0 || token != request->token || request->text[4096] != 0) return 0;
        if(!XC_IsHWINDOW(window)) return 0;
        if(request->operation == 1) return 0x58435431; // protocol handshake
        if(request->operation == 5) return capture(request->sequence) ? 1 : 0;
        if(request->operation == 2) {
            RECT rect{}; GetClientRect(hwnd, &rect);
            POINT point{request->x, request->y};
            if(point.x < 0 || point.y < 0 || point.x >= rect.right || point.y >= rect.bottom) return 0;
            // Native window message path, including XCGUI hit testing/dispatch.
            LPARAM xy = MAKELPARAM(point.x, point.y);
            XC_SendMessage(window, WM_MOUSEMOVE, 0, xy);
            XC_SendMessage(window, WM_LBUTTONDOWN, MK_LBUTTON, xy);
            XC_SendMessage(window, WM_LBUTTONUP, 0, xy);
            return 1;
        }
        if(request->operation == 3) {
            for(const wchar_t* c = request->text; *c; ++c) XC_SendMessage(window, WM_CHAR, *c, 1);
            return 1;
        }
        if(request->operation == 4) {
            if(request->key > 255) return 0;
            LPARAM scan = (MapVirtualKeyW(request->key, MAPVK_VK_TO_VSC) << 16) | 1;
            if(request->key == VK_DELETE || (request->key >= VK_END && request->key <= VK_DOWN)) scan |= 1 << 24;
            XC_SendMessage(window, WM_KEYDOWN, request->key, scan);
            if(request->key == VK_RETURN || request->key == VK_TAB || request->key == VK_BACK || request->key == VK_SPACE)
                XC_SendMessage(window, WM_CHAR, request->key, scan);
            XC_SendMessage(window, WM_KEYUP, request->key, scan | 0xc0000000);
            return 1;
        }
        return 0;
    }
    return CallWindowProcW(previous, hwnd, message, wp, lp);
}

static bool install(HWINDOW selected) {
    token = environment(L"CLI_ANYTHING_XCIDE_TEST_TOKEN");
    directory = environment(L"CLI_ANYTHING_XCIDE_TEST_DIR");
    if(token.size() != 32 || directory.empty() || previous || !XC_IsHWINDOW(selected)) return false;
    wchar_t desktop[128]{}; DWORD needed = 0;
    if(!GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()), UOI_NAME, desktop, sizeof(desktop), &needed)
       || std::wstring(desktop) != L"xcide-test-" + token) return false;
    window = selected; nativeWindow = XWnd_GetHWND(window);
    if(!nativeWindow || GetWindowThreadProcessId(nativeWindow, nullptr) != GetCurrentThreadId()) return false;
    ownerThread = GetCurrentThreadId();
    previous = reinterpret_cast<WNDPROC>(SetWindowLongPtrW(nativeWindow, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(receive)));
    return previous != nullptr;
}
}
