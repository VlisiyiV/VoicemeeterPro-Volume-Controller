# voicemeeter_memory.py
import threading
import time
from pymem import Pymem
from pymem.exception import ProcessNotFound
import maliang
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import psutil
from pymem.exception import ProcessNotFound, MemoryWriteError

# 读取上次音量
from platformdirs import user_data_dir
import os
config_dir = user_data_dir("VoicemeeterGainControl")
os.makedirs(config_dir, exist_ok=True)
config_path = os.path.join(config_dir, "vol.txt")



# === 配置 ===
PROCESS_NAME = "voicemeeterpro.exe"  # 进程名称
OFFSET_A1 = 0x9CA68                  # A1增益偏移地址
OFFSET_A2 = 0x9CAC8                  # A2增益偏移地址
ICON_PATH = r"C:\Users\lisiy\Desktop\编程\Python\VoicemeeterPro音量控制器\icon.ico"

# 全局变量
pm = None # Pymem对象
base_addr = None # 模块基址
running = True # 运行标志

Vol_Main = 0.00
Vol_A1 = 0.00
Vol_A2 = 0.00

RunGuiSignal = threading.Event()# 运行Gui标志
IamDied = False

try:
    def KillYouSelf():# 结束程序
        global IamDied
        IamDied = True

    def linmap(x, in_min, in_max, out_min, out_max):# 线性映射
        """
        将 x 从 [in_min, in_max] 线性映射到 [out_min, out_max]
        """
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def dB2Linear(db):# 将dB值转换为线性增益
        """将dB值转换为线性增益"""
        if db <= -60.0:
            return 0.0
        return 10.0 ** (db / 20.0)

    def WriteGains(master_db, a1_db, a2_db):# 写入增益值
        """
        写入增益值到内存
        :param master_db: 主增益 (dB)
        :param a1_db: A1通道增益 (dB)
        :param a2_db: A2通道增益 (dB)
        :return: 是否成功
        """
        global pm, base_addr
        
        if pm is None or base_addr is None:
            return False
        
        try:
            # 主增益作用于 A1/A2：最终 = 主增益 + 通道增益（dB 相加）
            if master_db != -60.0:
                if a1_db != -60.0:
                    final_a1 = master_db + a1_db
                else:
                    final_a1 = -60.0
                if a2_db != -60.0:
                    final_a2 = master_db + a2_db
                else:
                    final_a2 = -60.0
            else:
                final_a1 = -60.0
                final_a2 = -60.0
            
            # 限制在 [-60, 12]
            final_a1 = max(-60.0, min(20.0, final_a1))
            final_a2 = max(-60.0, min(20.0, final_a2))
            
            # 转换为线性值并写入内存
            pm.write_float(base_addr + OFFSET_A1, dB2Linear(final_a1))
            pm.write_float(base_addr + OFFSET_A2, dB2Linear(final_a2))
            return True
        except (MemoryWriteError, Exception) as e:
            print(f"写入失败: {e}")
            # 写入失败时，重置连接
            if pm is not None:
                try:
                    pm.close()
                except:
                    pass
            pm = None
            base_addr = None
            return False
        
    def WriteVol(max_db, master_vol, a1_vol, a2_vol):# 写入音量
        """写入当前音量到内存"""
        return WriteGains(linmap(master_vol, 0, 100, -60, max_db),
                          linmap(a1_vol,     0, 100, -60, max_db),
                          linmap(a2_vol,     0, 100, -60, max_db))

    def isProcessRunning():# 获取进程连接状态
        """获取进程连接状态"""
        global pm
        return pm is not None

    def MemoryInjectionToVoicemeeter():# 后台注入Voicemeeter进程
        """后台连接Voicemeeter进程"""
        global pm, base_addr, running

        try:
            while running:
                if pm is None:
                    try:
                        pm = Pymem(PROCESS_NAME)
                        base_addr = pm.process_base.lpBaseOfDll
                        print("成功注入到 VoicemeeterPro")
                    except ProcessNotFound:
                        print("未找到 VoicemeeterPro 进程")
                        time.sleep(1)
                else:
                    # 检查进程是否仍然存在
                    try:
                        # 尝试读取进程ID来验证连接是否仍然有效
                        pid = pm.process_id
                        if not psutil.pid_exists(pid):
                            print("VoicemeeterPro 进程已终止，正在重新连接...")
                            pm.close()
                            pm = None
                            base_addr = None
                    except Exception:
                        # 如果检查失败，也认为连接已断开
                        print("VoicemeeterPro 连接已断开，正在重新连接...")
                        pm = None
                        base_addr = None
                    
                    time.sleep(1)
        except Exception as e:
            print(f"后台注入失败: {e}")

    def StartBackgroundInjection():# 狠狠地向Voicemeeter注入爱国基因!
        """启动后台连接线程"""
        threading.Thread(target=MemoryInjectionToVoicemeeter, daemon=True).start()

    def StopBackgroundInjection():# 停止注入内存
        """停止后台连接"""
        global running
        running = False

    def create_tray_icon():# 创建托盘图标
        """创建托盘图标"""

        icon_image = None
        if ICON_PATH and os.path.isfile(ICON_PATH):
            try:
                icon_image = Image.open(ICON_PATH)
            except Exception as e:
                print(f"图标加载失败: {e}")
        
        if icon_image is None:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((16, 16, 48, 48), fill="lightblue")
            icon_image = img

        menu = Menu(MenuItem("打开软件", lambda:{RunGuiSignal.set()}, default=True),
                    MenuItem("退出", lambda:{KillYouSelf(), RunGuiSignal.set(), icon.stop()}))

        icon = Icon(
            name="VoicemeeterPro 音量控制器",
            icon=icon_image,
            title="VoicemeeterPro 音量控制器",
            menu=menu
        )
        return icon

    def GUI():# 图形用户界面
        global Vol_Main, Vol_A1, Vol_A2, IamDied
        if IamDied: return()

        def ChangeVol(Slider, Text, num, id):# 改变音量
            global Vol_Main, Vol_A1, Vol_A2
            if Slider:
                Slider.set(num/100)
            if Text:
                Text.set(f"{int(num)}%")
            match id:
                case 0: Vol_Main = num; 
                case 1: Vol_A1 = num
                case 2: Vol_A2 = num
            if isProcessRunning(): # 如果进程连接正常
                WriteVol(12, Vol_Main, Vol_A1, Vol_A2)
        
        def SaveVol():# 保存上次音量
            # while RunGuiSignal.is_set():
                # time.sleep(2)
                try:
                    with open(config_path, "w") as f:
                        # f.write(f"{vol_Main_Text.get()[:-1]}\n{vol_A1_Text.get()[:-1]}\n{vol_A2_Text.get()[:-1]}")
                        f.write(f"{50}\n{vol_A1_Text.get()[:-1]}\n{vol_A2_Text.get()[:-1]}")
                        print("已保存配置文件")
                except Exception as e:
                    print(f"保存配置文件失败: {e}")
                root.after(1000, SaveVol)
            # print("已停止保存配置文件")

        root = maliang.Tk(title="VoicemeeterPro 音量控制器", size=(720, 480))# 创建窗口
        root.center()# 居中
        root.minsize(720, 480)

        # 创建画布
        cv = maliang.Canvas(auto_zoom=True,   # 自动缩放
                            keep_ratio="min", # 保持宽高比
                            free_anchor=True) # 允许自由锚点
        # 放置画布
        cv.place(width=720,  # 宽度
                height=480, # 高度
                x=720/2,    # 锚点X坐标
                y=480/2,    # 锚点Y坐标
                anchor="center") # 锚点位置: 中心

        # 主增益
        # maliang.Text(cv, (30,30), fontsize=30, text="主增益:")
        # maliang.Slider(cv,
        #             (150,30),
        #             size=(400,50),
        #             default=Vol_Main/100,
        #             command=lambda value: ChangeVol(None, vol_Main_Text, int(value*100), 0))
        # vol_Main_Text = maliang.Text(cv, (560,30), fontsize=30, text=f"{Vol_Main}%")

        # A1增益
        maliang.Text(cv, (30,100), fontsize=30, text="A1增益:")
        maliang.Slider(cv,
                    (150,100),
                    size=(400,50),
                    default=Vol_A1/100,
                    command=lambda value: ChangeVol(None, vol_A1_Text, int(value*100), 1))
        vol_A1_Text = maliang.Text(cv, (560,100), fontsize=30, text=f"{Vol_A1}%")

        # A2增益
        maliang.Text(cv, (30,170), fontsize=30, text="A2增益:")
        maliang.Slider(cv,
                    (150,170),
                    size=(400,50),
                    default=Vol_A2/100,
                    command=lambda value: ChangeVol(None, vol_A2_Text, int(value*100), 2))
        vol_A2_Text = maliang.Text(cv, (560,170), fontsize=30, text=f"{Vol_A2}%")


        # threading.Thread(target=SaveVol, daemon=True).start()# 创建保存音量文件线程

        root.after(1000,SaveVol)



        root.mainloop()

    def SysVol2VoicemetterVol():# 系统音量转Voicemeeter音量
        try:
            from ctypes import cast, POINTER
            # 从 comtypes 库直接导入所需常量和类
            from comtypes import CLSCTX_ALL, CLSCTX_INPROC_SERVER, CoCreateInstance 
            from pycaw.pycaw import IAudioEndpointVolume, IMMDeviceEnumerator
            # 从 pycaw 的 constants 模块导入设备枚举器的 CLSID（类标识符）
            from pycaw.constants import CLSID_MMDeviceEnumerator
            global Vol_Main, Vol_A1, Vol_A2
            
            # 初始化设备和接口变量
            device = None
            volume = None
            enumerator = None
            
            while True:
                try:
                    # 只有在设备为空或之前出错时才重新创建枚举器和设备
                    if device is None or volume is None:
                        # 创建音频设备枚举器
                        enumerator = CoCreateInstance(
                            CLSID_MMDeviceEnumerator,
                            IMMDeviceEnumerator,  
                            CLSCTX_INPROC_SERVER
                        )

                        # 获取默认音频输出端点
                        # 0 = eRender（表示播放设备），1 = eConsole（默认多媒体设备角色）
                        device = enumerator.GetDefaultAudioEndpoint(0, 1)

                        # 为该设备激活 IAudioEndpointVolume 接口
                        # 传入 IAudioEndpointVolume 类的内部接口 ID（_iid_）
                        interface = device.Activate(
                            IAudioEndpointVolume._iid_,
                            CLSCTX_ALL,  # 从 comtypes 导入
                            None
                        )

                        # 将返回的接口指针转换为可使用的 Python COM 对象
                        volume = cast(interface, POINTER(IAudioEndpointVolume))
                        print(volume)

                    # 获取当前主音量（返回 0.0 到 1.0 之间的浮点数）
                    current_volume_scalar = volume.GetMasterVolumeLevelScalar()

                    # 转换为百分比并打印
                    volume_percent = current_volume_scalar * 100

                    Vol_Main = int(volume_percent)

                    WriteVol(12, Vol_Main, Vol_A1, Vol_A2)
                    # print(f"音量{Vol_Main},{Vol_A1},{Vol_A2}")

                    # print(f"当前系统音量: {volume_percent:.0f}%")
                    time.sleep(.1)
                    
                except Exception as audio_error:
                    # 重置设备和接口以便下次重新初始化
                    device = None
                    volume = None
                    enumerator = None
                    print(f"音频设备访问错误: {audio_error}")
                    time.sleep(2)  # 出错后等待更长时间
                    
        except Exception as e:
            print(f"系统音量转Voicemeeter音量出错: {e}")

    def GetLastVol():
        global Vol_Main, Vol_A1, Vol_A2
        # 读取上次音量
        try:
            with open(config_path, "r") as f:
                # vol_Main_Slider.set(int(f.readline())/100); vol_Main_Text.set(f"{int(vol_Main_Slider.get()*100)}%")
                # vol_A1_Slider.set(int(f.readline())/100); vol_A1_Text.set(f"{int(vol_A1_Slider.get()*100)}%")
                # vol_A2_Slider.set(int(f.readline())/100); vol_A2_Text.set(f"{int(vol_A2_Slider.get()*100)}%")
                # ChangeVol(vol_Main_Slider, vol_Main_Text, int(f.readline()), 0)
                # ChangeVol(vol_A1_Slider, vol_A1_Text, int(f.readline()), 1)
                # ChangeVol(vol_A2_Slider, vol_A2_Text, int(f.readline()), 2)
                Vol_Main, Vol_A1, Vol_A2 = int(f.readline()), int(f.readline()), int(f.readline())
                print(f"已读取上次音量: {Vol_Main*100:.0f}% {Vol_A1*100:.0f}% {Vol_A2*100:.0f}%")

        except FileNotFoundError:# 音量配置文件不存在
            print("未找到配置文件，已创建默认配置文件")
            with open(config_path, "w") as f:
                f.write("0\n0\n0")
        except Exception as e:# 其他错误
            print(f"读取配置文件失败: {e}")
            with open(config_path, "w") as f:
                f.write("0\n0\n0")

    GetLastVol()

    # 尝试内存注入
    StartBackgroundInjection()

    def tray():
        try: 
            create_tray_icon().run()
        except Exception as e:
            print(f"创建托盘图标出错: {e}")
            return None

    # 创建托盘图标线程
    threading.Thread(target=tray, daemon=True).start()

    # 将系统音量转Voicemeeter音量
    threading.Thread(target=SysVol2VoicemetterVol, daemon=True).start()


    while not IamDied:# 循环直到IamDied
        RunGuiSignal.wait()# 等待信号
        GUI()# 运行GUI
        RunGuiSignal.clear()# 清空信号
    print("程序退出")
except Exception as e:
    print(f"程序出错: {e}")

finally:# 退出
    print("清理线程...")
    StopBackgroundInjection()# 停止后台注入


# # 使用示例:
# if __name__ == "__main__":
#     # 启动后台连接
#     start_background_connection()
    
#     try:
#         # 等待连接
#         print("正在连接到 VoicemeeterPro...")
#         time.sleep(.1)
        
#         if get_process_status():
#             print("测试写入增益值...")
#             # 测试写入: 主增益 0dB, A1 0dB, A2 0dB
#             success = write_gains(0.0, 0.0, 0.0)
#             print(f"写入结果: {'成功' if success else '失败'}")
            
#             # 测试写入: 主增益 -6dB, A1 +3dB, A2 -3dB
#             time.sleep(1)
#             success = write_gains(-6.0, 3.0, -3.0)
#             print(f"写入结果: {'成功' if success else '失败'}")
#         else:
#             print("连接失败，无法写入增益")
    
#     finally:
#         # 清理
#         stop_background_connection()
#         print("程序退出")