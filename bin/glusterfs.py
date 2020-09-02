#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
from libs import common

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    soft_name="GlusterFS"

    log=common.Logger(None, "info", "remote")

    # 安装
    if action=="install":
        located=conf_dict.get("located")
        link_src="glusterfs-"
        link_dst="glusterfs"

        server_flag="server"
        pkg_dir="glusterfs_all"
        if conf_dict.get("glusterfs_info").get("server_info") is None:
            server_flag="client"
            pkg_dir="glusterfs_client"

        value, msg=common.install(soft_file, link_src, link_dst, pkg_dir, located)

        if value==1:
            if server_flag == "server":
                log.logger.info(f"{soft_name}安装完成")
                command="systemctl enable glusterd &> /dev/null && systemctl start glusterd"
                result=os.system(command)
                if result==0:
                    if common.port_exist(24007, 300):
                        log.logger.info(f"{soft_name}初始化完成")
                    else:
                        log.logger.error(f"{soft_name}初始化超时")
                else:
                    log.logger.error(f"{soft_name}初始化失败: {msg}")
            else:
                log.logger.info(f"{soft_name}客户端安装完成")
        else:
            log.logger.error(f"{soft_name}安装失败: {msg}")

    # 配置
    if action=="start":
        if conf_dict.get("glusterfs_info").get("server_info") is not None:
            gluster_info=conf_dict.get("glusterfs_info").get("server_info")
            volume_dir=gluster_info.get("volume_dir")
            members=gluster_info.get("members")
            mounted_dict=gluster_info.get("mounted")

            os.makedirs(volume_dir, exist_ok=1)

            # 配置集群
            result_list=[]
            create_volume_command=""

            for i in members:
                create_volume_command=f"{create_volume_command} {i}:{volume_dir} "
                add_peer_command=f"gluster peer probe {i} &> /dev/null"
                result=os.system(add_peer_command)
                result_list.append(result)

            if sum(result_list)==0:
                volume_name="g_data"
                N=len(members)
                volume_exist_command=f"gluster volume info {volume_name} &> /dev/null"
                if os.system(volume_exist_command) != 0:
                    create_volume_command=f"gluster volume create {volume_name} replica {N} {create_volume_command} force &> /dev/null"
                    result=os.system(create_volume_command)
                    if result==0:
                        log.logger.info("创建volume成功")
                        start_volume_command=f"gluster volume start {volume_name} &> /dev/null"
                        result=os.system(start_volume_command)
                        if result==0:
                            if common.port_exist(49152, 300):
                                log.logger.info(f"{soft_name}共享存储启动成功")
                        else:
                            log.logger.error("启动volume失败")
                    else:
                        log.logger.error(f"创建volume失败: {result}")
        if conf_dict.get("glusterfs_info").get("client_info") is not None:
            gluster_client_info=conf_dict.get("glusterfs_info").get("client_info")
            mounted_host=gluster_client_info.get("mounted_host")
            mounted_dir=gluster_client_info.get("mounted_dir")

            os.makedirs(mounted_dir, exist_ok=1)
            mounted_str=f"{mounted_host}:g_data {mounted_dir} glusterfs defaults 0 0\n"
            with open("/etc/fstab", "r+") as f:
                 text=f.readlines()
                 if mounted_str not in text:
                     f.write(mounted_str)

            command="mount -a &> /dev/null"
            result=os.system(command)
            if result==0:
                log.logger.info(f"{soft_name}客户端挂载完成")
            else:
                log.logger.error(f"{soft_name}客户端挂载失败: {result}")

if __name__ == "__main__":
    main()
