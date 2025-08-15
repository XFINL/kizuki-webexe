import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, tempfile, subprocess, threading, platform
import time 
import random

def apply_default_windows_theme(root):
    style = ttk.Style()
    
    available_themes = style.theme_names()
    if platform.system() == "Windows":
        if "vista" in available_themes:
            style.theme_use("vista")
        elif "xpnative" in available_themes:
            style.theme_use("xpnative")
        else:
            style.theme_use("default")
    else:
        if "clam" in available_themes:
            style.theme_use("clam")
        else:
            style.theme_use("default")

    style.configure(".", font=('Segoe UI', 9))
    style.configure("TButton", padding=[10, 5]) 
    style.configure("TEntry", padding=4)
    style.configure("TCheckbutton", padding=4)
    style.configure("TLabel", padding=[2, 2])
    style.configure("TLabelframe.Label", font=('Segoe UI', 9, 'bold'))


class Web2ExeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Web2EXE 网页打包器")
        self.root.geometry("1024x768") 
        self.root.resizable(True, True) 
        
        self.use_webview = tk.BooleanVar(value=True) 
        self.use_splash_screen = tk.BooleanVar(value=False) 
        self.splash_html_path = tk.StringVar() 
        self.increase_volume = tk.BooleanVar(value=False)
        
        self.fields = {} 
        
        apply_default_windows_theme(self.root) 
        
        self.last_output_dir = "" 
        self.start_build_time = None 
        self.timer_id = None 

        self.build_ui()

    def build_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(main_frame, borderwidth=0, highlightthickness=0) 
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion = self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame_window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.scrollable_frame_window_id, width=e.width), add="+")


        url_section_frame = ttk.LabelFrame(self.scrollable_frame, text="网址配置", padding=(15, 10)) 
        url_section_frame.pack(fill='x', padx=15, pady=(10, 5)) 
        ttk.Label(url_section_frame, text="输入网址（每行一个）:").pack(anchor='w', pady=(0, 5))
        self.url_text = tk.Text(url_section_frame, height=5, wrap='word',
                                font=('Segoe UI', 9), 
                                bd=1, relief="sunken", highlightthickness=0) 
        self.url_text.pack(fill='x', expand=True, pady=(0, 5))

        info_section_frame = ttk.LabelFrame(self.scrollable_frame, text="基本信息", padding=(15, 10))
        info_section_frame.pack(fill='x', padx=15, pady=5)

        row_idx = 0
        def add_field(parent_frame, label, key, browse=False, is_file=True):
            nonlocal row_idx
            field_row_frame = ttk.Frame(parent_frame)
            field_row_frame.pack(fill='x', pady=3) 

            ttk.Label(field_row_frame, text=f"{label}:", width=15, anchor='w').pack(side='left') 
            
            var = tk.StringVar()
            ent = ttk.Entry(field_row_frame, textvariable=var)
            ent.pack(side='left', fill='x', expand=True, padx=(0, 10))

            if browse:
                btn = ttk.Button(field_row_frame, text="浏览", command=lambda: self.select_path(var, is_file, key), width=8) 
                btn.pack(side='right') 
            self.fields[key] = var
            row_idx += 1
        
        add_field(info_section_frame, "程序标题", "title")
        add_field(info_section_frame, "软件版本", "version")
        add_field(info_section_frame, "公司名称", "company") 
        add_field(info_section_frame, "描述", "desc")
        add_field(info_section_frame, "程序图标 (.ico)", "icon", True, is_file=True)
        add_field(info_section_frame, "窗口图标 (.ico)", "winicon", True, is_file=True)
        add_field(info_section_frame, "启动页 HTML (.html)", "splash_html", True, is_file=True) 
        add_field(info_section_frame, "输出目录", "output", True, is_file=False)

        options_section_frame = ttk.LabelFrame(self.scrollable_frame, text="打包选项", padding=(15, 10))
        options_section_frame.pack(fill='x', padx=15, pady=5)
        
        ttk.Checkbutton(options_section_frame, text="使用内置浏览器（不跳出默认浏览器）", variable=self.use_webview).pack(anchor='w', pady=3)
        ttk.Checkbutton(options_section_frame, text="启用自定义启动页面（需要提供HTML文件）", variable=self.use_splash_screen).pack(anchor='w', pady=3)
        ttk.Checkbutton(options_section_frame, text="增大体积（额外添加一个300MB文件）", variable=self.increase_volume).pack(anchor='w', pady=3)


        ttk.Button(self.scrollable_frame, text="开始打包", command=self.start).pack(pady=15, padx=15) 
        self.status = ttk.Label(self.scrollable_frame, text="", foreground="green")
        self.status.pack(pady=5, padx=15)

        self.elapsed_time_label = ttk.Label(self.scrollable_frame, text="预计时间: 00:00:00", foreground="blue")
        self.elapsed_time_label.pack(pady=2, padx=15)

        self.open_output_button = ttk.Button(self.scrollable_frame, text="打开输出目录", command=self.open_output_folder, state='disabled')
        self.open_output_button.pack(pady=5, padx=15)

        log_section_frame = ttk.LabelFrame(self.scrollable_frame, text="打包日志", padding=(15, 10))
        log_section_frame.pack(fill='both', expand=True, padx=15, pady=(5, 15)) 

        self.log_text = tk.Text(log_section_frame, height=10, state='disabled', wrap='word',
                                font=('Consolas', 9), bg='white', fg='black', 
                                bd=1, relief="sunken", highlightthickness=0) 
        self.log_text.pack(fill='both', expand=True, pady=(0, 5))
        log_scrollbar = ttk.Scrollbar(log_section_frame, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)


    def _on_mousewheel(self, event):
        if platform.system() == "Windows":
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif platform.system() == "Darwin":
            self.canvas.yview_scroll(int(-1*event.delta), "units")
        else:
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

    def select_path(self, var, is_file, key):
        path = ""
        if is_file:
            if key == "icon" or key == "winicon":
                path = filedialog.askopenfilename(filetypes=[("ICO files", "*.ico"), ("All files", "*.*")])
            elif key == "splash_html":
                path = filedialog.askopenfilename(filetypes=[("HTML files", "*.html"), ("All files", "*.*")])
            else:
                path = filedialog.askopenfilename(filetypes=[("All files", "*.*")])
        else:
            path = filedialog.askdirectory()
        if path:
            var.set(path)

    def update_log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            try:
                if platform.system() == "Windows":
                    os.startfile(self.last_output_dir)
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", self.last_output_dir])
                else:
                    subprocess.Popen(["xdg-open", self.last_output_dir])
                self.update_log(f"已打开输出目录: {self.last_output_dir}")
            except Exception as e:
                messagebox.showerror("错误", f"无法打开目录: {e}")
                self.update_log(f"错误：无法打开目录 {self.last_output_dir}: {e}")
        else:
            messagebox.showinfo("提示", "没有可打开的输出目录或目录不存在。请先成功打包。")
            self.update_log("警告：无法打开输出目录，可能未成功打包或目录已不存在。")

    def update_elapsed_time_display(self):
        if self.start_build_time is not None:
            elapsed_seconds = int(time.time() - self.start_build_time)
            hours, remainder = divmod(elapsed_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.elapsed_time_label.config(text=f"预计时间: {hours:02}:{minutes:02}:{seconds:02}")
            self.timer_id = self.root.after(1000, self.update_elapsed_time_display)
        else:
            self.elapsed_time_label.config(text="预计时间: 00:00:00")

    def cancel_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.start_build_time = None

    def start(self):
        self.update_log("--- 开始打包任务 ---")
        self.open_output_button.config(state='disabled') 
        self.last_output_dir = "" 
        
        self.start_build_time = time.time()
        self.update_elapsed_time_display()

        urls = self.url_text.get("1.0", "end").strip().splitlines()
        if not urls:
            messagebox.showerror("错误", "请输入至少一个网址")
            self.update_log("错误：未输入网址。")
            self.cancel_timer() 
            return

        output_dir = self.fields["output"].get()
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            self.update_log("错误：未选择输出目录。")
            self.cancel_timer() 
            return
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            self.update_log(f"确保输出目录存在: {output_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"无法创建输出目录: {e}")
            self.update_log(f"错误：无法创建输出目录: {e}")
            self.cancel_timer() 
            return

        use_custom_splash = self.use_splash_screen.get()
        splash_html_path = self.fields["splash_html"].get() 
        increase_volume_enabled = self.increase_volume.get()

        dummy_file_path = None
        if increase_volume_enabled:
            dummy_file_size_mb = 300
            dummy_file_size_bytes = dummy_file_size_mb * 1024 * 1024
            dummy_file_path = os.path.join(tempfile.gettempdir(), "dummy_data.bin")
            try:
                self.update_log(f"正在创建 {dummy_file_size_mb}MB 虚拟文件以增大体积: {dummy_file_path}")
                with open(dummy_file_path, "wb") as f:
                    chunk_size = 1024 * 1024
                    for _ in range(dummy_file_size_mb):
                        f.write(os.urandom(chunk_size))
                self.update_log("虚拟文件创建成功。")
                actual_size = os.path.getsize(dummy_file_path)
                self.update_log(f"实际创建文件大小: {actual_size / (1024 * 1024):.2f} MB")
                if actual_size < dummy_file_size_bytes:
                    raise Exception("Dummy file created with insufficient size.")
            except Exception as e:
                messagebox.showwarning("警告", f"无法创建虚拟文件以增大体积: {e}\n打包将继续，但不会增大体积。")
                self.update_log(f"警告：无法创建虚拟文件: {e}。功能将禁用。")
                increase_volume_enabled = False


        for idx, url in enumerate(urls):
            if not url.strip():
                self.update_log(f"跳过空网址行：{idx+1}")
                continue
            
            self.update_log(f"正在处理网址: {url}")
            title = self.fields["title"].get() or f"App{idx+1}"
            version = self.fields["version"].get()
            company = self.fields["company"].get()
            desc = self.fields["desc"].get()
            icon = self.fields["icon"].get()
            winicon_raw = self.fields["winicon"].get()
            
            winicon_clean_path = winicon_raw.replace('\\', '/') if winicon_raw else ""

            use_webview_enabled = self.use_webview.get()

            script_code_for_packaging = self.build_startup_script_content(
                url, title, company, winicon_clean_path, use_webview_enabled, use_custom_splash, splash_html_path
            )
            
            temp_dir = tempfile.gettempdir()
            script_path = os.path.join(temp_dir, f"web2exe_final_startup_temp_{idx}.py")
            
            try:
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script_code_for_packaging)
                self.update_log(f"临时启动脚本已生成: {script_path}")
            except Exception as e:
                messagebox.showerror("错误", f"无法写入临时启动脚本: {e}")
                self.update_log(f"错误：无法写入临时启动脚本: {e}")
                self.cancel_timer() 
                continue

            cmd = ["pyinstaller", "--noconfirm", "--onefile", "--noconsole", script_path, "--name", title]
            
            if icon:
                cmd += ["--icon", icon]
                self.update_log(f"设置程序图标: {icon}")
            
            cmd += ["--distpath", output_dir]

            if use_custom_splash and splash_html_path and os.path.exists(splash_html_path):
                splash_html_dir = os.path.dirname(splash_html_path)
                cmd += ["--add-data", f"{splash_html_dir}{os.pathsep}."]
                self.update_log(f"捆绑自定义启动页面资源: {splash_html_dir} 到应用根目录")
            
            if increase_volume_enabled and dummy_file_path and os.path.exists(dummy_file_path):
                cmd += ["--add-data", f"{dummy_file_path}{os.pathsep}."]
                self.update_log(f"捆绑 {dummy_file_size_mb}MB 虚拟文件: {dummy_file_path}")
                cmd += ["--noupx"]
                self.update_log("已添加 --noupx 标志，确保虚拟文件不会被压缩。")

            self.update_log(f"PyInstaller 命令: {' '.join(cmd)}")

            def run_build_thread(current_cmd, current_title, current_script_path, output_dir_for_button, current_dummy_file_path):
                self.status.config(text=f"正在打包：{current_title}...")
                
                try:
                    process = subprocess.Popen(current_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

                    def read_stream(stream, prefix):
                        for line in iter(stream.readline, ''):
                            self.root.after(0, self.update_log, f"[{prefix}] {line.strip()}")
                        stream.close()

                    stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, "PyInstaller"))
                    stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "PyInstaller ERROR"))

                    stdout_thread.start()
                    stderr_thread.start()

                    process.wait()
                    
                    stdout_thread.join()
                    stderr_thread.join()

                    if process.returncode == 0:
                        self.status.config(text=f"✅ 打包完成：{current_title}")
                        self.update_log(f"打包成功 for {current_title}")
                        self.last_output_dir = output_dir_for_button
                        self.root.after(0, lambda: self.open_output_button.config(state='normal'))
                        
                        try:
                            os.remove(current_script_path)
                            self.update_log(f"已删除临时脚本: {current_script_path}")
                        except OSError as e:
                            self.update_log(f"警告：无法删除临时脚本 {current_script_path}: {e}")

                    else:
                        self.status.config(text=f"❌ 打包出错：{current_title}")
                        self.update_log(f"打包失败 for {current_title}。错误码: {process.returncode}")
                        self.root.after(0, lambda: messagebox.showerror("打包失败", f"打包 {current_title} 失败。请检查日志。"))

                except FileNotFoundError:
                    self.status.config(text="❌ 错误：未找到 PyInstaller 命令。请确保它已安装并添加到系统 PATH 中。") 
                    self.update_log("错误：PyInstaller 命令未找到。请确保它已安装并添加到 PATH。")
                    self.root.after(0, lambda: messagebox.showerror("错误", "未找到 PyInstaller 命令。请确保它已安装并添加到系统 PATH 中。"))
                except Exception as e:
                    self.status.config(text=f"❌ 打包出错：{str(e)}")
                    self.update_log(f"未知错误：{str(e)}")
                    self.root.after(0, lambda: messagebox.showerror("错误", f"打包过程中发生未知错误: {e}"))
                finally: 
                    self.root.after(0, self.cancel_timer)
                    if current_dummy_file_path and os.path.exists(current_dummy_file_path):
                        try:
                            os.remove(current_dummy_file_path)
                            self.update_log(f"已删除虚拟文件: {current_dummy_file_path}")
                        except OSError as e:
                            self.update_log(f"警告：无法删除虚拟文件 {current_dummy_file_path}: {e}")
                self.update_log("--- 单个打包任务结束 ---")

            threading.Thread(target=run_build_thread, args=(cmd, title, script_path, output_dir, dummy_file_path)).start()
        
        self.update_log("--- 所有打包任务已提交 ---")


    def build_startup_script_content(self, url, title, company_name, winicon_path_clean, use_webview_flag, use_custom_splash, splash_html_path_param):
        
        use_html_splash_only = use_custom_splash and bool(splash_html_path_param) and os.path.exists(splash_html_path_param)

        imports = [
            "import sys",
            "import platform",
            "import os",
            "import threading"
        ]
        if use_html_splash_only:
            imports.append("import tkinter as tk")

        if use_webview_flag:
            imports.append("import webview")
            if platform.system() == 'Windows':
                imports.append("import ctypes")
        else:
            imports.append("import webbrowser")

        imports_str = "\n".join(imports)

        startup_script_body = ""

        if use_html_splash_only: 
            splash_filename = os.path.basename(splash_html_path_param)
            
            startup_script_body = f"""
class Api:
    def close_splash_and_launch(self, url, title, winicon_param, use_webview_flag_js):
        global splash_window
        if splash_window:
            splash_window.destroy()
            splash_window = None

        if use_webview_flag_js:
            if platform.system() == 'Windows' and winicon_param:
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('myappid')
                except AttributeError:
                    pass
            webview.create_window(title, url, width=1024, height=720) 
            webview.start()
        else:
            webbrowser.open(url)
            sys.exit()

if __name__ == '__main__':
    global splash_window
    root = tk.Tk()
    root.withdraw()

    splash_window = webview.create_window('Loading...', f"file://{{os.path.join(sys._MEIPASS, '{splash_filename}')}}", 
                                          width=500, height=300, frameless=True, resizable=False, easy_drag=True, 
                                          js_api=Api(), hidden=True)

    def on_splash_loaded():
        screen_width = webview.screens[0].width if webview.screens else root.winfo_screenwidth()
        screen_height = webview.screens[0].height if webview.screens else root.winfo_screenheight()
        
        splash_window.move((screen_width - 500) // 2, (screen_height - 300) // 2)
        splash_window.show()
        
    splash_window.loaded += on_splash_loaded
    
    webview.start(splash_window, gui='tk', debug=False)
"""
        else:
            if use_webview_flag:
                icon_code = ""
                if platform.system() == 'Windows' and winicon_path_clean:
                    icon_code = "import ctypes\ntry:\n    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('myappid')\nexcept AttributeError: pass"
                startup_script_body = f"""
import webview
{icon_code}
if __name__ == '__main__':
    webview.create_window("{title}", "{url}", width=1024, height=720) 
    webview.start()
"""
            else:
                startup_script_body = f"""
import webbrowser
import sys
if __name__ == '__main__':
    webbrowser.open('{url}')
    sys.exit()
"""
        return imports_str + "\n" + startup_script_body


if __name__ == "__main__":
    root = tk.Tk()
    app = Web2ExeApp(root)
    root.mainloop()