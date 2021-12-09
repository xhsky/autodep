# Ext打包

## 说明

1. 下载时注意CPU架构不同(x86, arm)
2. 基于不同CPU架构编译不同的CPU架构软件



## 软件包

### Tomcat

- 从官网下载即可(https://tomcat.apache.org/download-80.cgi)



### ElasticSearch

- 官网下载即可(https://www.elastic.co/cn/downloads/elasticsearch)



### ffmpeg

1. 从官网下载即可(https://johnvansickle.com/ffmpeg/)
2. 重新解压缩, 将格式换为tar.gz格式



### Nacos

- 从官网下载即可(https://github.com/alibaba/nacos/releases)



### nacos_mysql_sql

- 用于支持Nacos的MySQL模式
- 建立`nacos_mysql_sql`, 将Nacos安装包内`conf/nacos-mysql.sql`拷贝入`nacos_mysql_sql`目录
- 编辑nacos-mysql.sql文件，将nacos用户密码改为`$2a$10$YEIvouR8SV/zDpsn885rou3af.SBub8o74j0xkgT04vvGHqR4j3yK`(DreamSoft_123)
- 打包: `tar -zcf nacos-mysql-sql-<version>.tar.gz nacos_mysql_sql`



### backup_tool

1. 目录结构为`backup_tool/{bin/backup.py,config,logs}`
2. `backup.py`文件可从`autodep/scripts/下获取`
3. 执行:`/opt/python3/bin/python3 bin/backup.py config/upload.json`



### Gluster

1. 建立`glusterfs-<version>`目录
2. 在该目录下建立`glusterfs_all`和`glusterfs_client`目录
3. 下载gluster安装包及其依赖至`glusterfs_all`目录
4. 下载gluster-client安装包及其依赖至`glusterfs_client`目录
5. 将`glusterfs-<version>`目录打包为`glusterfs-<version>-rpm.tar.gz`



### jdk

- 官网下载即可(https://www.oracle.com/java/technologies/javase/javase-jdk8-downloads.html)



### MySQL

1. 官网下载tar包(https://dev.mysql.com/downloads/mysql/)
2. 解压后在其目录建立`pkg`目录
3. 下载`libaio`包放入`pkg`目录
4. 重新打包为`mysql-<version>.tar.gz`



### Nginx

1. 按文档编译, 编译后目录为`/dream/nginx-<version>`
2. 打包后文件为`nginx-<version>-bin.tar.gz`



### Dialog

1. 建立`dialog`目录
2. 从系统内直接下载`dialog`安装包并移入
3. 将`dialog`目录移入`ext`即可



### Python3

- 按文档编译，编译后目录为`/opt/python3`

- python3目录:
  - 安装依赖
  
    ```
    # /opt/python3/bin/pip3 install psutil pythondialog requests paramiko
    bcrypt==3.2.0
    certifi==2021.10.8
    cffi==1.15.0
    charset-normalizer==2.0.9
    cryptography==36.0.0
    idna==3.3
    paramiko==2.8.1
    psutil==5.8.0
    pycparser==2.21
    PyNaCl==1.4.0
    pythondialog==3.5.3
    requests==2.26.0
    six==1.16.0
    urllib3==1.26.7
    ```
  
  - 将`python3`目录直接移入`ext`目录即可
  
- python3包: 
  - 在编译后目录下建立`code/libs`和`pkgs`目录
  
  - 安装依赖包
  
    ```shell
    # /opt/python3/bin/pip3 install psutil distro ntplib requests pyyaml paramiko
    bcrypt==3.2.0
    certifi==2021.10.8
    cffi==1.15.0
    charset-normalizer==2.0.9
    cryptography==36.0.0
    distro==1.6.0
    idna==3.3
    ntplib==0.4.0
    paramiko==2.8.1
    psutil==5.8.0
    pycparser==2.21
    PyNaCl==1.4.0
    PyYAML==6.0
    requests==2.26.0
    six==1.16.0
    urllib3==1.26.7
    ```
  
  - 安装`autocheck`依赖包
  
    ``` shell
    # /opt/python3/bin/pip3 install gevent psutil PyMySQL redis APScheduler prettytable requests
    APScheduler==3.8.1
    bcrypt==3.2.0
    certifi==2021.10.8
    cffi==1.15.0
    charset-normalizer==2.0.9
    cryptography==36.0.0
    Deprecated==1.2.13
    distro==1.6.0
    gevent==21.8.0
    greenlet==1.1.2
    idna==3.3
    ntplib==0.4.0
    paramiko==2.8.1
    prettytable==2.4.0
    psutil==5.8.0
    pycparser==2.21
    PyMySQL==1.0.2
    PyNaCl==1.4.0
    pytz==2021.3
    pytz-deprecation-shim==0.1.0.post0
    PyYAML==6.0
    redis==4.0.2
    requests==2.26.0
    six==1.16.0
    tzdata==2021.5
    tzlocal==4.1
    urllib3==1.26.7
    wcwidth==0.2.5
    wrapt==1.13.3
    zope.event==4.5.0
    zope.interface==5.4.0
    ```
  
  - 将其打包为`python3.tar.gz`并移入`ext`目录



### RabbitMQ

1. 按文档编译`erlang`, 编译后目录为`/dream/erlang-<version>`
2. 从官网下载rabbitmq(https://github.com/rabbitmq/rabbitmq-server/releases)解压
3. 将`erlang-<version>`目录移入rabbitmq解压目录，并做软连接(`ln -sv erlang-<version> erlang`)
4. 将rabbitmq目录打包为`rabbitmq-server-<version>.tar.gz`



### Redis

1. 按文档编译，编译后目录为`/dream/redis-<version>`
2. 将编译目录打包为`redis-<version>-bin.tar.gz`



### RocketMQ

1. 从官网下载(https://rocketmq.apache.org/release_notes/)
2. 更改`./bin/mqnamesrv`和`./bin/mqbroker`的最后一行`sh`为`bash`
3. 压缩格式改为tar.gz(解压后使用tar压缩, 仅后缀名更改)




## ext打包

1. 建立`ext`目录
2. 将以上打包好的各软件放入`ext`目录中
3. 根据操作系统及CPU架构不同，将`ext`目录打包为`ext-<version>-<dis>-<arch>.tar.gz`

