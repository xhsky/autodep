#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-11-20 16:33:57
# sky

logs_dir="./logs"
log_file=f"{logs_dir}/autodep.log"
log_console_level="info"
log_file_level="debug"
log_remote_level="debug"
log_platform_level="debug"

test_mode=True
fixed_dir="/opt"

remote_python_transfer_dir="/tmp"
remote_python_install_dir="/opt"
remote_python_dir=f"{remote_python_install_dir}/python3"
remote_python_exec=f"{remote_python_dir}/bin/python3"

remote_code_dir=f"{remote_python_dir}/code"
remote_pkgs_dir=f"{remote_python_dir}/pkgs"

interface={
        "mail": ["smtp.dreamdt.cn", 25, None],                              # 邮件接口
        "sms": ["smartone.10690007.com", 80, "/proxysms/mt"],               # 短信接口
        "platform_log": ["192.168.0.81", 8115, "/project/deploy/sendLog"],  # 公司平台日志接口
        "platform_info": ["192.168.0.81", 8115, "/project/deploy/sendDetection"],  # 公司平台信息接口
        }

# link
ffmpeg_src="ffmpeg"
ffmpeg_dst="ffmpeg"
ffmpeg_pkg_dir="deps"
ffmpeg_version="4.2.2"

elasticsearch_src="elasticsearch"
elasticsearch_dst="elasticsearch"
elasticsearch_pkg_dir=None
elasticsearch_version="7.8.1"

tomcat_src="apache-tomcat-"
tomcat_dst="tomcat"
tomcat_pkg_dir=None
tomcat_version="8.5.51"

glusterfs_src="glusterfs-"
glusterfs_dst="glusterfs"
glusterfs_all_pkg_dir="glusterfs_all"
glusterfs_client_pkg_dir="glusterfs_client"
glusterfs_volume_name="g_data"
glusterfs_version="7.5"

jdk_src="jdk"
jdk_dst="jdk"
jdk_pkg_dir=None
jdk_version="8u251"

erl_src="erlang"
erl_dst="erlang"
erl_pkg_dir=None
erl_version="23.2"

mysql_src="mysql-"
mysql_dst="mysql"
mysql_pkg_dir="pkg"
mysql_version="8.0.19"
mysql_user="mysql"

nginx_src="nginx-"
nginx_dst="nginx"
nginx_pkg_dir=None
nginx_version="1.17.9"

rabbitmq_src="rabbitmq_server-"
rabbitmq_dst="rabbitmq"
rabbitmq_pkg_dir=None
rabbitmq_version="3.8.9"

rocketmq_src="rocketmq-all-"
rocketmq_dst="rocketmq"
rocketmq_pkg_dir=None
rocketmq_version="4.8.0"

redis_src="redis-"
redis_dst="redis"
redis_pkg_dir=None
redis_version="5.0.7"
