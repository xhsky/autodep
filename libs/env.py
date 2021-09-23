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

# 操作系统支持
support_os=["centos 7", "uos 20"]
# 国产化软件及端口
localization_soft_port={
        "autocheck": 0, 
        "dameng": 5236, 
        "shentong": 2003, 
        "kingbase": 54321
        }

# 配置文件
#program_file="./config/program.json"
init_file="./config/init.json"
arch_file="./config/arch.json"
update_arch_file="./config/update_arch.json"
update_init_file="./config/update_init.json"
project_file="./config/project.json"
start_file="./config/start.json"
stop_file="./config/stop.json"
check_file="./config/check.json"
localization_file="./config/localization.json"
ext_file="./config/ext.json"
# 数据文件
data_dir="./data"
host_info_file=f"{data_dir}/host_info.json"
deploy_file=f"{data_dir}/deploy.json"
backup_version_file=f"{data_dir}/backup_version.json"
rollback_version_file=f"{data_dir}/rollback_version.json"

# ext路径
ext_dir="../ext"

# 安装目录名称
located_dir_name="dream"
located_dir_link="/dream"

# 备份/回滚目录
backup_dir=f"{located_dir_link}/backup"
rollback_dir=f"{located_dir_link}/rollback"
# 备份文件名称格式
backup_abs_file_format="{backup_dir}/{backup_version}_{softname}.tar.gz"
rollback_abs_file_format="{rollback_dir}/{backup_version}/{backup_version}_{softname}.tar.gz"
# 备份的软件类型
backup_soft_type=["frontend", "program", "sql"]

# 巡检汇总目录
report_dir="./report" 
report_file_list=["check.info", "slow_analysis.log"]

# 目录
autodep_dir=[logs_dir, data_dir, report_dir]

# 更新
#code_saved_remote_dir="/tmp"

# 部署各阶段状态文件
init_stats_file=f"{logs_dir}/init_stats.json"
install_stats_file=f"{logs_dir}/install_stats.json"
start_stats_file=f"{logs_dir}/start_stats.json"
run_stats_file=f"{logs_dir}/run_stats.json"
update_stats_file=f"{logs_dir}/update_stats.json"
#update_config_file_name="update.json"

# 程序运行返回值
normal_code=0           # 正常
error_code=127          # 错误
activated_code=10       # 已运行
stopped_code=20         # 已停止
abnormal_code=30        # 异常

# 文本图形化安装时的最小窗口尺寸
g_term_rows=20
g_term_cols=80

# 测试模式, 正式环境关闭
test_mode=False
# 检测时是否开启资源校验
resource_verify_mode=False

portless_service_code=0     # 无端口有服务软件代码, 用于获取软件端口时的识别
tool_service_code=1         # 工具类软件代码

# 目录配置
#fixed_dir="/opt"
remote_python_transfer_dir="/tmp"
remote_python_install_dir="/opt"
remote_python_dir=f"{remote_python_install_dir}/python3"
remote_python_exec=f"{remote_python_dir}/bin/python3"

remote_code_dir=f"{remote_python_dir}/code"
remote_pkgs_dir=f"{remote_python_dir}/pkgs"

update_package_dir=remote_pkgs_dir

#program_unzip_dir="./program_pkg"
# program控制脚本名称
program_sh_name="program.sh"
# 测试数据库连通的SQL文件. %s为数据库软件名称
test_sql_file="/tmp/%s_test.sql"

interface={
        "mail": ["smtp.dreamdt.cn", 25, None],                              # 邮件接口
        "sms": ["smartone.10690007.com", 80, "/proxysms/mt"],               # 短信接口
        "platform_log": ["125.69.82.54", 14206, "/project/deploy/sendLog"],  # 公司平台日志接口
        "platform_info": ["125.69.82.54", 14206, "/project/deploy/sendDetection"],  # 公司平台信息接口
        "platform_check": ["125.69.82.54", 14206, "/project/deploy/uploadXjText"],  # 公司平台巡检文件接口
        }

# link
ffmpeg_src="ffmpeg-"
ffmpeg_dst="ffmpeg"
ffmpeg_pkg_dir=None

elasticsearch_src="elasticsearch-"
elasticsearch_dst="elasticsearch"
elasticsearch_pkg_dir=None

tomcat_src="apache-tomcat-"
tomcat_dst="tomcat"
tomcat_pkg_dir=None

glusterfs_src="glusterfs-"
glusterfs_dst="glusterfs"
glusterfs_all_pkg_dir="glusterfs_all"
glusterfs_client_pkg_dir="glusterfs_client"
glusterfs_volume_name="g_data"

jdk_src="jdk"
jdk_dst="jdk"
jdk_pkg_dir=None

erl_src="erlang-"
erl_dst="erlang"
erl_pkg_dir=None

mysql_src="mysql-"
mysql_dst="mysql"
mysql_pkg_dir="pkg"
mysql_user="mysql"

nginx_src="nginx-"
nginx_dst="nginx"
nginx_pkg_dir=None

dps_src="dps-"
dps_dst="dps"
dps_pkg_dir=None

rabbitmq_src="rabbitmq_server-"
rabbitmq_dst="rabbitmq"
rabbitmq_pkg_dir=None

rocketmq_src="rocketmq-all-"
rocketmq_dst="rocketmq"
rocketmq_pkg_dir=None

redis_src="redis-"
redis_dst="redis"
redis_pkg_dir=None

dch_src="dch-"
dch_dst="dch"
dch_pkg_dir=None

autocheck_src="autocheck-"
autocheck_dst="autocheck"
autocheck_pkg_dir=None

nacos_src="nacos"
nacos_dst=None
nacos_pkg_dir=None

backup_tool_src="backup_tool"
backup_tool_dst=None
backup_tool_pkg_dir=None


'''
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
        """, 
        "智慧党校(含网络培训)-科研": """
            location / {
                %s
                if (!-e $request_filename) {
                    proxy_pass http://%s;
                  }
            }
        """
  '     }
'''
