import base64
import os
import signal
import sys

from ctypes import *
from ctypes.wintypes import *

from webview2 import *

APP_NAME = 'wrender'
APP_VERSION = '0.1'
APP_DIR = os.path.dirname(os.path.abspath(__file__))

INCHES_PER_MM = 1 / 25.4

WM_CLOSE = 16
WM_TIMER = 275
WS_EX_TOOLWINDOW = 128
WS_OVERLAPPEDWINDOW = 13565952
WS_POPUP = -2147483648
WS_VISIBLE = 268435456

STGM_CREATE = 4096
STGM_WRITE = 1

EXT_IMG_INPUT = ('.avif', '.bmp', '.gif', '.ico', '.jpeg', '.jpg', '.png', '.svg', '.webp')
EXT_IMG_OUTPUT_CV = ('.jpeg', '.jpg', '.png', '.webp')
EXT_IMG_OUTPUT_WV = ('.jpeg', '.jpg', '.png')
EXT_HTML = ('.htm', '.html')

# Exit codes
ERROR_WRONG_PARAMETERS = 1
ERROR_INPUT_NOT_FOUND = 2
ERROR_NO_EXT = 3
ERROR_INPUT_EXT_NOT_SUPPORTED = 4
ERROR_OUTPUT_EXT_NOT_SUPPORTED = 5
ERROR_PY_EXCEPTION = 6
ERROR_JS_EXCEPTION = 7
ERROR_WEBVIEW_CALLBACK = 8

IS_64_BIT = sys.maxsize > 2**32
LONG_PTR = ctypes.c_longlong if IS_64_BIT else ctypes.c_long
WNDPROC = ctypes.WINFUNCTYPE(LONG_PTR, HWND, UINT, WPARAM, LPARAM)

class WNDCLASSEXW(Structure):
    def __init__(self, *args, **kwargs):
        super(WNDCLASSEXW, self).__init__(*args, **kwargs)
        self.cbSize = sizeof(self)
    _fields_ = [
        ("cbSize", c_uint),
        ("style", c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", HANDLE),
        ("hIcon", HANDLE),
        ("hCursor", HANDLE),
        ("hbrBackground", HANDLE),
        ("lpszMenuName", LPCWSTR),
        ("lpszClassName", LPCWSTR),
        ("hIconSm", HANDLE)
    ]

shlwapi = windll.Shlwapi
shlwapi.SHCreateStreamOnFileW.argtypes = (LPCWSTR, DWORD, POINTER(POINTER(IStream)))

user32 = windll.user32
user32.CreateWindowExW.argtypes = (DWORD, LPCWSTR, LPCWSTR, DWORD, INT, INT, INT, INT, HWND, HMENU, HINSTANCE, LPVOID)
user32.DefWindowProcW.argtypes = (HWND, UINT, WPARAM, LPARAM)
user32.DispatchMessageW.argtypes = (LPMSG,)
user32.GetMessageW.argtypes = (LPMSG, HWND, UINT, UINT)
user32.TranslateMessage.argtypes = (LPMSG,)

DEBUG = False

class ctx:
    exit_code = 0


########################################
# Wrapper Class
########################################
class MainWin():

    ########################################
    #
    ########################################
    def __init__(self):

        self.timers = {}
        self.timer_id_counter = 1000

        ########################################
        #
        ########################################
        def _on_WM_TIMER(wparam):
            if wparam in self.timers:
                callback = self.timers[wparam][0]
                if self.timers[wparam][1]:
                    user32.KillTimer(self.hwnd, wparam)
                    del self.timers[wparam]
                callback()
            return 0

        ########################################
        #
        ########################################
        def _window_proc_callback(hwnd, msg, wparam, lparam):
            if msg == WM_TIMER:
                _on_WM_TIMER(wparam)
            elif msg == WM_CLOSE:
                self.quit()
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self.windowproc = WNDPROC(_window_proc_callback)

        newclass = WNDCLASSEXW()
        newclass.lpfnWndProc = self.windowproc
#        newclass.style = 3  # CS_VREDRAW | CS_HREDRAW
        newclass.lpszClassName = APP_NAME
        user32.RegisterClassExW(byref(newclass))

        if DEBUG:
            self.hwnd = user32.CreateWindowExW(
                0,
                newclass.lpszClassName,
                APP_NAME,
                WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                0, 0, 200, 200,
                0, 0, 0, 0
            )
        else:
            self.hwnd = user32.CreateWindowExW(
                WS_EX_TOOLWINDOW,
                newclass.lpszClassName,
                APP_NAME,
                WS_POPUP | WS_VISIBLE,
                0, 0, 0, 0,
                0, 0, 0, 0
            )

    ########################################
    #
    ########################################
    def create_timer(self, callback, ms, is_singleshot=False, timer_id=None):
        if timer_id is None:
            timer_id = self.timer_id_counter
            self.timer_id_counter += 1
        self.timers[timer_id] = (callback, is_singleshot)
        user32.SetTimer(self.hwnd, timer_id, ms, 0)
        return timer_id

    ########################################
    #
    ########################################
    def run(self):
        msg = MSG()
        while user32.GetMessageW(byref(msg), None, 0, 0):
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))
        return 0

    ########################################
    #
    ########################################
    def quit(self, *args, exit_code = 0):
        user32.PostQuitMessage(exit_code)


########################################
#
########################################
def url_to_img(url, output_file, ext_output, view_width, wait_ms):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, url = url, is_private = True, width = view_width, height = 100)

    image_format = IMAGE_FORMAT.PNG if ext_output == '.png' else IMAGE_FORMAT.JPEG

    ########################################
    #
    ########################################
    def _on_size(w, h):
#        print(w, h)
        try:
            webview.put_bounds(RECT(0, 0, view_width, h))

            ########################################
            #
            ########################################
            def _on_capture(error_code, result):
                if error_code != 0:
                    ctx.exit_code = ERROR_WEBVIEW_CALLBACK
                if not DEBUG:
                    webview.close()
                    win.quit()

            istream = POINTER(IStream)()
            shlwapi.SHCreateStreamOnFileW(output_file, STGM_CREATE | STGM_WRITE, byref(istream))
            webview.capture(image_format, istream, _on_capture)

        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
            if not DEBUG:
                webview.close()
                win.quit()

    ########################################
    #
    ########################################
    def _on_navigation_completed(webview, args):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_size', _on_size)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        js = 'chrome.webview.api.on_size(document.documentElement.scrollWidth,document.documentElement.scrollHeight);'  #document.body.style.overflow="hidden";

        if wait_ms:
            win.create_timer(lambda:webview.execute_js_with_result(js, _on_js_result), wait_ms, True)
        else:
            webview.execute_js_with_result(js, _on_js_result)

    webview.connect(EVENT.NAVIGATION_COMPLETED, _on_navigation_completed)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def url_to_pdf(url, output_file, page_margins, page_size, wait_ms):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, url = url, is_private = True)

    ########################################
    #
    ########################################
    def _do_print():
        print_settings = WebView2.environment.CreatePrintSettings()

        print_settings.put_PageWidth(page_size[0] * INCHES_PER_MM)
        print_settings.put_PageHeight(page_size[1] * INCHES_PER_MM)

        print_settings.put_MarginTop(page_margins[0] * INCHES_PER_MM)
        print_settings.put_MarginBottom(page_margins[1] * INCHES_PER_MM)
        print_settings.put_MarginLeft(page_margins[2] * INCHES_PER_MM)
        print_settings.put_MarginRight(page_margins[3] * INCHES_PER_MM)

        try:
            ########################################
            #
            ########################################
            def _on_printed(error_code, result):
                if (output_file and not result) or error_code != 0:
                    print(f'Error: Printing failed', file = sys.stderr)
                    ctx.exit_code = ERROR_WEBVIEW_CALLBACK
                if not DEBUG:
                    webview.close()
                    win.quit()

            if output_file:
                webview.print_to_pdf(output_file, print_settings, _on_printed)
            else:
                webview.print(print_settings, _on_printed)

        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
            if not DEBUG:
                webview.close()
                win.quit()

    ########################################
    #
    ########################################
    def _on_navigation_completed(webview, args):
        if DEBUG:
            webview.open_dev_tools()

        if wait_ms:
            win.create_timer(_do_print, wait_ms, True)
        else:
            _do_print()

    webview.connect(EVENT.NAVIGATION_COMPLETED, _on_navigation_completed)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def html_to_img(input_file, output_file, ext_output, view_width, wait_ms):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, url = f'http://localhost/{os.path.basename(input_file)}', is_private = True, width = view_width, height = 100)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))

    image_format = IMAGE_FORMAT.PNG if ext_output == '.png' else IMAGE_FORMAT.JPEG

    ########################################
    #
    ########################################
    def _on_size(w, h):
#        print(w, h)
        try:
            webview.put_bounds(RECT(0, 0, view_width, h))

            ########################################
            #
            ########################################
            def _on_capture(error_code, result):
                if error_code != 0:
                    ctx.exit_code = ERROR_WEBVIEW_CALLBACK
                    print(f'Error: Capture failed', file = sys.stderr)
                if not DEBUG:
                    webview.close()
                    win.quit()

            istream = POINTER(IStream)()
            shlwapi.SHCreateStreamOnFileW(output_file, STGM_CREATE | STGM_WRITE, byref(istream))
            webview.capture(image_format, istream, _on_capture)

        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
            if not DEBUG:
                webview.close()
                win.quit()

    ########################################
    #
    ########################################
    def _on_navigation_completed(webview, args):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_size', _on_size)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        js = 'chrome.webview.api.on_size(document.documentElement.scrollWidth,document.documentElement.scrollHeight);'  # document.body.style.overflow="hidden"

        if wait_ms:
            win.create_timer(lambda: webview.execute_js_with_result(js, _on_js_result), wait_ms, True)
        else:
            webview.execute_js_with_result(js, _on_js_result)

    webview.connect(EVENT.NAVIGATION_COMPLETED, _on_navigation_completed)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def html_to_pdf(input_file, output_file, page_margins, page_size, wait_ms):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, url = f'http://localhost/{os.path.basename(input_file)}', is_private = True)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))

    ########################################
    #
    ########################################
    def _on_print():
        print_settings = WebView2.environment.CreatePrintSettings()

        print_settings.put_PageWidth(page_size[0] * INCHES_PER_MM)
        print_settings.put_PageHeight(page_size[1] * INCHES_PER_MM)

        print_settings.put_MarginTop(page_margins[0] * INCHES_PER_MM)
        print_settings.put_MarginBottom(page_margins[1] * INCHES_PER_MM)
        print_settings.put_MarginLeft(page_margins[2] * INCHES_PER_MM)
        print_settings.put_MarginRight(page_margins[3] * INCHES_PER_MM)

        try:
            ########################################
            #
            ########################################
            def _on_printed(error_code, result):
                if (output_file and not result) or error_code != 0:
                    print(f'Error: Printing failed', file = sys.stderr)
                    ctx.exit_code = ERROR_WEBVIEW_CALLBACK
                if not DEBUG:
                    webview.close()
                    win.quit()

            if output_file:
                webview.print_to_pdf(output_file, print_settings, _on_printed)
            else:
                webview.print(print_settings, _on_printed)

        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
            if not DEBUG:
                webview.close()
                win.quit()

    ########################################
    #
    ########################################
    def _on_navigation_completed(webview, args):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_print', _on_print)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        js = f'document.body.style.margin="0px";document.title="{os.path.basename(input_file)}";chrome.webview.api.on_print();'

        if wait_ms:
            win.create_timer(lambda: webview.execute_js_with_result(js, _on_js_result), wait_ms, True)
        else:
            webview.execute_js_with_result(js, _on_js_result)

    webview.connect(EVENT.NAVIGATION_COMPLETED, _on_navigation_completed)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def img_to_img(input_file, output_file, ext_output):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, is_private = True)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))

    mimetype = 'image/' + ('jpeg' if ext_output == '.jpg' else ext_output[1:])

    ########################################
    #
    ########################################
    def _on_data(b64_data):
        try:
            with open(output_file, 'wb') as f:
                f.write(base64.b64decode(b64_data[13 + len(mimetype):]))  # data:image/png;base64,
        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
        if not DEBUG:
            webview.close()
            win.quit()

    ########################################
    #
    ########################################
    def _on_dom_content_loaded(webview):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_data', _on_data)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        webview.execute_js_with_result(
'''const img=new Image();
img.src="http://localhost/{}";
img.onload=() => {{
  const canvas=document.createElement("canvas");
  canvas.width=img.width;
  canvas.height=img.height;
  canvas.getContext('2d').drawImage(img,0,0,img.width,img.height);
  chrome.webview.api.on_data(canvas.toDataURL("{}"));
}}'''.format(os.path.basename(input_file), mimetype),
            _on_js_result
        )

    webview.connect(EVENT.DOM_CONTENT_LOADED, _on_dom_content_loaded)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def img_to_pdf(input_file, output_file):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, is_private = True)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))

    ########################################
    #
    ########################################
    def _on_size(w, h):
#        print(w, h)  # 133 127
        try:
            print_settings = WebView2.environment.CreatePrintSettings().QueryInterface(ICoreWebView2PrintSettings2)

            print_settings.put_PageWidth(w / 96)
            print_settings.put_PageHeight(h / 96)

            print_settings.put_MarginTop(0)
            print_settings.put_MarginBottom(0)
            print_settings.put_MarginLeft(0)
            print_settings.put_MarginRight(0)

            print_settings.put_PageRanges('1')  # Prevent second empty page

            ########################################
            #
            ########################################
            def _on_printed(error_code, result):
                if (output_file and not result) or error_code != 0:
                    print(f'Error: Printing failed', file = sys.stderr)
                    ctx.exit_code = ERROR_WEBVIEW_CALLBACK
                if not DEBUG:
                    webview.close()
                    win.quit()

            if output_file:
                webview.print_to_pdf(output_file, print_settings, _on_printed)
            else:
                webview.print(print_settings, _on_printed)

        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
            if not DEBUG:
                webview.close()
                win.quit()

    ########################################
    #
    ########################################
    def _on_dom_content_loaded(webview):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_size', _on_size)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        webview.execute_js_with_result(
'''const img=new Image();
img.src="http://localhost/{}";
img.onload=() => chrome.webview.api.on_size(img.width,img.height);
document.body.innerHTML="";
document.body.style.margin="0px";
document.body.appendChild(img);
document.title="{}";
'''.format(os.path.basename(input_file), os.path.basename(input_file)),
            _on_js_result
        )

    webview.connect(EVENT.DOM_CONTENT_LOADED, _on_dom_content_loaded)

    win.run()
    sys.exit(ctx.exit_code)

########################################
# , margin = '10px'
########################################
def md_to_img(input_file, output_file, view_width):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, url = f'http://localhost/{os.path.basename(input_file)}', is_private = True, width = view_width, height = 100)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))
    webview.set_virtual_host_name_to_folder_mapping('resources', APP_DIR)

    image_format = IMAGE_FORMAT.PNG if ext_output == '.png' else IMAGE_FORMAT.JPEG

    ########################################
    #
    ########################################
    def _on_size(w, h):
#        print(w, h)
        try:
            webview.put_bounds(RECT(0, 0, view_width, h))

            ########################################
            #
            ########################################
            def _on_capture(error_code, result):
                if error_code != 0:
                    ctx.exit_code = ERROR_WEBVIEW_CALLBACK
                if not DEBUG:
                    webview.close()
                    win.quit()

            istream = POINTER(IStream)()
            shlwapi.SHCreateStreamOnFileW(output_file, STGM_CREATE | STGM_WRITE, byref(istream))
            webview.capture(image_format, istream, _on_capture)

        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
            if not DEBUG:
                webview.close()
                win.quit()

    ########################################
    #
    ########################################
    def _on_navigation_completed(webview, args):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_size', _on_size)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        webview.execute_js_with_result(
f'''const scr=document.createElement("script");
scr.src="http://resources/marked.js";
scr.onload=() => {{
  document.body.innerHTML=marked.parse(document.body.firstElementChild.innerText);
  chrome.webview.api.on_size(document.body.scrollWidth,document.body.scrollHeight);
  document.body.style.overflow="hidden";
}};
document.body.appendChild(scr);''',
#document.body.style.margin="{margin}";''',
            _on_js_result
        )

    webview.connect(EVENT.NAVIGATION_COMPLETED, _on_navigation_completed)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def md_to_html(input_file, output_file):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, url = f'http://localhost/{os.path.basename(input_file)}', is_private = True)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))
    webview.set_virtual_host_name_to_folder_mapping('resources', APP_DIR)

    ########################################
    #
    ########################################
    def _on_html(html):
        try:
            with open(output_file, 'w') as f:
                f.write(html)
        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
        if not DEBUG:
            webview.close()
            win.quit()

    ########################################
    #
    ########################################
    def _on_dom_content_loaded(webview):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_html', _on_html)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        webview.execute_js_with_result(
'''const scr=document.createElement("script");
scr.src="http://resources/marked.js";
scr.onload=()=>chrome.webview.api.on_html(marked.parse(document.body.firstElementChild.innerText));
document.body.appendChild(scr);''',
            _on_js_result
        )

    webview.connect(EVENT.DOM_CONTENT_LOADED, _on_dom_content_loaded)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def md_to_pdf(input_file, output_file, page_margins, page_size):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, url = f'http://localhost/{os.path.basename(input_file)}', is_private = True)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))
    webview.set_virtual_host_name_to_folder_mapping('resources', APP_DIR)

    ########################################
    #
    ########################################
    def _on_parsed():
        print_settings = WebView2.environment.CreatePrintSettings()

        print_settings.put_PageWidth(page_size[0] * INCHES_PER_MM)
        print_settings.put_PageHeight(page_size[1] * INCHES_PER_MM)

        print_settings.put_MarginTop(page_margins[0] * INCHES_PER_MM)
        print_settings.put_MarginBottom(page_margins[1] * INCHES_PER_MM)
        print_settings.put_MarginLeft(page_margins[2] * INCHES_PER_MM)
        print_settings.put_MarginRight(page_margins[3] * INCHES_PER_MM)

        try:
            ########################################
            #
            ########################################
            def _on_printed(error_code, result):
                if (output_file and not result) or error_code != 0:
                    print(f'Error: Printing failed', file = sys.stderr)
                    ctx.exit_code = ERROR_WEBVIEW_CALLBACK
                if not DEBUG:
                    webview.close()
                    win.quit()

            if output_file:
                webview.print_to_pdf(output_file, print_settings, _on_printed)
            else:
                webview.print(print_settings, _on_printed)

        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
            if not DEBUG:
                webview.close()
                win.quit()

    ########################################
    #
    ########################################
    def _on_dom_content_loaded(webview):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_parsed', _on_parsed)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        webview.execute_js_with_result(
f'''const scr=document.createElement("script");
scr.src="http://resources/marked.js";
scr.onload=() => {{
  document.body.innerHTML=marked.parse(document.body.firstElementChild.innerText);
  chrome.webview.api.on_parsed();
}};
document.body.appendChild(scr);
document.body.style.margin="0px";
document.title="{os.path.basename(input_file)}";''',
            _on_js_result
        )

    webview.connect(EVENT.DOM_CONTENT_LOADED, _on_dom_content_loaded)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def xml_to_json(input_file, output_file):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, is_private = True)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))

    ########################################
    #
    ########################################
    def _on_data(json_data):
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_data)
        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
        if not DEBUG:
            webview.close()
            win.quit()

    ########################################
    #
    ########################################
    def _on_dom_content_loaded(webview):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_data', _on_data)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        webview.execute_js_with_result(
f'''function xml2json(doc) {{
  const children = [...doc.children];
  if (!children.length)
    return doc.innerHTML;
  const res = {{}};
  for (let child of children) {{
    if (children.filter(eachChild => eachChild.nodeName === child.nodeName).length > 1) {{
      if (res[child.nodeName] === undefined)
        res[child.nodeName] = [xml2json(child)];
      else
        res[child.nodeName].push(xml2json(child));
    }} else
      res[child.nodeName] = xml2json(child);
  }}
  return res;
}}
const xhr = new XMLHttpRequest();
xhr.responseType  = "document";
xhr.onreadystatechange = () => {{
  if (xhr.readyState === 4)
    chrome.webview.api.on_data(JSON.stringify(xml2json(xhr.response)));
}};
xhr.open("GET", "http://localhost/{os.path.basename(input_file)}", true);
xhr.send();''',
            _on_js_result
        )

    webview.connect(EVENT.DOM_CONTENT_LOADED, _on_dom_content_loaded)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def json_to_xml(input_file, output_file):
    win = MainWin()
    webview = WebView2(parent_hwnd = win.hwnd, is_private = True)
    webview.set_virtual_host_name_to_folder_mapping('localhost', os.path.dirname(input_file))

    with open(input_file, 'r', encoding='utf-8') as f:
        json_data = f.read().strip()

    ########################################
    #
    ########################################
    def _on_data(xml_data):
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>')
                f.write(xml_data)
        except Exception as e:
            print(f'Error: {e}', file = sys.stderr)
            ctx.exit_code = ERROR_PY_EXCEPTION
        if not DEBUG:
            webview.close()
            win.quit()

    ########################################
    #
    ########################################
    def _on_dom_content_loaded(webview):
        if DEBUG:
            webview.open_dev_tools()

        webview.expose('on_data', _on_data)

        ########################################
        #
        ########################################
        def _on_js_result(error_code, result):
            if not result.get_Succeeded():
                print(result.get_Exception().get_Message(), file = sys.stderr)
                ctx.exit_code = ERROR_JS_EXCEPTION
                if not DEBUG:
                    webview.close()
                    win.quit()

        webview.execute_js_with_result(
f'''function obj2xml(obj) {{
  let xml = '';
  for (let prop in obj) {{
    xml += obj[prop] instanceof Array ? '' : "<" + prop + ">";
    if (obj[prop] instanceof Array) {{
      for (let array in obj[prop]) {{
        xml += "<" + prop + ">";
        xml += obj2xml(new Object(obj[prop][array]));
        xml += "</" + prop + ">";
      }}
    }} else if (typeof obj[prop] == "object")
      xml += obj2xml(new Object(obj[prop]));
    else
      xml += obj[prop];
    xml += obj[prop] instanceof Array ? '' : "</" + prop + ">";
  }}
  return xml.replace(/<\\/?[0-9]{1,}>/g, '');
}}
chrome.webview.api.on_data(obj2xml({json_data}));''',
            _on_js_result
        )

    webview.connect(EVENT.DOM_CONTENT_LOADED, _on_dom_content_loaded)

    win.run()
    sys.exit(ctx.exit_code)

########################################
#
########################################
def print_usage(exit_code):

    print(f'''{APP_NAME} v{APP_VERSION}

Usage:

 {APP_NAME} <input> <output> [options...]
 {APP_NAME} -h              Show this help
 {APP_NAME} -u              Check for online update

Options:

 --page-margins=n,n,n,n  Top,bottom,left,right page margin in mm.
                         Default: 10,10,10,10
                         Applicable: input=<url>|.htm|.html|.md, output=.pdf|PRINTER

 --page-size=n,n         Page width and height in mm.
                         Default: 210,297 (=Din A4)
                         Applicable: input=<url>|.htm|.html|.md, output=.pdf|PRINTER

 --view-width=n          View width in pixel.
                         Default: 1024
                         Applicable: input=<url>|.htm|.html|.md, output=.jpg|.jpeg|.png

 --wait=n                After DOM content is loaded wait n milliseconds before rendering.
                         Default: 0
                         Applicable: input=<url>|.htm|.html

Input:                   Supported Outputs:

 <url>                   .jpeg .jpg .png .pdf PRINTER
 .avif                   .jpeg .jpg .png .pdf .webp PRINTER
 .bmp                    .jpeg .jpg .png .pdf .webp PRINTER
 .gif                    .jpeg .jpg .png .pdf .webp PRINTER
 .htm                    .jpeg .jpg .png .pdf PRINTER
 .html                   .jpeg .jpg .png .pdf PRINTER
 .ico                    .jpeg .jpg .png .pdf .webp PRINTER
 .jpeg                   .jpeg .jpg .png .pdf .webp PRINTER
 .jpg                    .jpeg .jpg .png .pdf .webp PRINTER
 .json                   .xml
 .md                     .html .jpeg .jpg .png .pdf PRINTER
 .png                    .jpeg .jpg .png .pdf .webp PRINTER
 .svg                    .jpeg .jpg .png .pdf .webp PRINTER
 .webp                   .jpeg .jpg .png .pdf .webp PRINTER
 .xml                    .json

If PRINTER is specified as output, {APP_NAME} tries to print with the default printer.''',
        file = sys.stderr
    )
    sys.exit(exit_code)

########################################
#
########################################
def check_update():
    shell32 = windll.Shell32
    shell32.ShellExecuteW.argtypes = (HWND, LPCWSTR, LPCWSTR, LPCWSTR, LPCWSTR, INT)
    command = f'"{os.path.join(APP_DIR, "update.ps1")}" "{APP_NAME}" {APP_VERSION} "https://github.com/59de44955ebd/{APP_NAME}"'
    shell32.ShellExecuteW(None, None, 'powershell.exe', command, None, 0)
    sys.exit(0)

########################################
#
########################################
if __name__ == '__main__':

    if len(sys.argv) < 3:
        if len(sys.argv) >= 2:
            if sys.argv[1] == '-h':
                print_usage(0)
            elif sys.argv[1] == '-u':
                check_update()

        print_usage(ERROR_WRONG_PARAMETERS)

    input_is_url = sys.argv[1].startswith('https:') or sys.argv[1].startswith('http:')

    if not input_is_url and not os.path.isfile(sys.argv[1]):
        print(f'Error: File {sys.argv[1]} not found', file = sys.stderr)
        sys.exit(ERROR_INPUT_NOT_FOUND)

    if input_is_url:
        input_file = sys.argv[1]
    else:
        ext_input = os.path.splitext(sys.argv[1])[1].lower()
        if not ext_input:
            print(f'Error: Input {sys.argv[1]} has no file extension', file = sys.stderr)
            sys.exit(ERROR_NO_EXT)
        input_file = os.path.abspath(sys.argv[1])

    output_to_printer = sys.argv[2].upper() == 'PRINTER'
    if output_to_printer:
        ext_output = 'PRINTER'
        output_file = None
    else:
        ext_output = os.path.splitext(sys.argv[2])[1].lower()
        if not ext_output:
            print(f'Error: Output {sys.argv[2]} has no file extension', file = sys.stderr)
            sys.exit(ERROR_NO_EXT)
        output_file = os.path.abspath(sys.argv[2])

    # --wait=...
    # --width=...
    # --margin=

    page_margins = (10, 10, 10, 10)
    page_size = (210, 297)
    view_width = 1024
    wait_ms = 0

    try:
        for arg in sys.argv[3:]:
            if arg.startswith('--page-margins='):
                page_margins = arg[15:].split(',')
                if len(page_margins) == 1:
                    page_margins = (float(page_margins[0]),) * 4
                else:
                    page_margins = (float(page_margins[0]), float(page_margins[1]), float(page_margins[2]), float(page_margins[3]))

            elif arg.startswith('--page-size='):
                page_size = arg[12:].split(',')
                page_size = (float(page_size[0]), float(page_size[1]))

            elif arg.startswith('--view-width='):
                view_width = int(arg[13:])

            elif arg.startswith('--wait='):
                wait_ms = int(arg[7:])
    except:
        print_usage(ERROR_WRONG_PARAMETERS)

    if input_is_url:

        if ext_output in EXT_IMG_OUTPUT_WV:
            url_to_img(input_file, output_file, ext_output, view_width = view_width, wait_ms = wait_ms)

        elif output_to_printer or ext_output == '.pdf':
            url_to_pdf(input_file, output_file, page_margins = page_margins, page_size = page_size, wait_ms = wait_ms)

        else:
            print(f'Error: {ext_output} not supported as output for URL input', file = sys.stderr)
            sys.exit(ERROR_OUTPUT_EXT_NOT_SUPPORTED)

    elif ext_input in EXT_HTML:

        if ext_output in EXT_IMG_OUTPUT_WV:
            html_to_img(input_file, output_file, ext_output, wait_ms = wait_ms, view_width = view_width)

        elif output_to_printer or ext_output == '.pdf':
            html_to_pdf(input_file, output_file, page_margins = page_margins, page_size = page_size, wait_ms = wait_ms)

        else:
            print(f'Error: {ext_output} not supported as output for input {ext_input}', file = sys.stderr)
            sys.exit(ERROR_OUTPUT_EXT_NOT_SUPPORTED)

    elif ext_input in EXT_IMG_INPUT:

        if ext_output in EXT_IMG_OUTPUT_CV:
            img_to_img(input_file, output_file, ext_output)

        elif output_to_printer or ext_output == '.pdf':
            img_to_pdf(input_file, output_file)

        else:
            print(f'Error: {ext_output} not supported as output for input {ext_input}', file = sys.stderr)
            sys.exit(ERROR_OUTPUT_EXT_NOT_SUPPORTED)

    elif ext_input == '.md':

        if ext_output in EXT_IMG_OUTPUT_WV:
            md_to_img(input_file, output_file, view_width = view_width)

        elif ext_output in EXT_HTML:
            md_to_html(input_file, output_file)

        elif output_to_printer or ext_output == '.pdf':
            md_to_pdf(input_file, output_file, page_margins = page_margins, page_size = page_size)

        else:
            print(f'Error: {ext_output} not supported as output for input {ext_input}', file = sys.stderr)
            sys.exit(ERROR_OUTPUT_EXT_NOT_SUPPORTED)

    elif ext_input == '.xml':

        if ext_output == '.json':
            xml_to_json(input_file, output_file)

        else:
            print(f'Error: {ext_output} not supported as output for input {ext_input}', file = sys.stderr)
            sys.exit(ERROR_OUTPUT_EXT_NOT_SUPPORTED)

    elif ext_input == '.json':

        if ext_output == '.xml':
            json_to_xml(input_file, output_file)

        else:
            print(f'Error: {ext_output} not supported as output for input {ext_input}', file = sys.stderr)
            sys.exit(ERROR_OUTPUT_EXT_NOT_SUPPORTED)

    else:
        print(f'Error: Extension {ext_input} not supported as input', file = sys.stderr)
        sys.exit(ERROR_INPUT_EXT_NOT_SUPPORTED)
