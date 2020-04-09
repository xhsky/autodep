#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import json
#from libs import abc
from libs.client import Client

def connect_test(host_dict):
    """ 判断主机配置信息是否正确
    """

    flag=1
    return_msg={}
    for i in host_dict.keys():
        host=Client()
        ip=host_dict[i].get("ip")
        port=host_dict[i].get("port")
        password=host_dict[i].get("root_password")
        status, msg=host.password_conn(ip, port, password)
        if status!=0:
            flag=0
        return_msg[i]=msg

    return flag, return_msg


def host_init(host_dict):
    """主机环境初始化
        * 生成秘钥
        * 免密码登录
        * 设置hostname
        * 配置hosts
        * 关闭firewalld
        * 关闭selinux
    """

    host=Client()
    if host.gen_keys():
        print("本机生成密钥对")
    else:
        print("本机已存在密钥对")

    hosts={}
    hosts_str="\n"
    for i in host_dict.keys():
        hosts_str=f"{hosts_str}{host_dict[i].get('ip')}\t{i}\n"

    #print(f"{hosts_str=}")
    for i in host_dict.keys():
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


def main():
    with open("./config/init.json") as load_file:
        try:
            load_dict=json.load(load_file)
            flag, connect_msg=connect_test(load_dict)
            if flag==0:
                print("Error: 配置文件有误, 请根据返回信息重新配置并初始化\n")
                for i in connect_msg:
                    print(f"{i}: {connect_msg[i]}")
                exit()
            host_init(load_dict)
        except json.decoder.JSONDecodeError:
            print("Error: json格式不正确")
    
if __name__ == "__main__":
    main()
