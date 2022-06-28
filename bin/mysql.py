#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, json
from libs import common, tools
from libs.env import log_remote_level, mysql_user, mysql_src, mysql_dst, mysql_pkg_dir, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

def init(db_info_dict, mysql_dir, init_password, cluster_info_dict, role, log):
    root_password=db_info_dict.get("root_password")
    change_pass_command=f"{mysql_dir}/bin/mysqladmin  -uroot -p'{init_password}' password {root_password}"
    log.logger.debug(f"更改root密码: {change_pass_command=}")
    result, msg=common.exec_command(change_pass_command)
    if result:
        business_db_list=db_info_dict.get("business_db")
        if business_db_list is not None and len(business_db_list)!=0:
            log.logger.debug("创建账号及数据库")
            init_sql_list=[]
            for db_name, user_name, user_password in zip(db_info_dict.get("business_db"), db_info_dict.get("business_user"), db_info_dict.get("business_password")):
                db_sql=f"create database if not exists {db_name};"
                use_sql=f"use {db_name};"
                user_sql=f"create user if not exists '{user_name}'@'%' identified by '{user_password}';"
                grant_sql=f"grant all on {db_name}.* to '{user_name}'@'%';"
                init_sql_list.append(db_sql)
                init_sql_list.append(use_sql)
                init_sql_list.append(user_sql)
                init_sql_list.append(grant_sql)
            init_sql=" ".join(init_sql_list)
            init_commands=f'export MYSQL_PWD="{root_password}" ; echo "{init_sql}" | {mysql_dir}/bin/mysql -uroot'
            log.logger.debug(f"{init_commands=}")
            result, msg=common.exec_command(init_commands)
            if not result:
                log.logger.error(msg)
                return error_code
        if role != "stand-alone":
            log.logger.debug("开始主从配置")
            if role == "master":
                sync_sql=f"create user 'repl'@'%' identified with mysql_native_password by 'DreamSoft_123456'; grant replication slave on *.* to 'repl'@'%';"
            elif role == "slave":
                sync_host, sync_port=cluster_info_dict.get("sync_host").split(":")
                sync_sql=f"change master to master_host='{sync_host}', master_port={sync_port}, master_user='repl', master_password='DreamSoft_123456', master_auto_position=1; start slave;"
            cluster_commands=f'export MYSQL_PWD="{root_password}" ; echo "{sync_sql}" | {mysql_dir}/bin/mysql -uroot'
            log.logger.debug(f"{cluster_commands=}")
            result, msg=common.exec_command(cluster_commands)
            if result:
                return normal_code
            else:
                log.logger.error(msg)
                return error_code
    else:
        log.logger.error(msg)
        return error_code

def install():
    """安装
    """
    return_value=normal_code
    pkg_file=conf_dict["pkg_file"]
    command=f"id -u {mysql_user} > /dev/null 2>&1 || useradd -r -s /bin/false {mysql_user}"
    log.logger.debug(f"创建用户: {command=}")
    result, msg=common.exec_command(command)
    if not result:
        log.logger.error(msg)
        return_value=error_code

    value, msg=common.install(pkg_file, mysql_src, mysql_dst, mysql_pkg_dir, located)
    if not value:
        log.logger.error(msg)
        sys.exit(error_code)

    # 配置
    mk_dirs_commands=f"mkdir -p {mysql_dir}/{my_data} && mkdir -p {mysql_dir}/{my_logs}/binlog && mkdir -p {mysql_dir}/{my_logs} && mkdir -p {mysql_dir}/{my_logs}/redolog && mkdir -p {mysql_dir}/{my_logs}/undolog && mkdir -p {mysql_dir}/{my_logs}/relay && chown -R {mysql_user}:{mysql_user} {located}/{mysql_src}* && ln -snf {located}/{mysql_src}* /usr/local/mysql && \cp -f {mysql_dir}/support-files/mysql.server /etc/init.d/mysqld && systemctl daemon-reload && systemctl enable mysqld"
    log.logger.debug(f"建立目录, 授权: {mk_dirs_commands=}")
    result, msg=common.exec_command(mk_dirs_commands)
    if not result:
        log.logger.error(msg)
        return error_code

    mem=db_info_dict.get("innodb_mem")
    server_id=db_info_dict.get("server_id")
    max_connections=db_info_dict.get("max_connections")

    mysql_sh_context=f"""\
        export MySQL_HOME={mysql_dir}
        export PATH=$MySQL_HOME/bin:$PATH
    """
    my_cnf_context=tools.render("config/templates/mysql/my.cnf.tem", db_info_dict=db_info_dict, mysql_dir=mysql_dir)
    my_cnf_file=f"/etc/my.cnf"

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

    # slave配置
    if cluster_flag:
        if role=="slave":
            my_client_cnf=f"""\
                [mysqld]
                #replication
                ## master
                ## slave
                ### relay log
                relay_log={mysql_dir}/{my_logs}/relay/relay
            """
            sync_dbs_list=cluster_info_dict.get("sync_dbs")
            sync_dbs_config=""
            for sync_db in sync_dbs_list:
                sync_dbs_config=f"{sync_dbs_config}\nreplicate_do_db={sync_db}"
            config_dict.update(
                    {
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
                    )
    else:
        config_dict.update(
                {
                    "my_client_cnf": {
                        "config_file": my_client_cnf_file,
                        "config_context": "",
                        "mode": "w"
                        }
                    }
                )
    log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
    result, msg=common.config(config_dict)
    if not result:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def run():
    """运行
    """
    return_value=normal_code
    #init_command=f"{mysql_dir}/bin/mysqld --initialize --user={mysql_user} --datadir={mysql_dir}/{my_data}"
    init_command=f"{mysql_dir}/bin/mysqld --initialize --user={mysql_user}"
    log.logger.debug(f"初始化中: {init_command=}")
    result, msg=common.exec_command(init_command, timeout=600)
    if result:
        try:
            log.logger.debug("获取随机密码")
            with open(f"{mysql_dir}/{my_logs}/mysqld.log", "r") as f:
                for i in f.readlines():
                    if "temporary password" in i:
                        pass_line=i.split(" ")
                        init_password=pass_line[-1].strip()
                        log.logger.debug(f"{init_password=}")
                        break
                else:
                    log.logger.error(f"初始化失败, 请查看MySQL日志")
        except Exception as e:
            log.logger.error(str(e))
            return error_code

        mysql_plugin_context="""\
                [mysqld]
                # plugin
                plugin-load-add=connection_control.so
                connection_control_failed_connections_threshold=10
                connection_control_min_connection_delay=1000
                """
        config_dict={
                "my_plugin_cnf":{
                    "config_file": my_plugin_cnf_file, 
                    "config_context": mysql_plugin_context, 
                    "mode":"w"
                    }
                }
        log.logger.debug(f"写入配置文件: {json.dumps(config_dict)}")
        result, msg=common.config(config_dict)
        if result:
            start_command=f"systemctl start mysqld"
            log.logger.debug(f"{start_command=}")
            result, msg=common.exec_command(start_command, timeout=600)
            if result:
                log.logger.debug(f"检测端口: {port_list=}")
                if common.port_exist(port_list):
                    return_value=init(db_info_dict, mysql_dir, init_password, cluster_info_dict, role, log)
                else:
                    return_value=error_code
            else:
                log.logger.error(msg)
                return_value=error_code
        else:
            log.logger.error(msg)
            return_value=error_code
    else:
        log.logger.error(msg)
        return_value=error_code
    return return_value

def start():
    """启动
    """
    start_command=f"systemctl start mysqld"
    log.logger.debug(f"{start_command=}")
    result, msg=common.exec_command(start_command, timeout=600)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list):
            return error_code
    else:
        log.logger.error(msg)
        return error_code
    return normal_code

def stop():
    """停止
    """
    stop_command=f"systemctl stop mysqld"
    log.logger.debug(f"{stop_command=}")
    result, msg=common.exec_command(stop_command, timeout=600)
    if result:
        log.logger.debug(f"检测端口: {port_list=}")
        if not common.port_exist(port_list, exist_or_not=False):
            return error_code
    else:
        log.logger.error(msg)
        return error_code
    return normal_code

def monitor():
    """监控
    return:
        启动, 未启动, 启动但不正常
    """
    return common.soft_monitor("localhost", port_list)

if __name__ == "__main__":
    """
        二进制安装, 需要libaio
        1.mysql-8.0.19-linux-glibc2.12-x86_64.tar.xz解压
        2.将liabio放入其中新建的pkg目录
        3.更改目录名为mysql-<version>并重新压缩
    """
    softname, action, conf_json=sys.argv[1:]
    conf_dict=json.loads(conf_json)
    located=conf_dict.get("located")
    mysql_dir=f"{located}/{mysql_dst}"

    log=common.Logger({"remote": log_remote_level}, loggger_name="mysql")
    mysql_info_dict=conf_dict.get("mysql_info")
    db_info_dict=mysql_info_dict.get("db_info")
    mysql_port=db_info_dict.get("mysql_port")
    my_logs="mylogs"
    my_data="mydata"
    port_list=[
            mysql_port
            ]

    cluster_info_dict=mysql_info_dict.get("cluster_info")
    my_client_cnf_file="/etc/my_client.cnf"
    my_plugin_cnf_file="/etc/my_plugin.cnf"
    if cluster_info_dict is None:
        cluster_flag=0
        role="stand-alone"
    else:
        cluster_flag=1
        role=cluster_info_dict.get("role")

    if action=="install":
        sys.exit(install())
    elif action=="run":
        sys.exit(run())
    elif action=="start":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(activated_code)
        elif status_value==stopped_code:
            sys.exit(start())
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(start())
            else:
                sys.exit(error_code)
    elif action=="stop":
        status_value=monitor()
        if status_value==activated_code:
            sys.exit(stop())
        elif status_value==stopped_code:
            sys.exit(stopped_code)
        elif status_value==abnormal_code:
            if stop()==normal_code:
                sys.exit(normal_code)
            else:
                sys.exit(error_code)
    elif action=="monitor":
        sys.exit(monitor())
    else:
        sys.exit(error_code)
