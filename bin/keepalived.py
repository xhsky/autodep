#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json, os, psutil, socket, textwrap
from libs import common
from libs.env import log_remote_level, keepalived_src, keepalived_dst, keepalived_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def get_adapter_name(ip):
    """根据ip获取其网卡名称
    """
    nic=psutil.net_if_addrs()
    for adapter in nic:
        for snic in nic[adapter]:
            if snic.address==ip:
                return adapter
    else:
        return ""

def install():
    """安装
    """
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, keepalived_src, keepalived_dst, keepalived_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    os.makedirs("/etc/keepalived", exist_ok=1)
    command=f"mkdir -p /etc/keepalived && \cp {keepalived_dir}/share/keepalived.service /lib/systemd/system/ && systemctl daemon-reload"
    log.logger.debug(f"{command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)
        return error_code

    check_process=keepalived_info_dict["check_process"]
    check_file="/etc/keepalived/check.sh"
    check_context=f"""\
            #!/bin/bash

            count=`ps -C {check_process} --no-header | wc -l`
            if [ $count -eq 0 ];then
                exit 1
            fi
    """

    state=keepalived_info_dict["state"].upper()
    weight=-30
    if state=="MASTER":
        priority=100
    else:
        priority=80

    interface=get_adapter_name(ip)
    if interface == "":
        log.logger.error(f"无法根据IP({ip})获取其网卡名称")
        return error_code

    virtual_addr=keepalived_info_dict["virtual_addr"]
    memebers=keepalived_info_dict["members"]
    try:
        for node in memebers:
            src_ip=socket.gethostbyname(node)
            if src_ip==ip:
                local_node=node
                break
        else:
            log.logger.error(f"当前主机{ip}不在{memebers}中")
            return error_code

        memebers.remove(local_node)
        unicast_src_ip=ip
        unicast_peer=""
        for i in memebers:
            unicast_peer=f"{unicast_peer}\n{socket.gethostbyname(i)}"
        else:
            unicast_peer=textwrap.indent(unicast_peer, '                     ')
    except Exception as e:
        log.logger.error(str(e))
        return error_code

    keepalived_conf_text=f"""\
            ! Configuration File for keepalived

            global_defs {{
                router_id {local_node}
                max_auto_priority 2
            }}

            vrrp_script check_sh {{
                script "bash {check_file}"
                interval 2
                weight {weight}
                user root
            }}

            vrrp_instance HA {{
                state {state}
                interface {interface}
                virtual_router_id 55
                priority {priority}
                advert_int 1
                unicast_src_ip {unicast_src_ip}
                unicast_peer {{ {unicast_peer}
                }}
                authentication {{
                    auth_type PASS
                    auth_pass 1234
                }}
                track_script {{
                    check_sh
                }}
                virtual_ipaddress {{
                    {virtual_addr}
                }}
            }}
            """
    keepalived_conf_file=f"/etc/keepalived/keepalived.conf"
    config_dict={
            "keepalived_conf":{
                "config_file": keepalived_conf_file, 
                "config_context": keepalived_conf_text, 
                "mode": "w"
                }, 
            "check_conf":{
                "config_file": check_file, 
                "config_context": check_context, 
                "mode": "w"
                }
            }

    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)=}")
    result, msg=common.config(config_dict)
    if result:
        return_value=normal_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    start_command=f"systemctl start keepalived"
    log.logger.debug(f"{start_command=}")
    result, msg=common.exec_command(start_command)
    if result:
        return_code=monitor()
        if return_code!=activated_code:
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
    stop_command=f"systemctl stop keepalived"
    log.logger.debug(f"{stop_command=}")
    result, msg=common.exec_command(stop_command)
    if result:
        return_code=monitor()
        if return_code!=stopped_code:
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
    if os.path.exists(pid_file):
        with open(pid_file, "r") as f:
            pid=int(f.read())
        if common.pid_exists(pid):
            return activated_code
        else:
            return stopped_code
    else:
        return stopped_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    log=common.Logger({"remote": log_remote_level}, loggger_name="keepalived")

    located=conf_dict["located"]
    ip=conf_dict["ip"]
    keepalived_dir=f"{located}/{keepalived_src}"
    keepalived_info_dict=conf_dict["keepalived_info"]
    pid_file="/run/keepalived.pid"

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

