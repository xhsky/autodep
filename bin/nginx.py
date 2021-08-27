#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, textwrap
from libs import common
from libs.env import log_remote_level, nginx_src, nginx_dst, nginx_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=0
    pkg_file=conf_dict["pkg_file"]
    command="id -u nginx &> /dev/null || useradd -r nginx"
    log.logger.debug(f"创建用户: {command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)
    value, msg=common.install(pkg_file, nginx_src, nginx_dst, nginx_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    # vhost文件路径
    vhosts_file=f"{nginx_dir}/conf/vhosts.conf"
    try:
        server_config_list=[]
        for port in vhosts_info_dict:
            nginx_server_config=f"""\
                    server {{
                        listen       {int(port)};
                        server_name  localhost;

                        #charset koi8-r;

                        access_log  logs/{port}.access.log  main;

                        error_page   500 502 503 504  /50x.html;
                        location = /50x.html {{
                            root   html;
                        }}

                        location = /favicon.ico {{
                            return 200;     		# 忽略浏览器的title前面的图标
                        }}
            """
            nginx_server_config=textwrap.dedent(nginx_server_config)
            for name in vhosts_info_dict[port]:
                mode=vhosts_info_dict[port][name]["mode"]
                if mode=="proxy":
                    # 配置upstream
                    proxy_name=vhosts_info_dict[port][name]["proxy_name"]
                    upstream_servers=f"upstream {proxy_name} {{"
                    for proxy_host in vhosts_info_dict[port][name]["proxy_hosts"]:
                        upstream_servers=f"{upstream_servers}\n\tserver {proxy_host};" 
                    else:
                        upstream_servers=f"{upstream_servers}\n}}" 
                    nginx_server_config=f"{upstream_servers}\n{nginx_server_config}"

                    name_config=textwrap.indent(textwrap.dedent(f"""\
                            location {name} {{
                                proxy_pass http://{proxy_name};
                            }}
                    """), "    ")
                elif mode=="location":
                    name_config=textwrap.indent(textwrap.dedent(f"""\
                            location {name} {{
                                root {vhosts_info_dict[port][name]['frontend_dir']};
                            }}
                    """), "    ")
                nginx_server_config=f"{nginx_server_config}\n{name_config}"
            else:
                nginx_server_config=f"{nginx_server_config}\n}}"
                server_config_list.append(nginx_server_config)
    except Exception as e:
        log.logger.error(f"配置vhosts失败: {str(e)}")
        return error_code

    # 配置
    worker_processes=nginx_info_dict.get("worker_processes")
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

                log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                                  '$status $body_bytes_sent "$http_referer" '
                                  '"$http_user_agent" "$http_x_forwarded_for"';

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
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    start_command=f"cd {nginx_dir} ; ./sbin/nginx"
    log.logger.debug(f"{start_command=}")
    result, msg=common.exec_command(start_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def start():
    """启动
    """
    return run()

def stop():
    """关闭
    """
    return_value=normal_code
    stop_command=f"cd {nginx_dir} ; ./sbin/nginx -s stop"
    log.logger.debug(f"{stop_command=}")
    result, msg=common.exec_command(stop_command)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, exist_or_not=False):
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def monitor():
    """监控
    return:
        启动, 未启动, 启动但不正常
    """
    return common.soft_monitor("localhost", port_list)

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level}, loggger_name="nginx")

    located=conf_dict["located"]
    nginx_dir=f"{located}/{nginx_dst}"
    nginx_info_dict=conf_dict["nginx_info"]
    vhosts_info_dict=nginx_info_dict["vhosts_info"]
    port_list=[int(port) for port in vhosts_info_dict]

    if action=="install":
        sys.exit(install())
    elif action=="run":
        sys.exit(run())
    elif action=="start":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(activated_code)
        elif status_value==stopped_code:
            sys.exit(start())
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(start())
            else:
                sys.exit(error_code)
    elif action=="stop":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(stop())
        elif status_value==stopped_code:
            sys.exit(stopped_code)
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(normal_code)
            else:
                sys.exit(error_code)
    elif action=="monitor":
        sys.exit(monitor())
    else:
        sys.exit(error_code)

