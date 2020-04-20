#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import json
#from libs import abc
from libs.client import Client
from libs.install import soft

def connect_test(host_dict):
    """ 判断主机配置信息是否正确
    """

    flag=1
    return_msg={}
    for i in host_dict.keys():
        if i != "local_name":
            host=Client()
            ip=host_dict[i].get("ip")
            port=host_dict[i].get("port")
            password=host_dict[i].get("root_password")
            status, msg=host.password_conn(ip, port, password)
            if status!=0:
                flag=0
            return_msg[i]=msg

    return flag, return_msg

def host_init(host_dict, conf_dict):
    """主机环境初始化
        * 生成秘钥
        * 免密码登录
        * 设置hostname
        * 配置hosts
        * 关闭firewalld
        * 关闭selinux
        * 配置Python3环境
    """

    host=Client()
    soft_install=soft()
    if host.gen_keys():
        print("本机生成密钥对\n")
    else:
        print("本机已存在密钥对\n")

    hosts={}
    hosts_str="\n"
    python3_path=conf_dict.get("python3")
    for i in host_dict.keys():
        if i != "local_name":
            hosts_str=f"{hosts_str}{host_dict[i].get('ip')}\t{i}\n"

    for i in host_dict.keys():
        if i != "local_name":
            print(f"主机{i}环境初始化...")
            ip=host_dict[i].get("ip")
            port=host_dict[i].get("port")
            password=host_dict[i].get("root_password")

            hostname=f"{i}.dream.org"
            hostname_cmd=f"hostnamectl set-hostname {hostname}"
            firewalld_cmd=f"systemctl disable firewalld; systemctl stop firewalld"
            selinux_cmd=f"setenforce 0"
            hosts_cmd=f"echo '{hosts_str}' >> /etc/hosts"

            host.free_pass_set(ip, port, password)
            print(f"{i}免密码登录设置完成")

            host.exec(ip, port, hostname_cmd)
            print(f"{i}设置主机名为{hostname}")

            host.exec(ip, port, firewalld_cmd)
            print(f"{i}已关闭防火墙")

            host.exec(ip, port, selinux_cmd)
            print(f"{i}已关闭SELinux")

            host.exec(ip, port, hosts_cmd)
            print(f"{i}添加hosts")

            status=soft_install.tar_install(python3_path, ip, port, "/opt")
            flag=status[1].read().decode('utf8').strip()
            if flag!='0':
                print("Python3安装报错: status[2].read().decode('utf8')")
            else:
                print(f"{i}配置Python3环境")

            print("")

def host_msg(host_dict):
    """获取主机信息
    """
    host=Client()
    get_msg_py="./bin/host.py"
    for i in host_dict.keys():
        if i != "local_name":
            ip=host_dict[i].get("ip")
            port=host_dict[i].get("port")

            remote_file=f"/tmp/{get_msg_py.split('/')[-1]}"
            host.scp(ip, port, "root", get_msg_py, remote_file)
            get_msg_command=f"/opt/python3/bin/python3 {remote_file}"
            status=host.exec(ip, port, get_msg_command)

            #print(f"Error: {i}无法获取主机信息: {status[2].read().decode('utf8')}")
            print(f"{status[1].read().decode('utf8')}")

def main():
    init_file="./config/init.json"
    conf_file="./config/conf.json"
    with open(init_file, 'r') as init_f, open(conf_file, 'r') as conf_f:
        try:
            init_dict=json.load(init_f)
            try:
                conf_dict=json.load(conf_f)
            except json.decoder.JSONDecodeError:
                print(f"Error: 配置文件({conf_file})json格式不正确")
            else:
                flag, connect_msg=connect_test(init_dict)
                if flag==0:
                    print(f"Error: 配置文件({init_file})有误, 请根据返回信息重新配置并初始化\n")
                    for i in connect_msg:
                        print(f"{i}: {connect_msg[i]}")
                    exit()
                print("主机初始化..")
                host_init(init_dict, conf_dict)
                print("初始化完成\n\n各主机信息如下:")
                host_msg(init_dict)
        except json.decoder.JSONDecodeError:
            print(f"Error: 配置文件({init_file})json格式不正确")
    
if __name__ == "__main__":
    main()
