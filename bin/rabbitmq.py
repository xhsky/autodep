#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, os, json
import tarfile
import psutil

def config(located, cluster_name, member_list, erlang_mem, node_type):
    try:
        config_text=(
                "listeners.tcp.default = 5672\n"
                f"vm_memory_high_watermark.absolute={erlang_mem}M\n"
                "vm_memory_high_watermark_paging_ratio = 0.5\n"
                "log.file.level = info\n"
                f"cluster_name={cluster_name}\n"
                "cluster_formation.peer_discovery_backend = classic_config\n"
                f"cluster_formation.node_type = {node_type}"
                #"cluster_formation.classic_config.nodes.1 ={}\n"
                )
        for index, item in enumerate(member_list):
            node_str=f"cluster_formation.classic_config.nodes.{index+1}=rabbit@{item}"
            config_text=f"{config_text}\n{node_str}"
        mq_config_file=f"{located}/rabbitmq/etc/rabbitmq/rabbitmq.conf"
        with open(mq_config_file, "w") as f:
            f.write(f"{config_text}\n")
        return 1
    except Exception as e:
        return e

def install(soft_file, located):
    os.makedirs(located, exist_ok=1)
    try:
        t=tarfile.open(soft_file)
        t.extractall(path=located)

        for i in os.listdir(located):
            if i.startswith("rabbitmq_server-"):
                src=f"{located}/{i}"
                break

        # 建立软连接
        dst=f"{located}/rabbitmq"
        os.symlink(src, dst)

        # 生成cookie
        cookie_file="/root/.erlang.cookie"
        cookie_context="PWSZLCZPGCLCQZXICHRW"
        with open(cookie_file, "w") as f:
            os.chmod(cookie_file, 0o400)
            f.write(cookie_context)

        pkg_dir=f"{located}/rabbitmq/pkg"
        erlang_file=os.listdir(pkg_dir)[0]
        result=os.system(f"cd {pkg_dir} ; rpm -Uvh {erlang_file} &> /dev/null")
        if result==0 or result==256:        # 256为重新安装返回值
            return 1, "ok"
        else:
            return 0, "RabbitMQ: erlang安装失败"
    except Exception as e:
        return 0, e

def main():
    """
        将erlang.rpm放入rabbitmq.tar.gz的pkg目录中
    """
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")

    # 安装
    if action=="install":
        value, msg=install(soft_file, located)
        if value==1:
            print("RabbitMQ安装完成")
        else:
            print(f"Error: 解压安装包失败: {msg}")
            return 

        mem=psutil.virtual_memory()
        erlang_mem=int(mem[0] * float(weight) /1024/1024)
        cluster_name=conf_dict["rabbitmq_info"]["cluster_name"]
        members=conf_dict["rabbitmq_info"]["members"]
        node_type=conf_dict["rabbitmq_info"]["node_type"]
        value=config(located, cluster_name, members, erlang_mem, node_type)
        if value==1:
            print("RabbitMQ配置优化完成")
        else:
            print(f"RabbitMQ配置优化失败:{value}")

    elif action=="start":
        command=f"cd {located}/rabbitmq ; ./sbin/rabbitmq-server -detached" 
        result=os.system(command)
        if result==0:
            print("RabbitMQ启动完成")
        else:
            print(f"Error: RabbitMQ启动失败")

if __name__ == "__main__":
    main()
