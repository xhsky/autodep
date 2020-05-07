#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import tarfile
import psutil
import shutil

def install(soft_file, located):
    os.makedirs(located, exist_ok=1)

    try:
        t=tarfile.open(soft_file)
        t.extractall(path=located)

        pkgs=" ".join(os.listdir(f"{located}/glusterfs_pkgs/"))
        command=f"cd {located}/glusterfs_pkgs/ &> /dev/null && rpm -Uvh {pkgs} &> /dev/null"
        result=os.system(command)
        # 4864为重新安装rpm返回值
        if result==0 or result==4864:
            return 1, "ok"
        else:
            return 0, "GlusterFS rpm包安装失败"
    except Exception as e:
        return 0, e

def main():
    weight, soft_file, conf_json=sys.argv[1:4]
    conf_dict=json.loads(conf_json)

    # 安装
    located=conf_dict.get("located")
    value, msg=install(soft_file, located)
    if value==1:
        print("GlusterFS安装完成")
    else:
        print(f"Error: GlusterFS安装失败: {msg}")
        return 

    # 配置

    gluster_info=conf_dict.get("glusterfs_info")

    volume_dir=gluster_info.get("volume_dir")
    members=gluster_info.get("members")
    mounted_dict=gluster_info.get("mounted")

    result=os.system("systemctl enable glusterd &> /dev/null && systemctl start glusterd")
    if result==0:
        print(f"GlusterFS初始化启动完成")
    return 0

    # 获取密码
    try:
        with open(f"{located}/mysql/mylog/mysqld.log", "r") as f:
            for i in f.readlines():
                if "temporary password" in i:
                    pass_line=i.split(" ")
                    init_password=pass_line[-1].strip()
                    break
    except Exception as e:
        print(f"Error: MySQL初始化失败: {e}")
        exit()

    root_password=db_info.get("root_password")
    change_pass_command=f"mysqladmin  -uroot -p'{init_password}' password {root_password} &> /dev/null"
    value=os.system(f"{change_pass_command}")
    if value==0:
        print("MySQL更改初始密码完成")
    else:
        print(f"MySQL更改初始密码失败:{value}")
        exit()
    
    # 创建自定义用户和数据库
    init_sql_list=[]
    for db_name, user_name, user_password in zip(db_info.get("business_db"), db_info.get("business_user"), db_info.get("business_password")):
        db_sql=f"create database {db_name};"
        use_sql=f"use {db_name};"
        user_sql=f"create user '{user_name}'@'%' identified by '{user_password}';"
        grant_sql=f"grant all on {db_name}.* to '{user_name}'@'%';"
        init_sql_list.append(db_sql)
        init_sql_list.append(user_sql)
        init_sql_list.append(grant_sql)
    init_sql=" ".join(init_sql_list)
    init_commands=f'export MYSQL_PWD="{root_password}" ; echo "{init_sql}" | mysql -uroot'
    value=os.system(init_commands)
    if value==0:
        print("MySQL用户配置完成")
    else:
        print(f"MySQL用户配置失败:{value}")

    # 集群
    if cluster_flag==1:
        cluster_commands=f'export MYSQL_PWD="{root_password}" ; echo "{sync_sql}" | mysql -uroot'
        value=os.system(cluster_commands)
        if value==0:
            print(f"MySQL({role})配置完成")
        else:
            print(f"MySQL({role})配置失败:{value}")


if __name__ == "__main__":
    main()
