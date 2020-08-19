#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# Date: 2020年 08月 11日 星期二 15:28:06 CST
# sky

import sys, os, json, time
import tarfile
import psutil

def config(located, cluster_name, memeber_list, jvm_mem):
    try:
        config_text=(
                f"cluster.name: {cluster_name}\n"
                #"node.name: es_node\n"
                "node.master: true\n"
                "node.voting_only: false\n"
                "node.data: true\n"
                "node.ingest: true\n"
                "network.host: 0.0.0.0\n"
                "http.port: 9200\n"
                f"discovery.seed_hosts: {memeber_list}\n"
                "transport.tcp.port: 9300\n"
                "gateway.recover_after_nodes: 1\n"
                "action.destructive_requires_name: true\n"
                )
        es_config_file=f"{located}/es/config/elasticsearch.yml"
        with open(es_config_file, "w") as f:
            f.write(config_text)

        jvm_config_file=f"{located}/es/config/jvm.options"
        with open(jvm_config_file, "r+") as f:
            raw_text=f.readlines()
            xms_index=raw_text.index('-Xms1g\n')
            xmx_index=raw_text.index('-Xmx1g\n')
            raw_text[xms_index]=f"-Xms{jvm_mem}m\n"
            raw_text[xmx_index]=f"-Xmx{jvm_mem}m\n"
            f.seek(0)
            f.writelines(raw_text)
        return 1
    except Exception as e:
        return e

def install(soft_file, located):
    os.makedirs(located, exist_ok=1)
    try:
        t=tarfile.open(soft_file)
        t.extractall(path=located)
        return 1, "ok"
    except Exception as e:
        return 0, e

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")

    # 安装
    if action=="install":
        value, msg=install(soft_file, located)
        if value==1:
            print("ElasticSearch安装完成")
        else:
            print(f"Error: 解压安装包失败: {msg}")
            return 

        # 配置
        for i in os.listdir(located):
            if i.startswith("elasticsearch-"):
                src=f"{located}/{i}"
        try:
            dst=f"{located}/es"
            # 建立软连接
            os.symlink(src, dst)

            os.system("useradd elastic")
            limit_conf="/etc/security/limits.conf"
            if os.path.exists(limit_conf):
                limit_conf_context=(
                        "elastic    -   memlock unlimited\n"
                        "elastic    -   fsize   unlimited\n"
                        "elastic    -   as  unlimited\n"
                        "elastic    -   nofile  65536\n"
                        "elastic    -   nproc   65536\n"
                        )
                with open(limit_conf, "a+") as f:
                    f.write(limit_conf_context)
            else:
                print(f"{limit_conf}文件不存在")

            sysctl_conf="/etc/sysctl.d/es.conf"
            sysctl_conf_context="vm.max_map_count=262144\n"
            with open(sysctl_conf, "w+") as f:
                f.write(sysctl_conf_context)

            os.system(f"chown -R elastic:elastic {src} ; sysctl -p")

        except Exception as e:
            print(f"Error: ElasticSearch配置环境变量出错: {e}")
        else:
            print(f"ElasticSearch配置环境变量完成")


        mem=psutil.virtual_memory()
        jvm_mem=int(mem[0] * float(weight) /1024/1024)
        cluster_name=conf_dict["elasticsearch_info"]["cluster_name"]
        members=conf_dict["elasticsearch_info"]["members"]
        value=config(located, cluster_name, members, jvm_mem)
        if value==1:
            print("ElasticSearch配置优化完成")
        else:
            print(f"ElasticSearch配置优化失败:{value}")

    elif action=="start":
        command=f"set -m ; {located}/es/ &> /dev/null" 
        result=os.system(command)
        if result==0:
            print("ElasticSearch启动完成")
        else:
            print(f"Error: ElasticSearcht启动失败")

if __name__ == "__main__":
    main()
