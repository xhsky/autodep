#!../ext/python3/bin/python3
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

def json_ana(init_dict, conf_dict, arch_dict):
    init_host_list=init_dict.keys()

    # arch.json中是否存在未初始化主机
    not_init_host_list=[]
    for i in arch_dict:
        if i not in init_host_list:
            not_init_host_list.append(i)
    if not_init_host_list != []:
        print(f"Error: 未初始化主机列表: {not_init_host_list}")
        exit()

    # 判断主机属性 attr
    attr={"software": list, "located": str}
    for i in arch_dict:
        for j in attr:
            if arch_dict[i].get(j) is None or not isinstance(arch_dict[i].get(j), attr[j]):
                print(f"Error: '{i}.{j}'配置错误")
                exit()
    soft_list=conf_dict.get("software").keys()
    check(arch_dict, soft_list, init_host_list)

def check_format(arch_host_dict, format_list):
    for i in format_list:
        #attrs=i[0].split(".")
        attr_type=arch_host_dict
        for j in i[0].split("."):
            attr_type=attr_type.get(j)
        if not isinstance(attr_type, i[1]):
            return 0, i[0]
    else:
        return 1, "sucessful"

def check(arch_dict, soft_list, init_host_list):
    for i in arch_dict:
        to_install_soft_list=arch_dict[i].get("software")
        # 判断software中是否有重复项
        if len(to_install_soft_list)!=len(set(to_install_soft_list)):
            print(f"Error: {i}.software中有重复项: {to_install_soft_list}")
            exit()
        # 各软件配置信息校验
        for j in to_install_soft_list:
            if j in soft_list:
                if j == "nginx":
                    format_list=[
                            ["nginx_info", dict], 
                            ["nginx_info.proxy_hosts", list]
                            ]
                    status, attr_name=check_format(arch_dict[i], format_list)
                    if not status:
                        print(f"Error: '{i}.{attr_name}'配置错误")
                        exit()
                if j == "jdk":
                    pass
                if j == "tomcat":
                    pass
                if j == "ffmpeg":
                    pass
                if j == "redis":
                    format_list=[
                            ["redis_info", dict], 
                            ["redis_info.db_info", dict], 
                            ["redis_info.cluster_info", dict], 
                            ["redis_info.db_info.redis_password", str], 
                            ["redis_info.cluster_info.role", str], 
                            ["redis_info.cluster_info.master_host", str]
                            ]
                    status, attr_name=check_format(arch_dict[i], format_list)
                    if not status:
                        print(f"Error: '{i}.{attr_name}'配置错误")
                        exit()

                    role=arch_dict[i].get("redis_info").get("cluster_info").get("role")
                    if role != "slave" and role != "master":
                        print(f"Error: '{i}.redis_info.cluster_info.role'配置错误")
                        exit()
                if j == "glusterfs":
                    format_list=[]
                if j == "mysql":
                    format_list=[
                            ["mysql_info", dict], 
                            ["mysql_info.db_info", dict], 
                            ["mysql_info.cluster_info", dict], 
                            ["mysql_info.db_info.root_password", str], 
                            ["mysql_info.db_info.server_id", int], 
                            ["mysql_info.db_info.business_db", list], 
                            ["mysql_info.db_info.business_user", list], 
                            ["mysql_info.db_info.business_password", list], 
                            ["mysql_info.cluster_info.role", str]
                            ]
                    status, attr_name=check_format(arch_dict[i], format_list)
                    if not status:
                        print(f"Error: '{i}.{attr_name}'配置错误")
                        exit()

                    role=arch_dict[i].get("mysql_info").get("cluster_info").get("role")
                    if role != "slave" and role != "master":
                        print(f"Error: '{i}.mysql_info.cluster_info.role'配置错误")
                        exit()
                    if role == "slave":
                        sync_format_list=[
                                ["mysql_info.cluster_info.sync_host", str], 
                                ["mysql_info.cluster_info.sync_dbs", list]
                                ]
                        status, attr_name=check_format(arch_dict[i], sync_format_list)
                        if not status:
                            print(f"Error: '{i}.{attr_name}'配置错误")
                            exit()
            else:
                print(f"Error: {i}.software中'{j}'不支持")
                exit()
                
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

    json_ana(init_dict, conf_dict, arch_dict)

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

    print("开始集群启动...")
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
