import os
import sys
import time
import threading
import subprocess
import configparser
import logging
import random
from paho.mqtt import client as mqtt_client
from logging.handlers import RotatingFileHandler

previous_clipboard = None

# 确保clientlogger文件夹存在
log_directory = 'clientlogger'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# 创建和配置日志
log_file_path = os.path.join(log_directory, 'client.log')
logger = logging.getLogger('ClientLogger')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(log_file_path, maxBytes=1048576, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# 创建配置解析器对象
config = configparser.ConfigParser()

# 读取配置文件
config.read('ClientConfig.ini')

# 创建MQTT客户端实例
client_id = f'python-mqtt-{random.randint(0, 1000)}'
client = mqtt_client.Client(client_id=client_id, clean_session=True, userdata=None, protocol=mqtt_client.MQTTv311, 
                            transport="tcp", callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)

# MQTT服务器地址和端口
mqtt_server_address = config['MQTT']['address']
mqtt_server_port = int(config['MQTT']['port'])

# MQTT主题
mqtt_topic_send = config['MQTT']['topic_send']
mqtt_topic_receive = config['MQTT']['topic_receive']



# 打印MQTT服务器地址和端口
logger.info(f"MQTT server address: {mqtt_server_address}")
logger.info(f"MQTT server port: {mqtt_server_port}")


# Windows平台的剪贴板读取函数
def get_clipboard_windows():
    try:
        return pyperclip.paste()
    except Exception as e:
        print(f"读取剪贴板时发生错误: {e}")
        # 可以根据需要返回一个默认值或者None
        return None

# Windows平台的剪贴板设置函数
def set_clipboard_windows(text):
    try:
        pyperclip.copy(text)
    except Exception as e:
        print(f"设置剪贴板时发生错误: {e}")

# macOS平台的剪贴板读取函数
def get_clipboard_mac():
    try:
        # 使用pbpaste命令读取剪贴板内容
        return subprocess.run(['pbpaste'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout.strip()
    except Exception as e:
        print(f"读取剪贴板时发生错误: {e}")
        # 可以根据需要返回一个默认值或者None
        return None

# macOS平台的剪贴板设置函数
def set_clipboard_mac(text):
    try:
        # 使用pbcopy命令设置剪贴板内容
        subprocess.run(['pbcopy'], input=text, universal_newlines=True)
    except Exception as e:
        print(f"设置剪贴板时发生错误: {e}")

# Linux平台的剪贴板读取函数
def get_clipboard_linux():
    env = os.environ.copy()
    env['DISPLAY'] = linux_display  # 用户DISPLAY环境变量的值
    env['XAUTHORITY'] = linux_xauthority  # 用户.Xauthority文件的路径
    try:
        process = subprocess.Popen(['xclip', '-selection', 'c', '-o'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            return stdout.decode('utf-8')
        else:
            logger.error("读取剪贴板失败：%s", stderr.decode('utf-8'))
            return ""
    except Exception as e:
        logger.exception("读取剪贴板时发生异常：%s", e)
        return ""

# Linux平台的剪贴板设置函数
def set_clipboard_linux(text):
    env = os.environ.copy()
    env['DISPLAY'] = linux_display  # 用户DISPLAY环境变量的值
    env['XAUTHORITY'] = linux_xauthority  # 用户.Xauthority文件的路径
    try:
        process = subprocess.Popen(['xclip', '-selection', 'c'],
                                   stdin=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        stdout, stderr = process.communicate(input=text.encode('utf-8'))
        if process.returncode != 0:
            logger.error("设置剪贴板失败：%s", stderr.decode('utf-8'))
    except Exception as e:
        logger.exception("设置剪贴板时发生异常：%s", e)


# 监视剪贴板内容的线程
def monitor_clipboard():
    global previous_clipboard
    while True:
        try:
            current_clipboard = get_clipboard()
            if current_clipboard != previous_clipboard:
                # 发布消息到MQTT主题
                client.publish(mqtt_topic_send, current_clipboard, qos=2)
                logger.info(f"Sent to MQTT: {current_clipboard}")
                previous_clipboard = current_clipboard
        except Exception as e:
            logger.error(f"Error sending data: {e}")

        time.sleep(1)  # 检查频率

# 连接到MQTT服务器
def connect_to_mqtt():
    global previous_clipboard
    # 接收MQTT消息的回调函数
    def on_message(client, userdata, msg):
        global previous_clipboard
        message = msg.payload.decode('utf-8')
        logger.info(f"Received from MQTT: {message}")
        previous_clipboard = message
        set_clipboard(message)
        
    # 连接到MQTT服务器的回调函数
    def on_connect(client, userdata, flags, reasonCode, properties):
        if reasonCode == 0:
            logger.info("Connected to MQTT server")
            # 订阅在on_connect()中意味着如果我们失去连接并重新连接，订阅将会被更新
            client.subscribe(mqtt_topic_receive, qos=2)
        else:
            logger.error(f"Failed to connect to MQTT server, return code {reasonCode}")
    try:
        # 设置MQTT客户端的回调函数
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(mqtt_server_address, mqtt_server_port, 60)
    except Exception as e:
        logger.error(f"Could not connect to MQTT server: {e}")


if __name__ == '__main__':

    # 根据平台选择合适的剪贴板功能函数
    if sys.platform == 'win32':
        import pyperclip
        get_clipboard = get_clipboard_windows
        set_clipboard = set_clipboard_windows
        logger.info("win32 platform")
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # 获取linux平台的环境变量
        linux_display = config['Env']['display']
        linux_xauthority = config['Env']['xauthority']
        get_clipboard = get_clipboard_linux
        set_clipboard = set_clipboard_linux
        logger.info("linux platform")
    elif sys.platform == 'darwin':  # macOS平台
        get_clipboard = get_clipboard_mac
        set_clipboard = set_clipboard_mac
        logger.info("macOS platform")
    else:
        raise NotImplementedError("该平台不支持剪贴板操作。")

    # 初始化剪贴板内容
    previous_clipboard = None

    
    try:
        connect_to_mqtt()
        # 开始MQTT客户端网络循环
        client.loop_start()

        # 创建一个线程来监控剪贴板
        clipboard_thread = threading.Thread(target=monitor_clipboard)
        clipboard_thread.daemon = True
        clipboard_thread.start()

        # 主线程等待上面的线程
        clipboard_thread.join()

    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"发生错误: {e}")
    finally:
        client.disconnect()
        client.loop_stop()
        logger.info("MQTT loop stopped")
        sys.exit()