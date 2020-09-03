#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import psutil
from libs import common

def main():
    action, weight, soft_file, conf_json=sys.argv[1:5]
    conf_dict=json.loads(conf_json)
    soft_name="MySQL"
    mysql_port=3306
    log=common.Logger(None, "info", "remote")

    mysql_info=conf_dict.get("mysql_info")
    db_info=mysql_info.get("db_info")
    located=conf_dict.get("located")

    my_cnf_file=f"/etc/my.cnf"
    my_client_cnf_file="/etc/my_client.cnf"
    os_user="mysql"
    src="mysql-"
    dst="mysql"
    my_data="mydata"
    my_logs="mylogs"

    # 安装
    if action == "install":
        result=os.system(f"id -u {os_user} &> /dev/null || useradd -r -s /bin/false {os_user}")
        if result != 0:
            log.logger.error(f"创建{soft_name}用户失败")
            return
        value, msg=common.install(soft_file, src, dst, "pkg", located)
        if value==1:
            log.logger.info(f"{soft_name}安装完成")
        else:
            log.logger.error(f"{soft_name}安装失败: {msg}")
            return 

        # 配置
        mk_dirs_commands=f"mkdir -p {located}/{dst}/{{{my_data},{my_logs}}} && mkdir -p {located}/{dst}/{my_logs}/{{binlog,redolog,undolog,relay}} && chown -R {os_user}:{os_user} {located}/{src}* && ln -snf {located}/{src}* /usr/local/mysql && \cp -f {located}/{dst}/support-files/mysql.server /etc/init.d/mysqld && systemctl daemon-reload"
        result=os.system(mk_dirs_commands)
        if result==0:
            log.logger.info(f"{soft_name}相关目录建立完成")
            mem=psutil.virtual_memory()
            mem=int(mem[0] * float(weight) /1024/1024)
            server_id=db_info.get("server_id")

            mysql_sh_context=f"""\
                export MySQL_HOME={located}/{dst}
                export PATH=$MySQL_HOME/bin:$PATH
            """
            my_cnf_context=f"""\
                [mysqld]
                # dir
                datadir={located}/{dst}/{my_data}
                #secure_file_priv=/var/lib/mysql-files
                pid_file={located}/{dst}/{my_data}/mysqld.pid

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
                log_error={located}/{dst}/{my_logs}/mysqld.log
                log_timestamps=system
                ## Slow log
                log_output=file
                slow_query_log=1
                long_query_time=2

                # bin log
                server_id={server_id}
                log_bin={located}/{dst}/{my_logs}/binlog/binlog
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
                innodb_log_group_home_dir={located}/{dst}/{my_logs}/redolog
                innodb_log_file_size=256M
                innodb_log_files_in_group=4

                ## log buffer
                innodb_log_buffer_size=16M
                innodb_flush_log_at_trx_commit=1

                ## tablespace
                ### system tablespace
                innodb_file_per_table=1
                ### undo tablespace
                innodb_undo_directory={located}/{dst}/{my_logs}/undolog
                innodb_rollback_segments=128
                innodb_max_undo_log_size=1G

                !include {my_client_cnf_file}

                log_slave_updates=1
                [client]
            """
            config_dict={
                    "mysql_sh":{
                        "config_file": "/etc/profile.d/mysql.sh", 
                        "config_context": mysql_sh_context, 
                        "mode": "w"
                        }, 
                    "my_cnf":{
                        "config_file": my_cnf_file, 
                        "config_context": my_cnf_context,
                        "mode": "w"
                        }
                    }
            result, msg=common.config(config_dict)
            if result==1:
                log.logger.info(f"{soft_name}配置优化完成")
            else:
                log.logger.error(f"{soft_name}配置优化失败: {msg}")
        else:
            log.logger.error(f"{soft_name}相关目录建立失败: {result}")

    elif action=="start":
        cluster_flag=0
        cluster_info=mysql_info.get("cluster_info")
        if cluster_info is not None:
            cluster_flag=1
            role=cluster_info.get("role")
            if role == "master":
                sync_sql=f"create user 'repl'@'%' identified with mysql_native_password by 'DreamSoft_123456'; grant replication slave on *.* to 'repl'@'%';"
            elif role == "slave":
                my_client_cnf=f"""\
                    [mysqld]
                    #replication
                    ## master
                    ## slave
                    ### relay log
                    relay_log={located}/{dst}/{my_logs}/relay/relay
                    relay_log_info_repository=table
                """

                sync_dbs_list=cluster_info.get("sync_dbs")
                sync_dbs_config=""
                for sync_db in sync_dbs_list:
                    sync_dbs_config=f"{sync_dbs_config}\nreplicate_do_db={sync_db}"
                config_dict={
                        "my_client_cnf":{
                            "config_file": my_client_cnf_file, 
                            "config_context": my_client_cnf,
                            "mode": "w"
                            }, 
                        "my_sync_db_cnf":{
                            "config_file": my_client_cnf_file, 
                            "config_context": sync_dbs_config, 
                            "mode": "a"
                            }
                        }

                result, msg=common.config(config_dict)
                if result==1:
                    log.logger.info(f"{role}配置完成")
                else:
                    log.logger.error(f"{role}配置失败: {msg}")

                sync_host=cluster_info.get("sync_host")
                sync_sql=f"change master to master_host='{sync_host}', master_user='repl', master_password='DreamSoft_123456', master_auto_position=1; start slave;"

        log.logger.info(f"{soft_name}初始化中...")
        init_command=f"{located}/{dst}/bin/mysqld --initialize --user={os_user}"
        os.system(init_command)
        # 获取密码
        try:
            with open(f"{located}/{dst}/{my_logs}/mysqld.log", "r") as f:
                for i in f.readlines():
                    if "temporary password" in i:
                        log.logger.info(f"{soft_name}初始化成功")
                        pass_line=i.split(" ")
                        init_password=pass_line[-1].strip()
                        break
        except Exception as e:
            log.logger.error(f"{soft_name}初始化失败: {e}")
            return 1

        start_command=f"systemctl start mysqld"
        os.system(start_command)
        if common.port_exist(mysql_port, 20):
            log.logger.info(f"{soft_name}启动成功")
        else:
            log.logger.error(f"{soft_name}启动超时")

        # 更改初始密码
        root_password=db_info.get("root_password")
        change_pass_command=f"{located}/{dst}/bin/mysqladmin  -uroot -p'{init_password}' password {root_password} &> /dev/null"
        value=os.system(f"{change_pass_command}")
        if value==0:
            log.logger.info(f"{soft_name}更改初始密码完成")
        else:
            log.logger.error(f"{soft_name}更改初始密码失败:{value}")
            return 1
        
        # 创建自定义用户和数据库
        init_sql_list=[]
        for db_name, user_name, user_password in zip(db_info.get("business_db"), db_info.get("business_user"), db_info.get("business_password")):
            db_sql=f"create database if not exists {db_name};"
            use_sql=f"use {db_name};"
            user_sql=f"create user if not exists '{user_name}'@'%' identified by '{user_password}';"
            grant_sql=f"grant all on {db_name}.* to '{user_name}'@'%';"
            init_sql_list.append(db_sql)
            init_sql_list.append(use_sql)
            init_sql_list.append(user_sql)
            init_sql_list.append(grant_sql)
        init_sql=" ".join(init_sql_list)
        init_commands=f'export MYSQL_PWD="{root_password}" ; echo "{init_sql}" | {located}/{dst}/bin/mysql -uroot'
        value=os.system(init_commands)
        if value==0:
            log.logger.info(f"{soft_name}用户配置完成")
        else:
            log.logger.error(f"{soft_name}用户配置失败:{value}")

        # 集群
        if cluster_flag==1:
            cluster_commands=f'export MYSQL_PWD="{root_password}" ; echo "{sync_sql}" | {located}/{dst}/bin/mysql -uroot'
            value=os.system(cluster_commands)
            if value==0:
                log.logger.info(f"{role}同步完成")
            else:
                log.logger.error(f"{role}同步失败:{value}")


if __name__ == "__main__":
    """
        二进制安装, 需要libaio
        1.mysql-8.0.19-linux-glibc2.12-x86_64.tar.xz解压
        2.将liabio放入其中新建的pkg目录
        3.更改目录名为mysql8并重新压缩
    """
    main()
