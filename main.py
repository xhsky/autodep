#!/usr/bin/env python3
# *-* coding:utf8 *-*
# sky

import json
from libs.client import Client
from libs.install import soft
from itertools import zip_longest

def get_weight():
    pass
    return 0.8

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

    # 安装
    print("开始集群部署...\n")
    for i in arch_dict.keys():
        weight=get_weight()
        print(f"{i}部署...")
        for j in arch_dict[i].get("software"):
            print(f"\n安装并配置{j}...")
            port=init_dict[i].get("port")
            soft_obj=soft(i, port)
            status=soft_obj.install(j, weight, conf_dict.get(j), f"'{json.dumps(arch_dict.get(i))}'")

            for line in status[1]:
                if line is not None:
                    print(line.strip("\n"))
            for line in status[2]:
                if line is not None:
                    print(line.strip("\n"))

    # 启动



    
    
if __name__ == "__main__":
    main()
