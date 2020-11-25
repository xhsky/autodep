#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-11-20 16:33:57
# sky

logs_dir="./logs"
log_file=f"{logs_dir}/autodep.log"
log_console_level="info"
log_file_level="debug"
log_remote_level="debug"

remote_python_transfer_dir="/tmp"
remote_python_install_dir="/opt"
remote_python_dir=f"{remote_python_install_dir}/python3"
remote_python_exec=f"{remote_python_dir}/bin/python3"

remote_code_dir=f"{remote_python_dir}/code"
remote_pkgs_dir=f"{remote_python_dir}/pkgs"

interface={
        "mail": ["smtp.dreamdt.cn", 25],        # 邮件接口
        "sms": ["smartone.10690007.com", 80],   # 短信接口
        "platform": ["", 80]                    # 公司平台接口
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

tomcat_src="tomcat"
tomcat_dst="tomcat"
tomcat_pkg_dir=""
tomcat_server="8.5.51"

glusterfs_src="glusterfs"
glusterfs_dst="glusterfs"
glusterfs_pkg_dir=""
glusterfs_version="7.5"

jdk_src="jdk"
jdk_dst="jdk"
jdk_pkg_dir=""
jdk_version="8u251"

mysql_src="mysql"
mysql_dst="mysql"
mysql_pkg_dir=""
mysql_version="8.0.19"

nginx_src="nginx"
nginx_dst="nginx"
nginx_pkg_dir=None
nginx_version="1.17.9"

rabbitmq_src="rabbitmq"
rabbitmq_dst="rabbitmq"
rabbitmq_pkg_dir=None
rabbitmq_version="3.8.7"

redis_src="redis"
redis_dst="redis"
redis_pkg_dir=None
redis_version="5.0.7"
