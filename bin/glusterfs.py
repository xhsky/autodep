#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
from libs import common
from libs.env import log_remote_level, glusterfs_src, glusterfs_dst, \
        glusterfs_all_pkg_dir, glusterfs_client_pkg_dir, \
        glusterfs_volume_name, glusterfs_version

def install():
    pkg_file=conf_dict["pkg_file"]
    log.logger.debug(f"{server_flag=}")
    value, msg=common.install(pkg_file, glusterfs_src, glusterfs_dst, pkg_dir, located)
    if not value:
        log.logger.error(msg)
        sys.exit(1)

    if server_flag != 1:
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
        log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
        result, msg=common.config(config_dict)
        if not result:
            log.logger.error(msg)
            sys.exit(1)

        command="systemctl enable glusterd && systemctl start glusterd"
        log.logger.debug(f"启动: {command=}")
        status, result=common.exec_command(command)
        if status:
            if result.returncode != 0:
                log.logger.error(result.stderr)
                flag=1
            else:
                log.logger.debug(f"检测端口: {glusterd_port}") 
                if not common.port_exist([glusterd_port]):
                    flag=2
        else:
            log.logger.error(result)
            flag=1
    return flag

def run():
    if server_flag == 3 or server_flag == 2:
        volume_dir=server_info_dict.get("volume_dir")
        members=server_info_dict.get("members")
        try:
            log.logger.debug(f"建立volume目录: {volume_dir}")
            os.makedirs(volume_dir, exist_ok=1)
        except Exception as e:
            log.logger.error(str(e))
            exit(1)

        # 配置集群
        create_volume_command=""
        for node in members:
            create_volume_command=f"{create_volume_command} {node}:{volume_dir}"
            add_peer_command=f"gluster peer probe {node}"
            log.logger.debug(f"添加节点: {add_peer_command=}")
            status, result=common.exec_command(add_peer_command)
            if status:
                if result.returncode != 0:
                    log.logger.error(result.stderr)
                    sys.exit(1)
            else:
                log.logger.error(result)
                sys.exit(1)

        volume_exist_command=f"gluster volume info {glusterfs_volume_name} &> /dev/null"
        log.logger.debug(f"查看volume是否存在: {volume_exist_command=}")
        status, result=common.exec_command(volume_exist_command)
        if status:
            if result.returncode==0:
                log.logger.debug(f"volume {glusterfs_volume_name}已存在")
            else:
                N=len(members)
                create_volume_command=f"gluster volume create {glusterfs_volume_name} replica {N} {create_volume_command} force"
                log.logger.debug(f"创建volume: {create_volume_command=}")
                status, result=common.exec_command(create_volume_command)
                if status:
                    if result.returncode != 0:
                        log.logger.error(result.stderr)
                        sys.exit(1)
                    else:
                        start_volume_command=f"gluster volume start {glusterfs_volume_name}"
                        log.logger.debug(f"启动volume: {start_volume_command=}")
                        status, result=common.exec_command(start_volume_command)
                        if status:
                            if result.returncode != 0:
                                log.logger.error(result.stderr)
                                sys.exit(1)
                            else:
                                log.logger.debug(f"检测端口: {volume_port}")
                                if not common.port_exist([volume_port]):
                                    sys.exit(2)
                        else:
                            log.logger.error(result)
                            sys.exit(1)
                else:
                    log.logger.error(result)
                    sys.exit(1)
        else:
            log.logger.error(result)
            sys.exit(1)
    if server_flag == 3 or server_flag == 1:
        mounted_host=client_info_dict.get("mounted_host")
        mounted_dir=client_info_dict.get("mounted_dir")

        try:
            log.logger.debug(f"创建挂载目录: {mounted_dir}")
            os.makedirs(mounted_dir, exist_ok=1)

            mounted_str=f"{mounted_host}:{glusterfs_volume_name} {mounted_dir} glusterfs defaults 0 0\n"
            fstab_file="/etc/fstab"
            with open(fstab_file, "r+") as f:
                 text=f.readlines()
                 if mounted_str not in text:
                    log.logger.debug(f"写入{fstab_file}文件: {mounted_str=}")
                    f.write(mounted_str)
        except Exception as e:
            log.logger.error(str(e))
            sys.exit(1)

        command="mount -a"
        log.logger.debug(f"执行挂载: {command}")
        status, result=common.exec_command(command)
        if status:
            if result.returncode != 0:
                log.logger.error(result.stderr)
                sys.exit(1)
        else:
            log.logger.error(result)
            sys.exit(1)
    return flag

def start():
    pass

def stop():
    pass

def monitor():
    pass


if __name__ == "__main__":
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    glusterfs_dir=f"{located}/{glusterfs_dst}"

    log=common.Logger({"remote": log_remote_level}, loggger_name="glusterfs")
    glusterfs_info_dict=conf_dict.get("glusterfs_info")
    server_flag=0             # 软件标志: 1: client, 2 server, 3 all
    server_info_dict=glusterfs_info_dict.get("server_info")
    client_info_dict=glusterfs_info_dict.get("client_info")
    if client_info_dict is not None:
        server_flag=1
        pkg_dir=glusterfs_client_pkg_dir
    if server_info_dict is not None:
        if server_flag == 0:
            server_flag=2
        else:
            server_flag=3
        pkg_dir=glusterfs_all_pkg_dir
        glusterd_port=server_info_dict["port"].get("glusterd_port")
        volume_port=server_info_dict["port"].get("volume_port")

    flag=0
    action_dict={
            "install": install, 
            "run": run, 
            "start": start, 
            "stop": stop, 
            "monitor": monitor
            }
    if action in action_dict:
        flag=action_dict[action]()
        sys.exit(flag)
