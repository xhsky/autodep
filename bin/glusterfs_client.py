#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import tarfile
import psutil

def install(soft_file, located):
    os.makedirs(located, exist_ok=1)

    try:
        t=tarfile.open(soft_file)
        t.extractall(path=located)

        pkgs=" ".join(os.listdir(f"{located}/glusterfs_client/"))
        command=f"cd {located}/glusterfs_client/ &> /dev/null && rpm -Uvh {pkgs} &> /dev/null"
        result=os.system(command)
        # 5120为重新安装rpm返回值
        if result==0 or result==5120:
            return 1, "ok"
        else:
            return 0, "GlusterFS Client rpm包安装失败"
    except Exception as e:
        return 0, e

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)

    # 安装
    if action=="install":
        located=conf_dict.get("located")
        value, msg=install(soft_file, located)
        if value==1:
            print("GlusterFS客户端安装完成")
        else:
            print(f"Error: GlusterFS客户端安装失败: {msg}")

    # 启动
    if action=="start":
        gluster_client_info=conf_dict.get("glusterfs_client_info")
        mounted_host=gluster_client_info.get("mounted_host")
        mounted_dir=gluster_client_info.get("mounted_dir")

        os.makedirs(mounted_dir, exist_ok=1)
        with open("/etc/fstab", "a+") as f:
             f.write(f"{mounted_host}:g_data {mounted_dir} glusterfs defaults 0 0\n")

        command="mount -a"
        result=os.system(command)
        if result==0:
            print(f"GlusterFS客户端挂载完成")
        else:
            print(f"Error: GlusterFS客户端挂载失败")



if __name__ == "__main__":
    main()
