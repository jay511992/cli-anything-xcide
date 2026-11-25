// Minimal XCIDE v3 output reader. Loaded ONLY by the CLI's private IDE copy.
// ABI: official plug_test/plug.h data_getHELE_, data_getProject_, OnInitPlug.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
#include <vector>

struct GetElement { int type; int id; void* element; };
struct GetProject { int type; const wchar_t* name; const wchar_t* path;
    const wchar_t* directory; const wchar_t* config; int load; BOOL zip; BOOL x64; };
using Set = int (*)(void*);
using Length = int (WINAPI*)(void*);
using Text = int (WINAPI*)(void*, wchar_t*, int);
using IsElement = BOOL (WINAPI*)(void*);
using GetHWND = HWND (WINAPI*)(void*);
static Set setter = nullptr;
static Length getLength = nullptr;
static Text getText = nullptr;
static IsElement isElement = nullptr;
static HWND mainWindow = nullptr;
static UINT_PTR timer = 0;
static std::wstring target;
static std::string previous;
static int version = 0;

static std::string utf8(const std::wstring& value) {
    int n = WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), nullptr, 0, nullptr, nullptr);
    std::string result(n, 0);
    if(n) WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), &result[0], n, nullptr, nullptr);
    return result;
}
static std::string quote(const std::wstring& value) {
    std::string result = "\"";
    for (unsigned char ch : utf8(value)) {
        if(ch == '"' || ch == '\\') { result += '\\'; result += ch; }
        else if(ch < 32) { char esc[7]; wsprintfA(esc, "\\u%04x", ch); result += esc; }
        else result += ch;
    }
    return result + "\"";
}
static void writeSnapshot(const std::string& content) {
    if(content == previous) return;
    std::wstring pending = target + L".pending";
    HANDLE f = CreateFileW(pending.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if(f == INVALID_HANDLE_VALUE) return;
    DWORD written = 0;
    BOOL ok = WriteFile(f, content.data(), (DWORD)content.size(), &written, nullptr);
    CloseHandle(f);
    if(ok && written == content.size() && MoveFileExW(pending.c_str(), target.c_str(), MOVEFILE_REPLACE_EXISTING)) previous = content;
}
static void CALLBACK tick(HWND, UINT, UINT_PTR, DWORD) {
    if(!setter || !IsWindow(mainWindow) || !IsWindowVisible(mainWindow)) return;
    GetElement output = {6, 1101, nullptr};
    setter(&output);
    GetProject project = {}; project.type = 8; setter(&project);
    int length = output.element && isElement(output.element) ? getLength(output.element) : -1;
    bool truncated = length > 2 * 1024 * 1024;
    std::wstring text;
    if(length >= 0 && !truncated) {
        std::vector<wchar_t> buffer((size_t)length + 2, 0);
        getText(output.element, buffer.data(), (int)buffer.size());
        text.assign(buffer.data());
    }
    std::string json = "{\"pid\":" + std::to_string(GetCurrentProcessId()) +
        ",\"version\":" + std::to_string(version) +
        ",\"ui_thread\":" + std::to_string(GetCurrentThreadId()) +
        ",\"ready\":" + (length >= 0 ? "true" : "false") +
        ",\"truncated\":" + (truncated ? "true" : "false") +
        ",\"project\":" + quote(project.path ? project.path : L"") +
        ",\"text\":" + quote(text) + "}";
    writeSnapshot(json);
}
extern "C" __declspec(dllexport) BOOL OnInitPlug(Set fun, void* mainFrame, int ver) {
    wchar_t path[32768];
    DWORD n = GetEnvironmentVariableW(L"CLI_ANYTHING_XCIDE_OUTPUT", path, 32768);
    if(!n || n >= 32768 || ver != 3) return FALSE;
    HMODULE xc = GetModuleHandleW(L"XCGUI.dll");
    getLength = (Length)GetProcAddress(xc, "XEdit_GetLength");
    getText = (Text)GetProcAddress(xc, "XEdit_GetText");
    isElement = (IsElement)GetProcAddress(xc, "XC_IsHELE");
    auto isWindow = (IsElement)GetProcAddress(xc, "XC_IsHWINDOW");
    auto getHWND = (GetHWND)GetProcAddress(xc, "XWnd_GetHWND");
    if(!getLength || !getText || !isElement || !isWindow || !getHWND || !isWindow(mainFrame)) return FALSE;
    mainWindow = getHWND(mainFrame);
    if(!IsWindow(mainWindow)) return FALSE;
    target.assign(path, n); setter = fun; version = ver;
    // OnInitPlug runs on the IDE UI thread. A thread timer reads the edit on
    // that same thread; no worker dereferences XCGUI objects across threads.
    timer = SetTimer(mainWindow, 0x58434C49, 150, tick);
    return timer != 0;
}
extern "C" __declspec(dllexport) BOOL OnExitPlug() {
    if(timer) KillTimer(mainWindow, timer);
    timer = 0; setter = nullptr;
    return TRUE;
}
