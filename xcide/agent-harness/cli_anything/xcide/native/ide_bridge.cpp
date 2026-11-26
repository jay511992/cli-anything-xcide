// XCIDE ABI-v3 bridge, hosted only in a CLI-owned private desktop.
// No sockets, HTTP, MCP, external plugin dependency or foreground input.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <stdexcept>
#include <cstring>

using Setter = int (*)(void*);
struct Data { int type = 0, id = 0; void* v[31] = {}; };
// From current official plug_test/plug.h, including lineno_end and pVarType.
struct Symbol { int type, line, end, col1, col2, depth;
    const wchar_t *name, *alias, *varType, *parentClass, *parentVar, *file; };
using Args = std::map<std::wstring, std::wstring>;
static Setter setter;
static HMODULE xc;
static HWND window;
static UINT_PTR timer;
static std::wstring directory, token;
static bool ready = false, verifiedParse = false, restoreKeys = false;
static unsigned working = 0, requestSequence = 0;
static BYTE previousKeys[256];
static ULONGLONG restoreAt;
static std::set<std::wstring> opened;

template<typename F> F api(const char* name) {
    auto value = GetProcAddress(xc, name);
    if (!value) throw std::runtime_error(std::string("Missing XCGUI export: ") + name);
    return reinterpret_cast<F>(value);
}
static int invoke(Data& data) {
    __try { return setter(&data); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return -2147483647; }
}
static bool measureWide(const wchar_t* p, size_t limit, size_t* length) {
    __try {
        *length = 0;
        while (*length < limit && p[*length]) ++*length;
        return *length < limit;
    } __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}
static bool copyWide(wchar_t* out, const wchar_t* p, size_t length) {
    __try { memcpy(out, p, length * sizeof(wchar_t)); return true; }
    __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}
static std::wstring wide(const wchar_t* p, size_t limit = 2097152) {
    if (!p) return L"";
    // Borrowed pointers are copied on the UI thread, with a bounded SEH guard.
    size_t length;
    if (!measureWide(p, limit, &length)) throw std::runtime_error("Invalid or oversized native text");
    std::wstring text(length, 0);
    if (length && !copyWide(&text[0], p, length)) throw std::runtime_error("Native text became unavailable");
    return text;
}
static std::string q(const std::wstring& value) {
    int n = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), (int)value.size(), nullptr, 0, nullptr, nullptr);
    if (!n && !value.empty()) throw std::runtime_error("Invalid UTF-16 in native text");
    std::string utf8(n, 0), result = "\"";
    if (n) WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), (int)value.size(), &utf8[0], n, nullptr, nullptr);
    for (unsigned char ch : utf8) {
        if (ch == '"' || ch == '\\') { result += '\\'; result += ch; }
        else if (ch < 32) { char esc[7]; sprintf_s(esc, "\\u%04x", ch); result += esc; }
        else result += ch;
    }
    return result + "\"";
}
static std::string error(const std::wstring& text) { return "{\"ok\":false,\"error\":" + q(text) + "}"; }
static std::wstring arg(const Args& a, const wchar_t* key, const wchar_t* fallback = L"") {
    auto it = a.find(key); return it == a.end() ? fallback : it->second;
}
static int number(const Args& a, const wchar_t* key, int def = 0) {
    auto it = a.find(key); return it == a.end() ? def : std::stoi(it->second);
}
static void writeFile(const std::wstring& name, const std::string& body) {
    auto path = directory + L"\\" + name, temporary = path + L".tmp";
    HANDLE f = CreateFileW(temporary.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) return;
    DWORD written = 0;
    BOOL ok = WriteFile(f, body.data(), (DWORD)body.size(), &written, nullptr);
    CloseHandle(f);
    if (ok && written == body.size()) MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING);
}
static void* element(int id) {
    Data d; d.type = 6; d.id = id; invoke(d);
    return d.v[0] && api<BOOL(WINAPI*)(void*)>("XC_IsHELE")(d.v[0]) ? d.v[0] : nullptr;
}
static std::wstring editText(void* h) {
    if (!h || !api<BOOL(WINAPI*)(void*)>("XC_IsHELE")(h)) throw std::runtime_error("Code editor unavailable");
    int n = api<int(WINAPI*)(void*)>("XEdit_GetLength")(h);
    if (n < 0 || n > 2097152) throw std::runtime_error("Editor text length outside limit");
    std::vector<wchar_t> text((size_t)n + 2, 0);
    api<int(WINAPI*)(void*, wchar_t*, int)>("XEdit_GetText")(h, text.data(), (int)text.size());
    return wide(text.data());
}
static Data editor(const std::wstring& path) {
    Data d; d.type = 16; if (!path.empty()) d.v[0] = (void*)path.c_str();
    invoke(d); return d;
}
static std::string project() {
    Data d; d.type = 8; invoke(d);
    if (!d.v[1]) return error(L"IDE 尚未加载工程");
    return "{\"ok\":true,\"name\":" + q(wide((wchar_t*)d.v[0])) +
        ",\"project_file\":" + q(wide((wchar_t*)d.v[1])) + ",\"dir\":" + q(wide((wchar_t*)d.v[2])) +
        ",\"config\":" + q(wide((wchar_t*)d.v[3])) + "}";
}
static std::string readEditor(const Args& a) {
    std::wstring path = arg(a, L"path");
    Data d = editor(path);
    if (!d.v[1]) return error(L"取不到已打开的代码编辑器");
    path = wide((wchar_t*)d.v[0]);
    opened.insert(path);
    auto text = editText(d.v[1]);
    return "{\"ok\":true,\"file\":" + q(path) + ",\"text\":" + q(text) +
        ",\"length\":" + std::to_string(text.size()) + ",\"rows\":" +
        std::to_string(api<int(WINAPI*)(void*)>("XEdit_GetRowCount")(d.v[1])) + "}";
}
static int importFile(const std::wstring& path, bool open) {
    Data d; d.type = 12; d.v[0] = (void*)path.c_str(); d.v[1] = (void*)(uintptr_t)open;
    int result = invoke(d);
    if (result > 0 && open) opened.insert(path);
    return result;
}
static std::string symbol(const Args& a, bool go) {
    auto name = arg(a, L"name"), path = arg(a, L"path");
    Data d; d.type = path.empty() ? 3 : 4;
    d.id = number(a, L"lineno");
    if (path.empty()) d.v[0] = name.empty() ? nullptr : (void*)name.c_str();
    else { d.v[0] = (void*)path.c_str(); d.v[1] = name.empty() ? nullptr : (void*)name.c_str(); }
    if (invoke(d) <= 0) return error(L"IDE 中未找到符号；请先打开文件并等待解析");
    Symbol s = {}; memcpy(&s, &d.v[path.empty() ? 1 : 2], sizeof(s));
    auto file = wide(s.file), symbolName = wide(s.name), alias = wide(s.alias);
    std::string out = "{\"ok\":true,\"symbol_type\":" + std::to_string(s.type) +
        ",\"lineno\":" + std::to_string(s.line) + ",\"lineno_end\":" + std::to_string(s.end) +
        ",\"col1\":" + std::to_string(s.col1) + ",\"col2\":" + std::to_string(s.col2) +
        ",\"file\":" + q(file) + ",\"name\":" + q(symbolName) + ",\"alias\":" + q(alias);
    if (go) {
        bool moved = false;
        if (!file.empty() && s.line >= 0) {
            importFile(file, true);
            Data view = editor(file);
            if (view.v[1] && wide((wchar_t*)view.v[0]) == file)
                moved = api<BOOL(WINAPI*)(void*, int, int)>("XEdit_SetCurPosEx")(view.v[1], s.line, std::max(0, s.col1)) != FALSE;
        }
        out += std::string(",\"moved\":") + (moved ? "true" : "false");
    }
    return out + "}";
}
static bool parseCounter(int& count, bool reset) {
    if (!verifiedParse) return false;
    auto host = (unsigned char*)GetModuleHandleW(nullptr);
    auto dos = (IMAGE_DOS_HEADER*)host;
    auto nt = (IMAGE_NT_HEADERS64*)(host + dos->e_lfanew);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || nt->Signature != IMAGE_NT_SIGNATURE ||
        nt->OptionalHeader.SizeOfImage < 0x4B83F0) return false;
    MEMORY_BASIC_INFORMATION m = {};
    int* address = (int*)(host + 0x4B83EC);
    if (!VirtualQuery(address, &m, sizeof(m)) || m.State != MEM_COMMIT ||
        (m.Protect != PAGE_READWRITE && m.Protect != PAGE_WRITECOPY)) return false;
    count = *address;
    if (reset) *address = 0;
    return true;
}
static bool postKey(int key, bool ctrl) {
    if (restoreKeys) return false;
    if (ctrl) {
        BYTE keys[256];
        if (!GetKeyboardState(previousKeys)) return false;
        memcpy(keys, previousKeys, sizeof(keys)); keys[VK_CONTROL] |= 0x80;
        if (!SetKeyboardState(keys)) return false;
        restoreKeys = true; restoreAt = GetTickCount64() + 350;
    }
    return PostMessageW(window, WM_KEYDOWN, key, 1) && PostMessageW(window, WM_KEYUP, key, 0xC0000001);
}

// Read only windows owned by this IDE UI thread. Never read a foreign thread's
// XCGUI objects or send pointers into an unbounded cross-thread window call.
static std::wstring nativeText(HWND h, int maximum) {
    std::vector<wchar_t> buffer((size_t)maximum + 1, 0);
    SendMessageW(h, WM_GETTEXT, buffer.size(), (LPARAM)buffer.data());
    return wide(buffer.data(), buffer.size());
}
static void append(std::wstring& out, const std::wstring& text, size_t limit) {
    if (text.empty() || out.size() >= limit) return;
    if (!out.empty()) out += L"\n";
    out += text.substr(0, limit - std::min(limit, out.size()));
    if (!out.empty() && out.back() >= 0xd800 && out.back() <= 0xdbff) out.pop_back();
}
// XMsg paints its body directly. Verified layout reference: XC-MCP-Next's
// dialogs.cpp, PE signature + code bytes + object identity all required.
static bool xmsgBody(void* root, HWND hwnd, wchar_t* output, size_t limit) {
    __try {
        auto base = (unsigned char*)xc;
        auto dos = (IMAGE_DOS_HEADER*)base;
        auto pe = (IMAGE_NT_HEADERS64*)(base + dos->e_lfanew);
        if (pe->FileHeader.TimeDateStamp != 0x69DD049C || pe->OptionalHeader.SizeOfImage != 0x3A3000) return false;
        auto type = (unsigned char*)GetProcAddress(xc, "XObj_GetType");
        const unsigned char expected[] = {0x48,0x63,0x05,0xA9,0x16,0x32,0x00,0x8B,0xD1,0x48,0x3B,0xD0,0x7C,0x26,
            0x48,0x63,0x05,0x9F,0x16,0x32,0x00,0x48,0x3B,0xD0,0x7D,0x1A,0x48,0x8B,0x05,0x87,0x16,0x32,0x00};
        if (!type || memcmp(type, expected, sizeof(expected))) return false;
        auto index = (uintptr_t)root;
        DWORD low = *(DWORD*)(base + 0x33A5D0), high = *(DWORD*)(base + 0x33A5D4);
        if (low > high || high > 0x100000 || index < low || index >= high) return false;
        auto objects = *(unsigned char***)(base + 0x33A5C8);
        auto object = objects[index];
        if (!object || *(uintptr_t*)object != (uintptr_t)base + 0x2DBA68 ||
            *(uintptr_t*)(object + 200) != index || *(HWND*)(object + 208) != hwnd) return false;
        auto length = *(size_t*)(object + 864), capacity = *(size_t*)(object + 872);
        if (length > capacity || capacity > 131072) return false;
        auto text = capacity >= 8 ? *(const wchar_t**)(object + 848) : (wchar_t*)(object + 848);
        size_t copied = std::min(length, limit - 1);
        memcpy(output, text, copied * sizeof(wchar_t)); output[copied] = 0;
        return true;
    } __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}
struct DialogScan { std::string entries; int limit, count = 0; bool partial = false; };
static BOOL CALLBACK childText(HWND h, LPARAM p) {
    auto out = (std::wstring*)p;
    wchar_t name[64] = {}; GetClassNameW(h, name, 64);
    if (IsWindowVisible(h) && (wcscmp(name, L"Static") == 0 || wcscmp(name, L"Edit") == 0))
        append(*out, nativeText(h, 16384), 65536);
    return out->size() < 65536;
}
static BOOL CALLBACK dialogWindow(HWND h, LPARAM p) {
    auto& scan = *(DialogScan*)p;
    DWORD pid = 0;
    if (h == window || !IsWindowVisible(h) || GetWindowThreadProcessId(h, &pid) != GetCurrentThreadId() || pid != GetCurrentProcessId()) return TRUE;
    if (scan.count >= 32) { scan.partial = true; return FALSE; }
    wchar_t cls[128] = {}; GetClassNameW(h, cls, 128);
    std::wstring text, title;
    bool recognized = false, bodyAvailable = true;
    try {
        if (wcscmp(cls, L"#32770") == 0) {
            recognized = true; title = nativeText(h, 1024);
            EnumChildWindows(h, childText, (LPARAM)&text);
        } else {
            void* root = api<void*(WINAPI*)(HWND)>("XC_hWindowFromHWnd")(h);
            auto kind = api<int(WINAPI*)(void*)>("XObj_GetType");
            if (!root || (kind(root) != 2 && !(kind(root) == 1 && GetWindow(h, GW_OWNER) && !IsWindowEnabled(GetWindow(h, GW_OWNER))))) return TRUE;
            recognized = true; title = wide(api<const wchar_t*(WINAPI*)(void*)>("XWnd_GetTitle")(root), 4096);
            std::vector<void*> nodes; std::set<void*> seen;
            int n = api<int(WINAPI*)(void*)>("XWnd_GetChildCount")(root);
            if (n < 0 || n > 2048) throw std::runtime_error("Dialog node limit");
            for (int i = 0; i < n; ++i) nodes.push_back(api<void*(WINAPI*)(void*, int)>("XWnd_GetChildByIndex")(root, i));
            while (!nodes.empty() && seen.size() < 2048) {
                void* node = nodes.back(); nodes.pop_back();
                if (!node || !seen.insert(node).second || !api<BOOL(WINAPI*)(void*)>("XWidget_IsShow")(node)) continue;
                int type = kind(node);
                if (type == 62) append(text, wide(api<const wchar_t*(WINAPI*)(void*)>("XShapeText_GetText")(node)), scan.limit);
                else if (type == 45 && api<BOOL(WINAPI*)(void*)>("XEdit_IsReadOnly")(node)) append(text, editText(node), scan.limit);
                if (api<int(WINAPI*)(void*)>("XObj_GetTypeBase")(node) == 21 && type != 22 && type != 45) {
                    int count = api<int(WINAPI*)(void*)>("XEle_GetChildCount")(node);
                    if (count < 0 || count + nodes.size() + seen.size() > 2048) throw std::runtime_error("Dialog node limit");
                    for (int i = 0; i < count; ++i) nodes.push_back(api<void*(WINAPI*)(void*, int)>("XEle_GetChildByIndex")(node, i));
                }
            }
            if (text.empty()) {
                std::vector<wchar_t> body((size_t)scan.limit + 1, 0);
                bodyAvailable = xmsgBody(root, h, body.data(), body.size());
                if (bodyAvailable) text = body.data();
            }
        }
    } catch (...) { scan.partial = true; bodyAvailable = false; }
    if (!recognized) return TRUE;
    if (!scan.entries.empty()) scan.entries += ',';
    if (text.size() > (size_t)scan.limit) { text.resize(scan.limit); scan.partial = true; }
    if (!text.empty() && text.back() >= 0xd800 && text.back() <= 0xdbff) text.pop_back();
    scan.entries += "{\"hwnd\":" + std::to_string((uintptr_t)h) + ",\"title\":" + q(title) +
        ",\"text\":" + q(text) + ",\"body_available\":" + (bodyAvailable ? "true" : "false") + "}";
    ++scan.count; return TRUE;
}

static std::string execute(const std::wstring& method, const Args& a) {
    if (method == L"status") return "{\"ok\":true,\"server\":\"cli-anything-xcide\",\"transport\":\"local-files/native-abi\",\"mcp\":false,\"abi\":3,\"pid\":" +
        std::to_string(GetCurrentProcessId()) + ",\"ui_thread\":" + std::to_string(GetCurrentThreadId()) +
        ",\"parse_count_supported\":" + (verifiedParse ? "true" : "false") + "}";
    if (method == L"project") return project();
    if (method == L"editor") return readEditor(a);
    if (method == L"output") return "{\"ok\":true,\"text\":" + q(editText(element(1101))) + "}";
    if (method == L"log") {
        auto text = arg(a, L"text"); Data d; d.type = 2; d.v[0] = (void*)text.c_str(); invoke(d);
        return "{\"ok\":true}";
    }
    if (method == L"import") {
        auto path = arg(a, L"path"); int rc = importFile(path, number(a, L"open", 1) != 0);
        return std::string("{\"ok\":") + (rc > 0 ? "true" : "false") + ",\"rc\":" + std::to_string(rc) + ",\"path\":" + q(path) + "}";
    }
    if (method == L"symbol" || method == L"goto") return symbol(a, method == L"goto");
    if (method == L"parse" || method == L"reset-parse") {
        int count = 0;
        if (!parseCounter(count, method == L"reset-parse")) return error(L"此 IDE 映像未通过解析计数器版本门禁；未读取或写入固定偏移");
        return "{\"ok\":true,\"count\":" + std::to_string(method == L"parse" ? count : 0) +
            ",\"before\":" + std::to_string(count) + ",\"parsing\":" + (method == L"parse" && count > 0 ? "true" : "false") + "}";
    }
    if (method == L"module-info") {
        auto path = arg(a, L"path"), name = arg(a, L"name"), module = arg(a, L"module"), author = arg(a, L"author");
        Data d; d.type = 17; d.v[0] = path.empty() ? nullptr : (void*)path.c_str(); d.v[1] = name.empty() ? nullptr : (void*)name.c_str();
        d.v[2] = module.empty() ? nullptr : (void*)module.c_str(); d.v[3] = author.empty() ? nullptr : (void*)author.c_str();
        if (invoke(d) <= 0) return error(L"IDE 未找到该模块");
        const char* keys[] = {"path", "file", "module", "alias", "version", "date", "remark", "md5", "qq"};
        std::string out = "{\"ok\":true";
        for (int i = 0; i < 9; ++i) out += std::string(",\"") + keys[i] + "\":" + q(wide((wchar_t*)d.v[i]));
        return out + "}";
    }
    if (method == L"menu" || method == L"save") {
        auto command = arg(a, L"command", L"compile");
        bool control = method == L"save" || command != L"compile";
        bool sent = postKey(method == L"save" ? 'S' : control ? VK_F5 : VK_F7, control);
        return std::string("{\"ok\":") + (sent ? "true" : "false") +
            ",\"status\":" + (sent ? "\"dispatched\"" : "\"not_dispatched\"") +
            ",\"compiled\":null,\"saved\":null,\"channel\":\"private-ui-thread-key\"}";
    }
    if (method == L"dialogs") {
        DialogScan scan; scan.limit = std::max(128, std::min(65536, number(a, L"maxChars", 16000)));
        EnumThreadWindows(GetCurrentThreadId(), dialogWindow, (LPARAM)&scan);
        return "{\"ok\":true,\"count\":" + std::to_string(scan.count) + ",\"dialogs\":[" + scan.entries +
            "],\"partial\":" + (scan.partial ? "true" : "false") + "}";
    }
    if (method == L"probe") {
        int cmd = number(a, L"cmd_id");
        if (cmd < 1 || cmd > 21) return error(L"ABI 命令号范围为 1..21");
        if (cmd != 20 && cmd != 21 && (arg(a, L"allow_unsafe") != L"1" || arg(a, L"confirm") != L"I-UNDERSTAND-THE-RISK"))
            return error(L"该 ABI 探测可能终止私有 IDE，需 allow_unsafe 与明确 confirm");
        Data d; d.type = cmd; d.id = number(a, L"arg0"); int rc = invoke(d);
        return std::string("{\"ok\":") + (rc == -2147483647 ? "false" : "true") + ",\"rc\":" + std::to_string(rc) + "}";
    }
    return error(L"未知原生桥接操作");
}

static void processRequest(bool diagnosticsOnly) {
    auto incoming = directory + L"\\request.bin", claimed = directory + L"\\working-" + std::to_wstring(++requestSequence) + L".bin";
    if (!MoveFileExW(incoming.c_str(), claimed.c_str(), MOVEFILE_REPLACE_EXISTING)) return;
    HANDLE f = CreateFileW(claimed.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) return;
    DWORD n = GetFileSize(f, nullptr), got = 0;
    std::vector<unsigned char> raw;
    if (n >= 20 && n <= 8 * 1024 * 1024) { raw.resize(n); if (!ReadFile(f, raw.data(), n, &got, nullptr)) raw.clear(); }
    CloseHandle(f);
    std::wstring id;
    try {
        if (raw.size() < 20 || got != raw.size() || memcmp(raw.data(), "XCIDE02\0", 8)) throw std::runtime_error("Malformed frame");
        ULONGLONG deadline; DWORD count;
        memcpy(&deadline, raw.data() + 8, 8); memcpy(&count, raw.data() + 16, 4);
        if (count < 3 || count > 67 || count % 2 != 1) throw std::runtime_error("Malformed field count");
        size_t at = 20; std::vector<std::wstring> fields;
        for (DWORD i = 0; i < count; ++i) {
            DWORD size;
            if (at + 4 > raw.size()) throw std::runtime_error("Truncated field");
            memcpy(&size, raw.data() + at, 4); at += 4;
            if (size % 2 || at + size > raw.size()) throw std::runtime_error("Truncated string");
            std::wstring value(size / 2, 0);
            if (size) memcpy(&value[0], raw.data() + at, size);
            if (value.find(L'\0') != std::wstring::npos) throw std::runtime_error("NUL in field");
            fields.push_back(std::move(value)); at += size;
        }
        if (at != raw.size() || fields[0] != token || fields[1].size() != 32 || fields[1].find_first_not_of(L"0123456789abcdef") != std::wstring::npos)
            throw std::runtime_error("Invalid request identity");
        id = fields[1]; Args args;
        for (size_t i = 3; i < fields.size(); i += 2) {
            if (!args.emplace(fields[i], fields[i+1]).second) throw std::runtime_error("Duplicate argument");
        }
        // A synchronous ABI call can enter a modal loop. Allow bounded reads
        // there so an agent can diagnose it after its original call times out.
        bool permitted = !diagnosticsOnly || fields[2] == L"dialogs" || fields[2] == L"status" || fields[2] == L"output";
        std::string result = GetTickCount64() >= deadline ? error(L"请求已过期；未执行") :
            !permitted ? error(L"IDE 正在处理上次操作；仅允许 status/dialogs/output 诊断") : execute(fields[2], args);
        if (result.size() > 8 * 1024 * 1024 - 512) result = error(L"原生响应超过 8 MiB；请缩小输入或输出范围");
        writeFile(L"response-" + id + L".json", "{\"id\":" + q(id) + ",\"token\":" + q(token) +
                  ",\"pid\":" + std::to_string(GetCurrentProcessId()) + ",\"result\":" + result + "}");
    } catch (const std::exception& e) {
        if (!id.empty()) {
            std::string msg = e.what();
            writeFile(L"response-" + id + L".json", "{\"id\":" + q(id) + ",\"token\":" + q(token) +
                ",\"pid\":" + std::to_string(GetCurrentProcessId()) + ",\"result\":" + error(std::wstring(msg.begin(), msg.end())) + "}");
        }
    }
    DeleteFileW(claimed.c_str());
}
static void CALLBACK tick(HWND, UINT, UINT_PTR, DWORD) {
    if (working >= 2) return;
    ++working;
    try {
        if (restoreKeys && GetTickCount64() >= restoreAt) { SetKeyboardState(previousKeys); restoreKeys = false; }
        if (!ready && IsWindowVisible(window) && element(1101)) {
            Data d; d.type = 8; invoke(d);
            if (d.v[1]) {
                writeFile(L"bridge-ready.json", "{\"pid\":" + std::to_string(GetCurrentProcessId()) + ",\"token\":" + q(token) + "}");
                ready = true;
            }
        }
        if (ready) processRequest(working > 1);
    } catch (...) { }
    --working;
}
extern "C" __declspec(dllexport) BOOL OnInitPlug(Setter fn, void* mainFrame, int version) {
    if (version != 3 || sizeof(void*) != 8) return FALSE;
    wchar_t path[32768], secret[64], verified[4] = {};
    DWORD n = GetEnvironmentVariableW(L"CLI_ANYTHING_XCIDE_IPC", path, 32768);
    DWORD k = GetEnvironmentVariableW(L"CLI_ANYTHING_XCIDE_IPC_TOKEN", secret, 64);
    if (!n || n >= 32768 || k != 32) return FALSE;
    directory.assign(path, n); token.assign(secret, k);
    if (token.find_first_not_of(L"0123456789abcdef") != std::wstring::npos) return FALSE;
    GetEnvironmentVariableW(L"CLI_ANYTHING_XCIDE_PARSE_VERIFIED", verified, 4);
    verifiedParse = verified[0] == L'1';
    xc = GetModuleHandleW(L"XCGUI.dll"); setter = fn;
    try {
        window = api<HWND(WINAPI*)(void*)>("XWnd_GetHWND")(mainFrame);
        DWORD pid = 0;
        if (!IsWindow(window) || GetWindowThreadProcessId(window, &pid) != GetCurrentThreadId() || pid != GetCurrentProcessId()) return FALSE;
        timer = SetTimer(window, 0x58434932, 50, tick);
        return timer != 0;
    } catch (...) { return FALSE; }
}
extern "C" __declspec(dllexport) BOOL OnExitPlug() {
    if (timer) KillTimer(window, timer);
    if (restoreKeys) SetKeyboardState(previousKeys);
    timer = 0; setter = nullptr; return TRUE;
}
