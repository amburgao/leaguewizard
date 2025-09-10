import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

ULONG_PTR: type[ctypes.c_uint32] | type[ctypes.c_uint64]

if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ULONG_PTR),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.CHAR * 260),
    ]


CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
Process32First = kernel32.Process32First
Process32Next = kernel32.Process32Next
OpenProcess = kernel32.OpenProcess
CloseHandle = kernel32.CloseHandle
QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW

QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
QueryFullProcessImageNameW.restype = wintypes.BOOL


def get_process_fullname(pid: int) -> str | None:
    hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hProcess:
        return None
    try:
        buf_len = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        if QueryFullProcessImageNameW(hProcess, 0, buf, ctypes.byref(buf_len)):
            return buf.value
    finally:
        CloseHandle(hProcess)
    return None


def find_process_fullname(target_name: str) -> str | None:
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == -1:
        msg = "CreateToolhelp32Snapshot failed"
        raise OSError(msg)

    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

    if not Process32First(snapshot, ctypes.byref(entry)):
        CloseHandle(snapshot)
        return None

    while True:
        exe_name = entry.szExeFile.decode("utf-8")
        if exe_name.lower() == target_name.lower():
            pid = entry.th32ProcessID
            CloseHandle(snapshot)
            return get_process_fullname(pid)
        if not Process32Next(snapshot, ctypes.byref(entry)):
            break

    CloseHandle(snapshot)
    return None
