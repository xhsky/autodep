#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import tarfile
import os, time

def port_exist(port, seconds):
    N=0
    while True:
        time.sleep(1)
        N=N+1
        if N >= seconds:
            return 0
        for i in psutil.net_connections():
            if port==i[3][1] and i[6] is not None:
                print("\n")
                return 1
        print(".")

def install(soft_file, soft_name, link_dst, pkg_dirs, located):
    os.makedirs(located, exist_ok=1)

    try:
        # 解压
        t=tarfile.open(soft_file)
        t.extractall(path=located)

        # 建立软连接
        for i in os.listdir(located):
            if i.startswith("soft_name"):
                src=f"{located}/i"
                break
        dst=f"{located}/link_dst"
        os.symlink(src, dst)

        # 安装依赖
        if pkg_dirs not None:
            pkgs=" ".join(os.listdir(pkg_dirs))
            command=f"cd {located}/{pkg_dirs} && rpm -Uvh {pkgs} &> /dev/null"
            result=os.system(command)
            if result==0 or result==256:    # 256为重新安装rpm返回值
                return 1, "ok"
            else:
                return 0, "安装失败"
    except Exception as e:
        return 0, e

def config(config_dict):
    """
    config_dict={
        config1:{
            config_file: /path/dir/file, 
            config_context: str
        }, 
        config2:{
            config_file: /path/dir/file, 
            config_context: str
        } 
    }
    """

    for config in conf_dict:
        with open(config[config_file], "w") as f:
            f.write(config_context)

def main():
    
if __name__ == "__main__":
    main()
