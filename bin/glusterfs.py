#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json, time
from libs import common
from libs.env import log_remote_level, glusterfs_src, glusterfs_dst, \
        glusterfs_all_pkg_dir, glusterfs_client_pkg_dir, glusterfs_volume_name, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def install():
    pkg_file=conf_dict["pkg_file"]
    value, msg=common.install(pkg_file, glusterfs_src, glusterfs_dst, pkg_dir, located)
    if not value:
        log.logger.error(msg)
        return error_code

    if server_flag == 1:
        glusterd_conf_context=f"""\
                volume management
                    type mgmt/glusterd
                    option working-directory /var/lib/glusterd
                    option transport-type socket,rdma
                    option transport.socket.keepalive-time 10
                    option transport.socket.keepalive-interval 2
                    option transport.socket.read-fail-log off
                    option transport.socket.listen-port {glusterd_port}
                    option transport.rdma.listen-port 24008
                    option ping-timeout 0
                    option event-threads 1
                #   option lock-timer 180
                #   option transport.address-family inet6
                    option base-port {volume_port}
                    option max-port  60999
                end-volume
                """
        glusterd_conf_file="/etc/glusterfs/glusterd.vol"
        config_dict={
                "glusterd_conf":{
                    "config_file": glusterd_conf_file, 
                    "config_context": glusterd_conf_context, 
                    "mode": "w"
                    }
                }
    elif server_flag == 2:
        try:
            log.logger.debug(f"创建挂载目录: {mounted_dir}")
            os.makedirs(mounted_dir, exist_ok=1)

            mounted_str=f"{mounted_host}:{glusterfs_volume_name} {mounted_dir} glusterfs defaults 0 0\n"
            fstab_file="/etc/fstab"
            with open(fstab_file, "r") as f:
                 text=f.readlines()
            if mounted_str not in text:
                config_dict={
                        "gluster_client_conf": {
                            "config_file": fstab_file, 
                            "config_context": mounted_str, 
                            "mode": "a"
                            }
                        }
            else:
                config_dict={}
        except Exception as e:
            log.logger.error(str(e))
            return error_code

    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg=common.config(config_dict)
    if result:
        if server_flag==1:          # server需要提前启动
            return glusterd_start()
    else:
        log.logger.error(msg)
        return error_code

def run():
    if server_flag == 1:    # server
        volume_dir=f"{located}/brick"
        members=glusterfs_info_dict.get("members")
        try:
            log.logger.debug(f"建立volume目录: {volume_dir}")
            os.makedirs(volume_dir, exist_ok=1)

            # 配置集群
            create_volume_command=""
            for node in members:
                create_volume_command=f"{create_volume_command} {node}:{volume_dir}"
                add_peer_command=f"gluster peer probe {node}"
                log.logger.debug(f"添加节点: {add_peer_command=}")
                result, msg=common.exec_command(add_peer_command)
                if not result:
                    log.logger.error(msg)
                    return error_code
                else:
                    time.sleep(1)           # 迅速添加后会导致创建volume失败...

            # 判读volume是否存在 以决定其它gluster是否去创建volume
            volume_exist_command=f"gluster volume info {glusterfs_volume_name} > /dev/null 2>&1"
            log.logger.debug(f"查看volume是否存在: {volume_exist_command=}")
            result, msg=common.exec_command(volume_exist_command)
            if result:
                log.logger.debug(f"volume({glusterfs_volume_name})已存在")
            else:
                N=len(members)
                create_volume_command=f"gluster volume create {glusterfs_volume_name} replica {N} {create_volume_command} force"
                log.logger.debug(f"创建volume: {create_volume_command=}")
                result, msg=common.exec_command(create_volume_command)
                if result:
                    return volume_start()
                else:
                    log.logger.error(msg)
                    return error_code
        except Exception as e:
            log.logger.error(str(e))
            return error_code
    elif server_flag == 2:  # client
        return start()
    return normal_code

def glusterd_start():
    """glusterd启动
    """
    command="systemctl enable glusterd && systemctl start glusterd"
    log.logger.debug(f"启动: {command=}")
    result, msg=common.exec_command(command)
    if result:
        log.logger.debug(f"检测端口: {glusterd_port}") 
        if not common.port_exist([glusterd_port]):
            return error_code
    else:
        return error_code
    return normal_code

def volume_start():
    """volume启动
    """
    log.logger.debug(f"检测端口: {volume_port}")
    if not common.port_exist([volume_port], seconds=2):
        start_volume_command=f"gluster volume start {glusterfs_volume_name}"
        log.logger.debug(f"启动volume: {start_volume_command=}")
        result, msg=common.exec_command(start_volume_command)
        if result:
            log.logger.debug(f"检测端口: {volume_port}")
            if not common.port_exist([volume_port]):
                return error_code
        else:
            return error_code
    return normal_code

def start():
    """启动
    """
    if server_flag==1:      
        result_code=glusterd_start()
        if result_code==normal_code:
            return volume_start()
        else:
            return result_code
    elif server_flag==2:
        command="mount -a"
        log.logger.debug(f"执行挂载: {command}")
        result, msg=common.exec_command(command)
        if not result:
            log.logger.error(msg)
            return error_code
    return normal_code

def stop():
    """关闭
    """
    if server_flag==1:      
        command=f"echo y | gluster volume stop {glusterfs_volume_name} force"
        log.logger.debug(f"关闭volume: {command=}")
        result, msg=common.exec_command(command)
        if result:
            log.logger.debug(f"检测端口: {volume_port}") 
            if not common.port_exist([volume_port], exist_or_not=False):
                return error_code
            #else:
            #    command="systemctl stop glusterd"
            #    log.logger.debug(f"关闭glusterd: {command=}")
            #    result, msg=common.exec_command(command)
            #    if result:
            #        log.logger.debug(f"检测端口: {glusterd_port}") 
            #        if not common.port_exist([glusterd_port], exist_or_not=False):
            #            return error_code
            #    else:
            #        return error_code
        else:
            return error_code
    elif server_flag==2:
        command=f"umount {mounted_dir}"
        log.logger.debug(f"执行卸载: {command}")
        result, msg=common.exec_command(command)
        if not result:
            log.logger.error(msg)
            return error_code
    return normal_code

def monitor():
    """监控
    return:
        启动, 未启动, 启动但不正常
    """
    if server_flag==1:      
        #return common.soft_monitor("localhost", port_list)
        return common.soft_monitor("localhost", [volume_port])
    elif server_flag==2:
        if os.path.ismount(mounted_dir):
            return activated_code
        else:
            return stopped_code

if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    glusterfs_dir=f"{located}/{glusterfs_dst}"

    log=common.Logger({"remote": log_remote_level}, loggger_name="glusterfs")
    glusterfs_info_dict=conf_dict[f"{softname}_info"]
    if softname=="glusterfs-server":
        server_flag=1             # 软件标志: 1: server, 2: client, 3 all
        pkg_dir=glusterfs_all_pkg_dir
        glusterd_port=glusterfs_info_dict["port"].get("glusterd_port")
        volume_port=glusterfs_info_dict["port"].get("volume_port")
        port_list=[glusterd_port, volume_port]
    elif softname=="glusterfs-client":
        server_flag=2
        pkg_dir=glusterfs_client_pkg_dir
        mounted_host=glusterfs_info_dict.get("mounted_host")
        mounted_dir=glusterfs_info_dict.get("mounted_dir")

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

