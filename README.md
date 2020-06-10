# 自动化部署
用于自动化部署集群

## 说明
1. 本项目基于Centos7系统, x86架构测试, 用于自动安装, 配置, 优化常用软件
2. 本站点提供的形如`autodep-version-x64.tar.gz`文件为安装包
3. 本文所有操作均使用root用户

## 功能
1. 当前支持软件: nginx, jdk, tomcat, ffmpeg, redis, glusterfs, mysql
2. 当前支持集群: web集群(nginx+tomcat), redis主从-哨兵集群, glusterfs镜像集群, MySQL主从集群
3. 支持自动配置, 自动优化, 自动安装

## 部署安装
1. 将安装包上传至某台服务器上
2. 解压
```
# tar -xf autodep-1.0-x84.tar.gz
# cd autodep-1.0/autodep
```
3. 编辑初始化配置文件, 指定集群中各个主机
```
# vim config/init.json
{
  "local_name": "web",
  "web":{
    "ip":"192.168.1.203", 
    "root_password":"111111", 
    "port":22
  },
  "web1":{
    "ip":"192.168.1.107", 
    "root_password":"111111", 
    "port":22
  },
  "web2":{
    "ip":"192.168.1.204", 
    "root_password":"111111", 
    "port":22
  },
  "redis1":{
    "ip":"192.168.1.206", 
    "root_password":"111111", 
    "port":22
  },
  "redis2":{
    "ip":"192.168.1.207", 
    "root_password":"111111", 
    "port":22
  },
  "data1":{
    "ip":"192.168.1.210", 
    "root_password":"111111", 
    "port":22
  },
  "data2":{
    "ip":"192.168.1.102", 
    "root_password":"111111", 
    "port":22
  },
  "db1":{
    "ip":"192.168.1.214", 
    "root_password":"111111", 
    "port":22
  },
  "db2":{
    "ip":"192.168.1.209", 
    "root_password":"111111", 
    "port":22
  }
} 

```

4. 编辑架构配置文件, 指定集群架构
```
# vim config/arch.json
```

5. 初始化
```
# ./init.py
检测配置文件中账号端口等信息, 请等待...                                                                                                                                       
主机初始化..                                                                                                                                                                  
本机生成密钥对                                                                                                                                                                
                                                                                                                                                                              
主机web环境初始化...                                                                                                                                                          
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为web完成                                                                                                                                                           
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
主机web1环境初始化...                                                                                                                                                         
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为web1完成                                                                                                                                                          
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 

主机web2环境初始化...
免密码登录设置完成
配置Python3环境完成
设置主机名为web2完成
关闭防火墙完成
关闭SELinux完成
用户权限已提升
hosts配置完成

主机redis1环境初始化...                                                                                                                                                       
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为redis1完成                                                                                                                                                        
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 

主机redis2环境初始化...
免密码登录设置完成
配置Python3环境完成
设置主机名为redis2完成
关闭防火墙完成
关闭SELinux完成
用户权限已提升
hosts配置完成

主机data1环境初始化...
免密码登录设置完成
配置Python3环境完成
设置主机名为data1完成
关闭防火墙完成
关闭SELinux完成
用户权限已提升
hosts配置完成

主机data2环境初始化...                                                                                                                                                        
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为data2完成                                                                                                                                                         
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
主机db1环境初始化...                                                                                                                                                          
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为db1完成                                                                                                                                                           
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
主机db2环境初始化...                                                                                                                                                          
免密码登录设置完成                                                                                                                                                            
配置Python3环境完成                                                                                                                                                           
设置主机名为db2完成                                                                                                                                                           
关闭防火墙完成                                                                                                                                                                
关闭SELinux完成                                                                                                                                                               
用户权限已提升                                                                                                                                                                
hosts配置完成                                                                                                                                                                 
                                                                                                                                                                              
初始化完成             

各主机信息如下:                                                                                                                                                               
主机名: web                                                                                                                                                                   
发行版:         CentOS Linux release 7.5.1804 (Core)                                                                                                                          
内核版本:       3.10.0-862.14.4.el7.x86_64                                                                                                                                    
CPU核心数:      8(0.5%)                                                                                                                                                       
内存大小:       9.61G(5.9%)                                                                                                                                                   
磁盘(/):        896.29G(0.7%)                                                                                                                                                 
磁盘(/boot):    1014.00M(16.8%)                                                                                                                                               
                                                                                                                                                                              
主机名: web1                                                                                                                                                                  
发行版:         CentOS Linux release 7.5.1804 (Core)                                                                                                                          
内核版本:       3.10.0-862.14.4.el7.x86_64                                                                                                                                    
CPU核心数:      8(0.0%)                                                                                                                                                       
内存大小:       9.61G(4.7%)                                                                                                                                                   
磁盘(/):        896.29G(0.2%)                                                                                                                                                 
磁盘(/boot):    1014.00M(16.8%)                                                                                                                                               
                                                                                                                                                                              
主机名: web2                                                                                                                                                                  
发行版:         CentOS Linux release 7.5.1804 (Core)                                                                                                                          
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.0%)
内存大小:       9.61G(4.8%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: redis1
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.0%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: redis2                                                                                                                                                                
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.6%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: data1
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.0%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: data2
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.6%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: db1
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

主机名: db2
发行版:         CentOS Linux release 7.5.1804 (Core)
内核版本:       3.10.0-862.14.4.el7.x86_64
CPU核心数:      8(0.1%)
内存大小:       9.61G(4.7%)
磁盘(/):        896.29G(0.2%)
磁盘(/boot):    1014.00M(16.8%)

```

5. 开始部署
```
# ./main.py
[root@node autodep]# ./main.py                                                                                                                                                
开始集群部署...                                                                                                                                                               
                                                                                                                                                                              
web部署...                                                                                                                                                                    
                                                                                                                                                                              
安装并配置nginx...                                                                                                                                                            
nginx安装完成                                                                                                                                                                 
nginx配置优化完成                                                                                                                                                             
                                                                                                                                                                              
web1部署...                                                                                                                                                                   
                                                                                                                                                                              
安装并配置jdk...                                                                                                                                                              
jdk安装完成                                                                                                                                                                   
jdk配置完成                                                                                                                                                                   
                                                                                                                                                                              
安装并配置tomcat...                                                                                                                                                           
Tomcat安装完成                                                                                                                                                                
Tomcat配置环境变量完成                                                                                                                                                        
Tomcat配置优化完成                                                                                                                                                            
                                                                                                                                                                              
安装并配置ffmpeg...                                                                                                                                                           
ffmpeg安装完成                                                                                                                                                                
                                                                                                                                                                              
web2部署...                                                                                                                                                                   
                                                                                                                                                                              
安装并配置jdk...                                                                                                                                                              
jdk安装完成                                                                                                                                                                   
jdk配置完成           

安装并配置tomcat...
Tomcat安装完成
Tomcat配置环境变量完成
Tomcat配置优化完成

安装并配置ffmpeg...
ffmpeg安装完成

redis1部署...

安装并配置redis...
Redis安装完成
Redis配置环境变量完成
Sentinel安装配置完成
Redis(master)配置优化完成

redis2部署...

安装并配置redis...
Redis安装完成
Redis配置环境变量完成
Sentinel安装配置完成
Redis(slave)配置优化完成

data1部署...
安装并配置glusterfs...
GlusterFS安装完成

data2部署...

安装并配置glusterfs...
GlusterFS安装完成

db1部署...

安装并配置mysql...
MySQL安装完成
MySQL配置完成

db2部署...

安装并配置mysql...
MySQL安装完成
MySQL配置完成

开始集群启动...

web部署...

启动并配置nginx...
nginx启动完成

web1部署...
启动并配置jdk...                                                                                                                                                              
jdk无须启动

启动并配置tomcat...
Tomcat启动完成

启动并配置ffmpeg...
ffmpeg无须启动

web2部署...
                                                                                                
启动并配置jdk...
jdk无须启动                                                                                     
            
启动并配置tomcat...                                                                             
Tomcat启动完成
                                                                                                
启动并配置ffmpeg...
ffmpeg无须启动

redis1部署...                                                                                             

启动并配置redis...
Redis(master)启动成功
Sentinel启动成功

redis2部署...

启动并配置redis...
Redis(slave)启动成功
Sentinel启动成功

data1部署...

启动并配置glusterfs...
GlusterFS共享存储创建成功
Mounting glusterfs on /data_mount failed.
Error: GlusterFS客户端挂载失败

data2部署...

启动并配置glusterfs...
Mounting glusterfs on /data_mount failed.
Error: GlusterFS客户端挂载失败

db1部署...

启动并配置mysql...
MySQL初始化中...
MySQL更改初始密码完成
MySQL用户配置完成
MySQL(master)配置完成

db2部署...

启动并配置mysql...
MySQL初始化中...
MySQL更改初始密码完成
MySQL用户配置完成
MySQL(slave)配置完成
```


## 配置文件信息
```

```

## 

