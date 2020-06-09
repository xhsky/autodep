#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import tarfile
import psutil

def install(soft_file, located, server_flag):
    os.makedirs(located, exist_ok=1)
    try:
        t=tarfile.open(soft_file)
        t.extractall(path=located)

        pkgs=" ".join(os.listdir(f"{located}/glusterfs_{server_flag}/"))
        #command=f"cd {located}/glusterfs_{server_flag}/ &> /dev/null && rpm -Uvh {pkgs} &> /dev/null"
        command=f"cd {located}/glusterfs_{server_flag}/ &> /dev/null && yum install -y {pkgs} &> /dev/null"
        result=os.system(command)
        # 256为重新安装rpm返回值
        if result==0 or result==256:
            return 1, "ok"
        else:
            return 0, "GlusterFS rpm包安装失败"
    except Exception as e:
        return 0, e

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)

    # 安装
    if action=="install":
        located=conf_dict.get("located")
        server_flag="server"
        if conf_dict.get("glusterfs_info").get("server_info") is None:
            server_flag="client"
        value, msg=install(soft_file, located, server_flag)
        if value==1:
            if server_flag == "server":
                command="systemctl enable glusterd &> /dev/null && systemctl start glusterd"
                result=os.system(command)
                print("GlusterFS安装完成")
            else:
                print("GlusterFS客户端安装完成")
        else:
            print(f"Error: GlusterFS安装失败: {msg}")

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
                create_volume_command=f"gluster volume create {volume_name} replica {N} {create_volume_command} force &> /dev/null"
                result=os.system(create_volume_command)
                if result==0:
                    start_volume_command=f"gluster volume start {volume_name} &> /dev/null"
                    result=os.system(start_volume_command)
                    if result==0:
                        print("GlusterFS共享存储创建成功")
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

            command="mount -a"
            result=os.system(command)
            if result==0:
                print(f"GlusterFS客户端挂载完成")
            else:
                print(f"Error: GlusterFS客户端挂载失败")

if __name__ == "__main__":
    main()
