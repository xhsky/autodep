#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import psutil
from libs import common

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    soft_name="Nginx"

    log=common.Logger(None, "info", "remote")

    # 安装
    if action=="install":
        os.system("id -u nginx &> /dev/null || useradd -r nginx")
        value, msg=common.install(soft_file, "nginx-", "nginx", None, located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.error(f"{soft_name}安装失败: {msg}")
            return 

        # 配置
        cpu_count=int(psutil.cpu_count() * float(weight))
        if cpu_count==0:
            cpu_count=1
        # proxy
        tomcat_servers=""
        for i in conf_dict.get("nginx_info").get("proxy_hosts"):
            tomcat_servers=f"{tomcat_servers}server {i}:8080;\n                "
        
        nginx_conf_text=f"""\
                user  nginx;
                worker_processes  {cpu_count};

                #error_log  logs/error.log;
                #error_log  logs/error.log  notice;
                error_log  logs/error.log  info;

                pid        logs/nginx.pid;
                worker_rlimit_nofile 65535;

                events {{
                    use epoll;
                    worker_connections  65535;
                }}

                http {{
                    include       mime.types;
                    default_type  application/octet-stream;
                    charset utf-8;

                    #log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                    #                  '$status $body_bytes_sent "$http_referer" '
                    #                  '"$http_user_agent" "$http_x_forwarded_for"';

                    #access_log  logs/access.log  main;
                    server_names_hash_bucket_size 128;
                    client_header_buffer_size 32k;
                    large_client_header_buffers 4 64k;

                    client_max_body_size 8m;
                    sendfile        on;
                    tcp_nopush     on;
                    tcp_nodelay on;
                    #keepalive_timeout  0;
                    keepalive_timeout  65;

                    # gzip
                    gzip  on;
                    gzip_min_length 1k;
                    gzip_buffers 4 16k;
                    gzip_types text/plain application/x-javascript text/css application/xml;
                    gzip_vary on;

                    # proxy header
                    underscores_in_headers on;

                    # load 
                    upstream tomcat_servers {{
                        ip_hash;
                        {tomcat_servers}
                    }}

                    server {{
                        listen       80;
                        server_name  localhost;

                        #charset koi8-r;

                        #access_log  logs/host.access.log  main;

                        location / {{
                          proxy_pass http://tomcat_servers;
                          proxy_set_header Host $host; 
                          proxy_set_header X-Real-IP $remote_addr;
                          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                        }}
                    }}
                }}
                """
        nginx_conf_file=f"{located}/nginx/conf/nginx.conf"
        config_dict={
                "nginx_conf":{
                    "config_file": nginx_conf_file, 
                    "config_context": nginx_conf_text, 
                    "mode": "w"
                    }
                }
        result, msg=common.config(config_dict)
        if result==1:
            command=f"cd {located}/nginx ;./sbin/nginx -t &> /dev/null"
            if os.system(command) == 0:
                log.logger.info(f"{soft_name}配置优化完成")
            else:
                log.logger.error(f"{soft_name}配置优化失败")
        else:
            log.logger.error(f"{soft_name}配置文件写入失败:{msg}")

    elif action=="start":
        start_command=f"cd {located}/nginx ; ./sbin/nginx &> /dev/null"
        result=os.system(start_command)
        if result==0:
            status=common.port_exist(80, 300)
            if status==1:
                log.logger.info(f"{soft_name}启动完成")
            else:
                log.logger.error(f"{soft_name}启动超时")
        else:
            log.logger.error(f"Error: {soft_name}启动失败")

if __name__ == "__main__":
    main()
