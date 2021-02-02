#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-11-20 16:33:57
# sky

# 日志目录及各类日志级别
logs_dir="./logs"
log_file=f"{logs_dir}/autodep.log"
log_console_level="info"
log_graphics_level="info"
log_file_level="debug"
log_remote_level="debug"
log_platform_level="debug"
log_update_level="debug"

# 安装目录名称
located_dir_name="dream"

# 占位软件列表
placeholder_software_list=["program"]

#log_update_file=f"{logs_dir}/update.log"
code_saved_remote_dir="/tmp"
#update_version_file="code_version"

# 部署各阶段状态文件
host_info_file=f"{logs_dir}/host_info.json"
init_stats_file=f"{logs_dir}/init.json"
install_stats_file=f"{logs_dir}/install.json"
start_stats_file=f"{logs_dir}/start.json"
update_stats_file=f"{logs_dir}/update.json"

update_config_file_name="update.json"

# 文本图形化安装时的最小窗口尺寸
g_term_rows=24
g_term_cols=80

test_mode=True
fixed_dir="/opt"

remote_python_transfer_dir="/tmp"
remote_python_install_dir=fixed_dir
remote_python_dir=f"{remote_python_install_dir}/python3"
remote_python_exec=f"{remote_python_dir}/bin/python3"

remote_code_dir=f"{remote_python_dir}/code"
remote_pkgs_dir=f"{remote_python_dir}/pkgs"

update_package_dir=remote_pkgs_dir

interface={
        "mail": ["smtp.dreamdt.cn", 25, None],                              # 邮件接口
        "sms": ["smartone.10690007.com", 80, "/proxysms/mt"],               # 短信接口
        "platform_log": ["192.168.0.81", 8115, "/project/deploy/sendLog"],  # 公司平台日志接口
        "platform_info": ["192.168.0.81", 8115, "/project/deploy/sendDetection"],  # 公司平台信息接口
        }

# 各软件安装最小配置
min_install_config={
        "nginx":{
            "mem": 1024,        # 内存单位均为M
            "cpus": 1
            }, 
        "jdk": {
            "mem": 0, 
            "cpus": 0
            }, 
        "tomcat":{
            "mem": 1024, 
            "cpus": 1
            }, 
        "ffmpeg":{
            "mem": 512, 
            "cpus": 1
            }, 
        "elasticsearch":{
            "mem": 1024, 
            "cpus": 1
            }, 
        "glusterfs":{
            "mem": 1024, 
            "cpus":1
            }, 
        "mysql":{
            "mem":2048, 
            "cpus": 2
            }, 
        "rabbitmq":{
            "mem": 1024, 
            "cpus": 1
            }, 
        "redis": {
            "mem": 1024, 
            "cpus":1
            }, 
        "rocketmq":{
            "mem": 1024, 
            "cpus":1
            }
        }
# 各软件权重比
soft_weights_dict={
        "elasticsearch": 1, 
        "glusterfs": 1, 
        "nginx": 1, 
        "redis": 2, 
        "ffmpeg": 1, 
        "mysql": 3, 
        "erlang": 0, 
        "rabbitmq": 1, 
        "rocketmq": 1, 
        "jdk": 0, 
        "tomcat": 2, 
        "program": 2
        }
# 部署环境下的权重基数
soft_weights_unit_dict={
        "演示环境": 0.5, 
        "测试环境": 1, 
        "正式环境": 2
        }
host_weights_unit_dict={
        "cpu": 1,               # 1 cpu core = 1
        "mem": 512              # 512M = 1
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


## nginx配置/代码模块转发配置
nginx_server_config="""
server {
        listen       %s;
        server_name  localhost;

        #charset koi8-r;

        #access_log  logs/host.access.log  main;

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }

        location = /favicon.ico {
            return 200;     		# 忽略浏览器的title前面的图标
        }
        
        %s
}
"""

nginx_module_dict={
        "智慧党校(含网络培训)-大教务4.0": """
            location /dsfa {
                %s                                # 前端代码目录, 配置到dsfa上级目录 
                if (!-e $request_filename) {
                    proxy_pass http://%s;
                    }
                #try_files $uri $uri/ /index.html;
            }
        """, 
        "智慧党校(含网络培训)-大教务5.0": """
            location /dsf5/ {
	        %s                               # 配置到dsf5的上级目录, (pages, 改为dsf5)
                if (!-e $request_filename) {
                    rewrite ^/dsf5/(.*)$ /$1 break;   # 后端代码无前缀
                    proxy_pass http://%s;
                  }
	      
	        error_page 404 = @rewrite_dsfa;
                }
	    
	    location @rewrite_dsfa {
                rewrite ^(.*)$ /dsfa$1 last;
	    }
        """
        }
