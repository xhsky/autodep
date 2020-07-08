#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import tarfile
import psutil
import shutil

def my_cnf_conf(located, N, mem):
    my_cnf=f""" [mysqld]
# dir
datadir={located}/mysql/mydata
#secure_file_priv=/var/lib/mysql-files
pid_file={located}/mysql/mydata/mysqld.pid

# network
#socket=/tmp/mysql.sock
max_connections=1500

# general set
lower_case_table_names=1
default_authentication_plugin=mysql_native_password
default-time-zone='+08:00'
wait_timeout=30

# Log 
## Error Log
log_error={located}/mysql/mylog/mysqld.log
log_timestamps=system
## Slow log
log_output=file
slow_query_log=1
long_query_time=2

# bin log
server_id={N}
log_bin={located}/mysql/mylog/binlog/binlog
binlog_format=row
binlog_row_event_max_size=8192
binlog_checksum=crc32
max_binlog_size=512M

binlog_cache_size=128K
binlog_stmt_cache_size=32K
max_binlog_cache_size=8G
max_binlog_stmt_cache_size=2G

binlog_error_action=abort_server
binlog_expire_logs_seconds=0

sync_binlog=1
binlog_group_commit_sync_delay=0

default_storage_engine=innodb
transaction_write_set_extraction=xxhash64

# innodb
gtid_mode=on
enforce_gtid_consistency=1
## buffer pool
innodb_buffer_pool_size={mem}M
innodb_change_buffer_max_size=25
innodb_buffer_pool_instances=8

## redo log
innodb_log_group_home_dir={located}/mysql/mylog/redolog
innodb_log_file_size=256M
innodb_log_files_in_group=4

## log buffer
innodb_log_buffer_size=16M
innodb_flush_log_at_trx_commit=1

## tablespace
### system tablespace
innodb_file_per_table=1
### undo tablespace
innodb_undo_directory={located}/mysql/mylog/undolog
innodb_rollback_segments=128
innodb_max_undo_log_size=1G


!include /etc/my_client.cnf

log_slave_updates=1
[client]
"""

    my_cnf_file=f"/etc/my.cnf"
    with open(my_cnf_file, "w") as f:
        f.write(my_cnf)

def install(soft_file, located):
    """
        二进制安装, 需要libaio
        1.mysql-8.0.19-linux-glibc2.12-x86_64.tar.xz解压
        2.将liabio放入其中新建的pkg目录
        3.更改目录名为mysql8并重新压缩
    """
    os.makedirs(located, exist_ok=1)

    try:
        result=os.system("groupadd mysql && useradd -r -g mysql -s /bin/false mysql")
        if result != 0:
            return 0, "MySQL: 创建MySQL用户失败"

        t=tarfile.open(soft_file)
        t.extractall(path=located)
        libaio_file=os.listdir(f"{located}/mysql8/pkg/")[0]
        result=os.system(f"cd {located}/mysql8/pkg &> /dev/null && rpm -Uvh {libaio_file} &> /dev/null")
        # 1792为重新安装rpm返回值
        if result==0 or result==1792:
            return 1, "ok"
        else:
            return 0, "MySQL: libaio安装失败"
    except Exception as e:
        return 0, e

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)

    mysql_info=conf_dict.get("mysql_info")
    db_info=mysql_info.get("db_info")
    located=conf_dict.get("located")

    # 安装
    if action == "install":
        value, msg=install(soft_file, located)
        if value==1:
            print("MySQL安装完成")
        else:
            print(f"Error: MySQL安装失败: {msg}")
            return 

        # 配置
        mem=psutil.virtual_memory()
        mem=int(mem[0] * float(weight) /1024/1024)

        server_id=db_info.get("server_id")

        my_cnf_conf(located, server_id, mem)

        mk_dirs_commands=f"mkdir -p {located}/mysql/{{mydata,mylog}}; mkdir -p {located}/mysql/mylog/{{binlog,redolog,undolog,relay}}; chown -R mysql:mysql {located}/mysql ; ln -s {located}/mysql8 /usr/local/mysql && \cp -f {located}/mysql8/support-files/mysql.server /etc/init.d/mysqld && systemctl daemon-reload"
        result=os.system(mk_dirs_commands)
        if result==0:
            print("MySQL配置完成")
        else:
            print("Error: MySQL配置失败")

    elif action=="start":
        cluster_info=mysql_info.get("cluster_info")
        cluster_flag=0
        if cluster_info is not None:
            cluster_flag=1
            role=cluster_info.get("role")
            if role == "master":
                sync_sql=f"create user 'repl'@'%' identified with mysql_native_password by 'DreamSoft_123456'; grant replication slave on *.* to 'repl'@'%';"
            elif role == "slave":
                my_client_cnf=f"[mysqld]\n#replication\n## master\n## slave\n### relay log\nrelay_log={located}/mysql/mylog/relay/relay\nrelay_log_info_repository=table\n"
                my_cnf_file="/etc/my_client.cnf"
                with open(my_cnf_file, "w") as f:
                    f.write(my_client_cnf)
                sync_host=cluster_info.get("sync_host")
                sync_dbs_list=cluster_info.get("sync_dbs")
                with open(my_cnf_file, "a") as f:
                    for i in sync_dbs_list:
                        f.write(f"replicate_do_db={i}\n")
                sync_sql=f"change master to master_host='{sync_host}',  master_user='repl',  master_password='DreamSoft_123456',  master_auto_position=1; start slave;"

        print(f"MySQL初始化中...")
        init_and_start_command=f"{located}/mysql8/bin/mysqld --initialize --user=mysql && systemctl start mysqld"
        os.system(init_and_start_command)
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
            return 1

        root_password=db_info.get("root_password")
        change_pass_command=f"{located}/mysql8/bin/mysqladmin  -uroot -p'{init_password}' password {root_password} &> /dev/null"
        value=os.system(f"{change_pass_command}")
        if value==0:
            print("MySQL更改初始密码完成")
        else:
            print(f"MySQL更改初始密码失败:{value}")
            return 1
        
        # 创建自定义用户和数据库
        init_sql_list=[]
        for db_name, user_name, user_password in zip(db_info.get("business_db"), db_info.get("business_user"), db_info.get("business_password")):
            db_sql=f"create database {db_name};"
            use_sql=f"use {db_name};"
            user_sql=f"create user '{user_name}'@'%' identified by '{user_password}';"
            grant_sql=f"grant all on {db_name}.* to '{user_name}'@'%';"
            init_sql_list.append(db_sql)
            init_sql_list.append(use_sql)
            init_sql_list.append(user_sql)
            init_sql_list.append(grant_sql)
        init_sql=" ".join(init_sql_list)
        init_commands=f'export MYSQL_PWD="{root_password}" ; echo "{init_sql}" | {located}/mysql8/bin/mysql -uroot'
        value=os.system(init_commands)
        if value==0:
            print("MySQL用户配置完成")
        else:
            print(f"MySQL用户配置失败:{value}")

        # 集群
        if cluster_flag==1:
            cluster_commands=f'export MYSQL_PWD="{root_password}" ; echo "{sync_sql}" | {located}/mysql8/bin/mysql -uroot'
            value=os.system(cluster_commands)
            if value==0:
                print(f"MySQL({role})配置完成")
            else:
                print(f"MySQL({role})配置失败:{value}")


if __name__ == "__main__":
    main()
