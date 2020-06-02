#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import json
from libs.client import Client
from libs.install import soft
from itertools import zip_longest

def get_weight(soft_weight_dict, soft_install_list):
    """ 返回各软件占服务器的权重
    """
    soft_install_dict={}
    for i in soft_install_list:
        soft_install_dict[i]=soft_weight_dict[i]
    weight_sum=sum(soft_install_dict.values())+1		# 1为系统权重
    
    for i in soft_install_dict:
        soft_install_dict[i]=round(soft_install_dict[i]/weight_sum, 2)
    return soft_install_dict

def json_ana():
    pass

def main():
    arch_file="./config/arch.json"
    init_file="./config/init.json"
    conf_file="./config/conf.json"
    with open(arch_file, "r") as arch_f, open(init_file, "r") as init_f, open(conf_file, "r") as conf_f:
        try:
            arch_dict=json.load(arch_f)
            try:
                init_dict=json.load(init_f)
                try:
                    conf_dict=json.load(conf_f)
                except json.decoder.JSONDecodeError:
                    print(f"Error: 配置文件({conf_file})json格式不正确")
                    exit()
            except json.decoder.JSONDecodeError:
                print(f"Error: 配置文件({init_file})json格式不正确")
                exit()
        except json.decoder.JSONDecodeError:
            print(f"Error: 配置文件({arch_file})json格式不正确")
            exit()

    json_ana()

    # 部署
    print("开始集群部署...")

    # 安装
    for i in arch_dict:
        print(f"\n{i}部署...")
        soft_install_dict=get_weight(conf_dict["software"], arch_dict[i].get("software"))
        action="install"
        #for j in arch_dict[i].get("software"):
        for j in soft_install_dict:
            print(f"\n安装并配置{j}...")
            port=init_dict[i].get("port")
            soft_obj=soft(i, port)
            weight=soft_install_dict[j]
            status=soft_obj.control(j, action, weight, conf_dict["location"].get(j), f"'{json.dumps(arch_dict.get(i))}'")

            for line in status[1]:
                if line is not None:
                    print(line.strip("\n"))
            for line in status[2]:
                if line is not None:
                    print(line.strip("\n"))

    # 启动
    for i in arch_dict:
        print(f"\n{i}部署...")
        action="start"
        for j in arch_dict[i].get("software"):
            print(f"\n启动并配置{j}...")
            port=init_dict[i].get("port")
            soft_obj=soft(i, port)
            status=soft_obj.control(j, action, weight, conf_dict["location"].get(j), f"'{json.dumps(arch_dict.get(i))}'")

            for line in status[1]:
                if line is not None:
                    print(line.strip("\n"))
            for line in status[2]:
                if line is not None:
                    print(line.strip("\n"))



    
    
if __name__ == "__main__":
    main()
