#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, textwrap
from libs import common, tools
from libs.env import log_remote_level, dps_src, dps_dst, dps_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    """安装
    """
    return_value=0
    pkg_file=conf_dict["pkg_file"]
    command="id -u dps > /dev/null 2>&1 || useradd -r dps"
    log.logger.debug(f"创建用户: {command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)
    value, msg=common.install(pkg_file, dps_src, dps_dst, dps_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    # vhost文件路径
    vhosts_file=f"{dps_dir}/conf/vhosts.conf"
    try:
        server_config_list=[]
        for port in vhosts_info_dict:
            dps_server_config=f"""\
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
            dps_server_config=textwrap.dedent(dps_server_config)
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
                    dps_server_config=f"{upstream_servers}\n{dps_server_config}"

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
                dps_server_config=f"{dps_server_config}\n{name_config}"
            else:
                dps_server_config=f"{dps_server_config}\n}}"
                server_config_list.append(dps_server_config)
    except Exception as e:
        log.logger.error(f"配置vhosts失败: {str(e)}")
        return error_code

    # 配置
    worker_processes=dps_info_dict.get("worker_processes")
    dps_conf_text=tools.render("config/templates/dps/dps.conf.tem", worker_processes=worker_processes, vhosts_file=vhosts_file)
    dps_conf_file=f"{dps_dir}/conf/dps.conf"
    config_dict={
            "dps_conf":{
                "config_file": dps_conf_file, 
                "config_context": dps_conf_text, 
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
        command=f"cd {dps_dir} && ./sbin/dps-server -t"
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
    start_command=f"cd {dps_dir} ; ./sbin/dps-server"
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
    stop_command=f"cd {dps_dir} ; ./sbin/dps-server -s stop"
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
    log=common.Logger({"remote": log_remote_level}, loggger_name="dps")

    located=conf_dict["located"]
    if dps_dst is None:
        dps_dir=f"{located}/{dps_src}"
    else:
        dps_dir=f"{located}/{dps_dst}"
    dps_info_dict=conf_dict["dps_info"]
    vhosts_info_dict=dps_info_dict["vhosts_info"]
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

