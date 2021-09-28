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



### Python3

- 按文档编译，编译后目录为`/opt/python3`

- python3目录:
  - 使用`pip3`安装`paramiko`, `psutil`, `pythondialog`和`requests`
  - 将`python3`目录直接移入`ext`目录即可
- python3包: 
  - 在编译后目录下建立`code/libs`和`pkgs`目录
  - 使用`pip3`安装`psutil`, `requests`, `distro`, `ntplib`, `pyyaml`, `paramiko`
  - 将其打包为`python3.tar.gz`



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

