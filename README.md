# ClipSync

## 为啥有这个小项目？

个人主力机是win11，然后有台ubuntu机器做做实验用，一般就用todesk远程连接比较方便，但是！！不管是todesk还是向日葵，竟然都不支持win和linux共享剪切板！！！这实在不能忍，太不方便了，反正就接受一点文字数据，想想很简单，就自己做了这个小工具，纯纯自用，所以安全性不高。

## 项目架构

偷懒不画图了，比较简单，就是通过mqtt协议转发两台机器的剪切板数据。

## 使用说明

1. 找一台闲置服务器安装mosquitto，运行后记得打开防火墙端口即可

2. 需要共享剪切板的两台机器，下载文件后，编译成可执行文件

   ```bash
   pyinstaller --onefile --add-data "Client/ClientConfig.ini:." Client/ClipsyncClient.py
   ```

3. 填写配置文件

   1. win就填写一下服务器地址，端口号，发送接受主题即可

   2. ubuntu里还需要多加环境变量，因为我的GUI框架是用的X11，需要额外的环境变量

      ```ini
      [Env]
      display = :1
      xauthority = /run/user/1000/gdm/Xauthority
      ```

4. 自启动

   1. win的话，在自启动文件夹里，写一个vbs，启动对应可执行文件即可
   2. ubunut可以写成service，很方便