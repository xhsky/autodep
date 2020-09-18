#!../ext/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import json, sys, textwrap
from libs.client import Client
from libs.install import soft
from libs.common import Logger
from libs.doc import dict_to_md

def get_weight(soft_weight_dict, soft_install_list):
    """ 返回各软件占服务器的权重

        soft_install_dict={
            "soft_name": weight, 
            "soft_name": weight, 
        }
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
                    db_format_list=[
                            ["redis_info", dict], 
                            ["redis_info.db_info", dict], 
                            ["redis_info.db_info.redis_password", str]
                            ]
                    status, attr_name=check_format(arch_dict[i], db_format_list)
                    if not status:
                        print(f"Error: '{i}.{attr_name}'配置错误")
                        exit()

                    if arch_dict[i].get("redis_info").get("cluster_info") is not None:
                        cluster_format_list=[
                                ["redis_info.cluster_info", dict], 
                                ["redis_info.cluster_info.role", str], 
                                ["redis_info.cluster_info.master_host", str]
                                ]
                        status, attr_name=check_format(arch_dict[i], cluster_format_list)
                        if not status:
                            print(f"Error: '{i}.{attr_name}'配置错误")
                            exit()

                        role=arch_dict[i].get("redis_info").get("cluster_info").get("role")
                        if role != "slave" and role != "master":
                            print(f"Error: '{i}.redis_info.cluster_info.role'配置错误")
                            exit()
                if j == "glusterfs":
                    format_list=[
                            ["glusterfs_info", dict]
                            ]
                    status, attr_name=check_format(arch_dict[i], format_list)
                    if not status:
                        print(f"Error: '{i}.{attr_name}'配置错误")
                        exit()

                    server_info=arch_dict[i].get("glusterfs_info").get("server_info")
                    client_info=arch_dict[i].get("glusterfs_info").get("client_info")

                    if server_info is not None or client_info is not None:
                        if server_info is not None:
                            server_format_list=[
                                    ["glusterfs_info.server_info.volume_dir", str], 
                                    ["glusterfs_info.server_info.members", list]
                                    ]
                            status, attr_name=check_format(arch_dict[i], server_format_list)
                            if not status:
                                print(f"Error: '{i}.{attr_name}'配置错误")
                                exit()
                        if client_info is not None:
                            client_format_list=[
                                    ["glusterfs_info.client_info.mounted_host", str], 
                                    ["glusterfs_info.client_info.mounted_dir", str]
                                    ]
                            status, attr_name=check_format(arch_dict[i], client_format_list)
                            if not status:
                                print(f"Error: '{i}.{attr_name}'配置错误")
                                exit()
                    else:
                        print(f"Error: '{i}.glusterfs_info.server_info'或'{i}.glusterfs_info.client_info'至少存在一个")
                        exit()
                if j == "mysql":
                    db_format_list=[
                            ["mysql_info", dict], 
                            ["mysql_info.db_info", dict], 
                            ["mysql_info.db_info.root_password", str], 
                            ["mysql_info.db_info.server_id", int], 
                            ["mysql_info.db_info.business_db", list], 
                            ["mysql_info.db_info.business_user", list], 
                            ["mysql_info.db_info.business_password", list], 
                            ]
                    status, attr_name=check_format(arch_dict[i], db_format_list)
                    if not status:
                        print(f"Error: '{i}.{attr_name}'配置错误")
                        exit()

                    if arch_dict[i].get("mysql_info").get("cluster_info") is not None:
                        cluster_format_list=[
                                ["mysql_info.cluster_info", dict], 
                                ["mysql_info.cluster_info.role", str]
                                ]
                        status, attr_name=check_format(arch_dict[i], cluster_format_list)
                        if not status:
                            print(f"Error: '{i}.{attr_name}'配置错误")
                            exit()

                        role=arch_dict[i].get("mysql_info").get("cluster_info").get("role")
                        role_list=["master", "slave"]
                        if role not in role_list:
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

def get_attach_soft(soft_list):
    """
        返回软件集群角色
    """
    pass

    return ", ".join(soft_list)

def set_soft_info_to_md(softname_list, soft_dict):
    info_all=""
    prefix='    '
    located=soft_dict["located"]
    for softname in softname_list:
        if softname=="nginx":
            info=f"""\
                    - {softname}

                        - 后端代理主机: `{', '.join(soft_dict['nginx_info']['proxy_hosts'])}`

                        - 启动: `# cd {located}; ./sbin/nginx`

                        - 关闭: `# cd {located}; ./sbin/nginx -s stop`
                    """
        elif softname=="ffmpeg":
            info=f"""\
                    - {softname}

            """
        elif softname=="jdk":
            info=f"""\
                    - {softname}

            """
        elif softname=="tomcat":
            info=f"""\
                    - {softname}

                        - 启动: `# catalina.sh start`

                        - 关闭: `# catalina.sh stop -force`
            """
        elif softname=="redis":
            redis_cluster_info=soft_dict["redis_info"].get("cluster_info")
            password=soft_dict["redis_info"]["db_info"]["redis_password"]
            if redis_cluster_info is None:
                role="stand-alone"
                sentinel_info=""
            else:
                role=redis_cluster_info.get("role")
                sentinel_info=f"""\
                            - master: {redis_cluster_info["master_host"]} 

                        - sentinel:

                            - 密码: `{password}`

                            - 启动: `# cd {located}/redis ; ./bin/redis-sentinel conf/sentinel.conf`

                            - 关闭: `# cd {located}/redis ; ./bin/redis-cli -p 26379 -a {password} shutdown`
                """

            info=f"""\
                    - {softname}

                        - 角色: {role}

                        - 密码: `{password}`

                        - 启动: `# cd {located}/redis ; ./bin/redis-server conf/redis.conf`

                        - 关闭: `# cd {located}/redis ; ./bin/redis-cli -a {password} shutdown`
            """
            info=f"{textwrap.dedent(info)}\n{textwrap.dedent(sentinel_info)}"
        elif softname=="rabbitmq":
            accounts=""
            if soft_dict["rabbitmq_info"].get("vhosts") is not None:
                account_dict=list(zip(soft_dict["rabbitmq_info"]["vhosts"], soft_dict["rabbitmq_info"]["users"], soft_dict["rabbitmq_info"]["passwords"]))
                for i in account_dict:
                    accounts=f"{accounts}`{i[1]}/{i[2]}({i[0]})`, "
                accounts=f"\n- 虚拟机账号: {accounts[:-2]}\n"

            info=f"""\
                    - {softname}

                        - 集群名称: `{soft_dict["rabbitmq_info"]["cluster_name"]}`

                        - 节点类型: `{soft_dict["rabbitmq_info"]["node_type"]}`

                        - 集群成员: `{', '.join(soft_dict['rabbitmq_info']['members'])}`
            """
            info=f"{textwrap.dedent(info)}{textwrap.indent(accounts, prefix=prefix)}"
            control=f"""\
                    - 启动: `# cd {located}; ./sbin/rabbitmq-server -detached`

                    - 关闭: `# cd {located}; ./sbin/rabbitmqctl stop`
            """
            info=f"{info}\n{textwrap.indent(textwrap.dedent(control), prefix=prefix)}"
        elif softname=="glusterfs":
            server_flag=0
            client_flag=0
            role="all(server and client)"
            if soft_dict["glusterfs_info"].get("server_info") is not None:
                server_flag=1
                role="server"
            if soft_dict["glusterfs_info"].get("client_info") is not None:
                client_flag=1
                role="client"

            info=f"""\
                    - {softname}

                        - 角色: {role}
            """
            if server_flag==1:
                server_info=f"""\
                        - 集群成员: `{', '.join(soft_dict["glusterfs_info"]["server_info"]["members"])}`

                        - 卷目录: `{soft_dict["glusterfs_info"]["server_info"]["volume_dir"]}`
                """
                info=f"{textwrap.dedent(info)}\n{textwrap.indent(textwrap.dedent(server_info), prefix=prefix)}"
            if client_flag==1:
                client_info=f"""\
                        - 挂载主机: `{soft_dict["glusterfs_info"]["client_info"]["mounted_host"]}`

                        - 挂载目录: `{soft_dict["glusterfs_info"]["client_info"]["mounted_dir"]}`
                """
                info=f"{textwrap.dedent(info)}\n{textwrap.indent(textwrap.dedent(client_info), prefix=prefix)}"
            control_info=f"""\
                    - 启动: `systemctl start glusterd`

                    - 关闭: `systemctl stop glusterd`
            """
            info=f"{info}\n{textwrap.indent(textwrap.dedent(control_info), prefix=prefix)}"

        elif softname=="mysql":
            accounts_list=list(zip(soft_dict['mysql_info']['db_info']['business_db'],soft_dict['mysql_info']['db_info']['business_user'], soft_dict['mysql_info']['db_info']['business_password']))
            accounts=""
            for i in accounts_list:
                accounts=f"{accounts}`{i[1]}/{i[2]}({i[0]})`, "
            #info=f"{textwrap.dedent(info)}{textwrap.indent(accounts, prefix=prefix)}"

            role="stand-alone"
            slave_info=""
            if soft_dict["mysql_info"].get("cluster_info") is not None:
                role=soft_dict["mysql_info"]["cluster_info"]["role"]
                if role=="slave":
                    slave_info=f"""\
                            - 同步主机: `{soft_dict['mysql_info']['cluster_info']['sync_host']}`

                            - 同步数据库: `{', '.join(soft_dict['mysql_info']['cluster_info']['sync_dbs'])}`

                    """

            info=f"""\
                    - {softname}

                        - 管理员密码: `{soft_dict['mysql_info']['db_info']['root_password']}`

                        - 数据库账号: {accounts[:-2]}

                        - 角色: {role}
                """
            #cluster_info=f"- 角色: {role}\n\n{textwrap.dedent(slave_info)}"
            control_info=f"""\
                    - 启动: `# systemctl start mysqld`

                    - 关闭: `# systemctl stop mysqld`
            """
            info=f"{textwrap.dedent(info)}\n{textwrap.indent(textwrap.dedent(slave_info), prefix=prefix)}{textwrap.indent(textwrap.dedent(control_info), prefix=prefix)}"

        elif softname=="elasticsearch":
            info=f"""\
                    - {softname}

                        - 集群名称: `{soft_dict['elasticsearch_info']['cluster_name']}`

                        - 集群成员: `{', '.join(soft_dict['elasticsearch_info']['members'])}`

                        - 启动: `# cd {located}/es;  ./bin/elasticsearch -d -p elasticsearch.pid`

                        - 关闭: ```# cd {located}/es; kill `cat elasticsearch.pid` ```
            """
        else: 
            info=f"""\
                    - {softname}

            """
        info_all=f"{info_all}\n{textwrap.dedent(info)}"
    return info_all

def to_doc(host_info_dict, arch_info_dict):
    """

    ## 主机信息列表
    ## 安装信息列表
    ## 软件信息
    
    """
    with open("./config/project", "r") as f:
        project_name=f.read().strip()
    if project_name == '':
        project_name="项目部署文档"
    else:
        project_name=f"项目({project_name})部署文档"

    md=dict_to_md(project_name)

    # 主机信息列表
    host_info_table=[
            {"IP": "ip"}, 
            {"SSH端口": "port"}, 
            {"root密码": "root_password"}
            ]
    host_info_table_md=md.to_table("主机名", host_info_table, host_info_dict)
    host_info_header={
            "2": ["主机信息列表", 1], 
            }
    md.add_content(host_info_header, host_info_table_md)

    # 安装信息列表
    install_info_table=[
            {"安装软件": "soft"}, 
            {"安装目录": "located"}
            ]
    install_info_dict={}
    for i in arch_info_dict:
        install_info_dict[i]={
                "soft": get_attach_soft(arch_info_dict[i]["software"]), 
                "located": arch_info_dict[i]["located"]
                }
    install_info_header={
            "2": ["安装信息列表", 2], 
            }
    install_info_table_md=md.to_table("主机名", install_info_table, install_info_dict)
    md.add_content(install_info_header, install_info_table_md)

    # 软件信息
    n=0
    for i in arch_info_dict:
        n=n+1
        soft_info_header={
                "2":["软件信息列表", 2], 
                "3":[f"主机{i}", n]
                }
        info=set_soft_info_to_md(arch_info_dict[i]["software"], arch_info_dict[i])
        md.add_content(soft_info_header, info)

    md.write_to_file()
    return f"{project_name}.md"

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

    args=sys.argv[:]
    if args is None or len(args) != 2:
        print(f"Usage: {args[0]} install|start")
        exit()

    log_dir=conf_dict["log"]["log_dir"]
    log_file=f"{log_dir}/autodep.log"
    log_level=conf_dict["log"]["log_level"]
    log=Logger(log_file, log_level)

    file_name, action=args
    ssh=Client()
    if action=="install":
        log.logger.info("开始集群部署...\n")
        for host_name in arch_dict:
            log.logger.info(f"{host_name}部署...")
            soft_install_dict=get_weight(conf_dict["software"], arch_dict[host_name].get("software"))
            for soft_name in soft_install_dict:
                log.logger.info(f"{soft_name}开始安装...")
                port=init_dict[host_name].get("port")
                soft_obj=soft(host_name, port)
                weight=soft_install_dict[soft_name]
                # 去除located结尾的/
                located_dir=arch_dict[host_name]["located"]
                if located_dir.endswith("/"):
                    arch_dict[host_name]["located"]=located_dir[0:-1]

                ssh.scp(host_name, port, "root", "./libs/common.py", "/opt/python3/code/libs/common.py")
                status=soft_obj.control(soft_name, action, weight, conf_dict["location"].get(soft_name), f"'{json.dumps(arch_dict.get(host_name))}'")

                for line in status[1]:
                    if line is not None:
                        log.logger.info(line.strip("\n"))
                for line in status[2]:
                    if line is not None:
                        log.logger.error(line.strip("\n"))
                log.logger.info(f"{soft_name}结束安装...\n")
        else:
            log.logger.info("集群部署完成...")

    elif action=="start":
        log.logger.info("开始集群启动...\n")
        for host_name in arch_dict:
            log.logger.info(f"{host_name}启动...")
            for soft_name in arch_dict[host_name].get("software"):
                log.logger.info(f"{soft_name}开始启动...")
                port=init_dict[host_name].get("port")
                soft_obj=soft(host_name, port)
                # 去除located结尾的/
                located_dir=arch_dict[host_name]["located"]
                if located_dir.endswith("/"):
                    arch_dict[host_name]["located"]=located_dir[0:-1]
                ssh.scp(host_name, port, "root", "./libs/common.py", "/opt/python3/code/libs/common.py")
                status=soft_obj.control(soft_name, action, None, conf_dict["location"].get(soft_name), f"'{json.dumps(arch_dict.get(host_name))}'")

                for line in status[1]:
                    if line is not None:
                        if line == ".\r\n":
                            #log.logger.info(".", end="")
                            print(".", end="")
                            sys.stdout.flush()
                        else:
                            log.logger.info(line.strip("\n"))
                for line in status[2]:
                    if line is not None:
                        log.logger.error(line.strip("\n"))
                log.logger.info(f"{soft_name}启动完毕...\n")
        else:
            log.logger.info("集群启动完毕...\n")
            log.logger.info("开始生成部署文档...")
            project_file=to_doc(init_dict, arch_dict)
            log.logger.info(f"部署文档{(project_file)}生成完毕...")
    else:
        print(f"Usage: {args[0]} install|start")

if __name__ == "__main__":
    main()
