#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import tarfile
import psutil

def config(located, cpu_count, tomcat_servers):
    nginx_conf=f'''\
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
'''

    nginx_conf_file=f"{located}/nginx/conf/nginx.conf"
    with open(nginx_conf_file, "w") as nginx_f:
        nginx_f.write(nginx_conf)

    os.system("id -u nginx &> /dev/null || useradd -r nginx")
    command=f"cd {located}/nginx ;./sbin/nginx -t &> /dev/null"
    return os.system(command)

def install(soft_file, located):
    os.makedirs(located, exist_ok=1)

    try:
        t=tarfile.open(soft_file)
        t.extractall(path=located)
        return 1, "ok"
    except Exception as e:
        return 0, e
def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")

    # 安装
    if action=="install":
        value, msg=install(soft_file, located)
        if value==1:
            print("nginx安装完成")
        else:
            print(f"Error: 解压安装包失败: {msg}")
            return 

        # 配置
        cpu_count=int(psutil.cpu_count() * float(weight))
        if cpu_count==0:
            cpu_count=1
        tomcat_servers=""
        for i in conf_dict.get("nginx_info").get("proxy_hosts"):
            tomcat_servers=f"{tomcat_servers}server {i}:8080;\n\t"
        #webapp=conf_dict.get("nginx_info").get("proxy_webapp")
        value=config(located, cpu_count, tomcat_servers)
        if value==0:
            print("nginx配置优化完成")
        else:
            print(f"nginx配置优化失败:{value}")
    elif action=="start":
        start_command=f"cd {located}/nginx ;./sbin/nginx &> /dev/null"
        result=os.system(start_command)
        if result==0:
            print(f"nginx启动完成")
        else:
            print(f"Error: nginx启动失败")


if __name__ == "__main__":
    main()
