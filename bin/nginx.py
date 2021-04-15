#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os
from libs import common
from libs.env import log_remote_level, nginx_src, nginx_dst, nginx_pkg_dir, nginx_version, \
        nginx_server_config, nginx_module_dict

def main():
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")

    nginx_dir=f"{located}/{nginx_dst}"
    nginx_info_dict=conf_dict["nginx_info"]
    vhosts_info_dict=nginx_info_dict["vhost_info"]
    port_list=[int(port) for port in vhosts_info_dict.keys()]

    log=common.Logger({"remote": log_remote_level}, loggger_name="nginx")

    # 安装
    flag=0
    if action=="install":
        pkg_file=conf_dict["pkg_file"]
        command="id -u nginx &> /dev/null || useradd -r nginx"
        log.logger.debug(f"创建用户: {command=}")
        result, msg=common.exec_command(command)
        if not result:
            log.logger.error(msg)
        value, msg=common.install(pkg_file, nginx_src, nginx_dst, nginx_pkg_dir, located)
        if not value:
            log.logger.error(msg)
            flag=1
            sys.exit(flag)

        # 配置
        worker_processes=nginx_info_dict.get("worker_processes")

        # vhost文件路径
        vhosts_file=f"{nginx_dir}/conf/vhosts.conf"
        try:
            #log.logger.debug(f"创建vhosts目录: {vhosts_dir}")
            #os.makedirs(vhosts_dir, exist_ok=1)

            server_config_list=[]
            for port in vhosts_info_dict:
                config_mod=[]
                upstream_servers_list=[]
                for config_name in vhosts_info_dict[port]:
                    proxy_name=vhosts_info_dict[port][config_name]["proxy_name"]
                    # 配置upstream
                    upstream_servers=f"\nupstream {proxy_name} {{"
                    for proxy_host in vhosts_info_dict[port][config_name].get("proxy_hosts"):
                        upstream_servers=f"{upstream_servers}\n\tserver {proxy_host};" 
                    else:
                        upstream_servers=f"{upstream_servers}\n}}" 
                        upstream_servers_list.append(upstream_servers)
                    # 配置root
                    code_dir=vhosts_info_dict[port][config_name].get("code_dir")
                    if code_dir is None:
                        code_dir=""
                    else:
                        code_dir=f"root {code_dir};"

                    config_mod.append(nginx_module_dict[config_name] % (code_dir, proxy_name))
                upstream_servers="\n".join(upstream_servers_list)
                server_config_list.append(f"{upstream_servers}\n{nginx_server_config}" % (port, "\n".join(config_mod)))
        except Exception as e:
            log.logger.error(f"配置vhosts失败: {str(e)}")
            flag=1
            sys.exit(flag)

        nginx_conf_text=f"""\
                user  nginx;
                worker_processes  {worker_processes};

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

                    server_tokens   off;
                    server_names_hash_bucket_size 128;
                    client_header_buffer_size 512k;
                    large_client_header_buffers 4 512k;

                    client_max_body_size 20m;
                    sendfile        on;
                    tcp_nopush     on;
                    tcp_nodelay on;
                    keepalive_timeout  65;

                    # gzip
                    gzip  on;
                    gzip_min_length 1k;
                    gzip_buffers 16 64k;
                    gzip_types text/plain application/x-javascript text/css application/xml;
                    gzip_vary on;


                    # 使客户端请求header中带有下划线的字段生效
                    underscores_in_headers on;
                    
                    # proxy
                    proxy_intercept_errors on;			# 启用error_page
                    proxy_set_header Host $http_host; 
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_buffer_size 512k;			# userLogin接口, 用户header信息的缓冲区大小
                    proxy_buffers 32 128k;
                    
                    #proxy_connect_timeout 3000;
                    #proxy_read_timeout 600000;
                    #proxy_send_timeout 600000;
                    #open_file_cache max=204800 inactive=30s;
                    #open_file_cache_min_uses 1;
                    #open_file_cache_valid 50s;
                    #send_timeout  60;
                    #proxy_request_buffering off;

                    include {vhosts_file};
                }}
                """
        nginx_conf_file=f"{nginx_dir}/conf/nginx.conf"
        config_dict={
                "nginx_conf":{
                    "config_file": nginx_conf_file, 
                    "config_context": nginx_conf_text, 
                    "mode": "w"
                    }, 
                "vhosts_conf": {
                    "config_file": vhosts_file, 
                    "config_context": "\n".join(server_config_list), 
                    "mode": "w"
                    }
                }
        log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
        result, msg=common.config(config_dict)
        if result:
            command=f"cd {nginx_dir} && ./sbin/nginx -t"
            log.logger.debug(f"检测配置文件: {command=}")
            result, msg=common.exec_command(command)
            if not result:
                log.logger.error(msg)
                flag=1  
        else:
            log.logger.error(msg)
            flag=1

        sys.exit(flag)

    elif action=="run" or action=="start":
        start_command=f"cd {nginx_dir} ; ./sbin/nginx"
        log.logger.debug(f"{start_command=}")
        result, msg=common.exec_command(start_command)
        if result:
            log.logger.debug(f"检测端口: {port_list=}")
            if not common.port_exist(port_list):
                flag=2
        else:
            log.logger.error(msg)
            flag=1
        sys.exit(flag)
    elif action=="stop":
        start_command=f"cd {nginx_dir} ; ./sbin/nginx -s stop"
        log.logger.debug(f"{start_command=}")
        result, msg=common.exec_command(start_command)
        if result:
            log.logger.debug(f"检测端口: {port_list=}")
            if not common.port_exist(port_list, exist_or_not=False):
                flag=2
        else:
            log.logger.error(msg)
            flag=1
        sys.exit(flag)

if __name__ == "__main__":
    main()
