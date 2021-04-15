#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 13:55:46
# sky

import sys, os
import json, tarfile
from libs import remote
from libs.env import update_package_dir, test_mode, \
        remote_python_exec, remote_code_dir, rollback_dir

'''
def db_update(package, update_dict, log):
    """数据库更新
    return:

    """
    log.logger.info("开始数据库更新")

    update_result=True
    hosts_update_dict={}
    host_and_port=update_dict["update_info"]["host"].split(":")
    host=host_and_port[0]
    try:
        type_=update_dict["update_info"]["type"]
        user=update_dict["update_info"]["user"]
        password=update_dict["update_info"]["password"]
        db_name=update_dict["update_info"]["db"]
        if type_.lower()=="mysql":
            try:
                port=int(host_and_port[1])
            except IndexError:
                port=3306
            log.logger.info(f"解压数据文件")
            log.logger.debug(f"{package} --> {update_package_dir}")
            with tarfile.open(package, "r", encoding="utf8") as tar:
                for i in tar.getnames():
                    if i.endswith("sql"):
                        sql_file=i
                        break
                tar.extractall(update_package_dir)
                sql_file_abs=f"{update_package_dir}/{sql_file}"

            db=remote.DB(type_, host, port, user, password, db_name)

            sql_list=[]
            log.logger.debug(f"读取数据文件{sql_file_abs}")
            with open(sql_file_abs, "rb") as f:
                log.logger.info("数据更新中, 时间可能较长, 请稍后...")
                for line in f:
                    line=line.decode("utf8", "ignore").strip()
                    if line=="" or line.startswith("--"):
                        continue
                    if line[-1]==";":
                        if len(sql_list)==0:
                            sql_statement=line
                        else:
                            sql_list.append(line)
                            sql_statement=" ".join(sql_list)
                    else:
                        sql_list.append(line)
                        continue

                    #log.logger.debug(sql_statement)
                    db.exec(sql_statement)
                    sql_list=[]
                else:
                    db.commit()
                    log.logger.info(f"'{host}'更新完成\n")
    except Exception as e:
        log.logger.error(f"更新失败: {str(e)}")
        update_result=False

    hosts_update_dict[host]=update_result
    return update_result, hosts_update_dict
'''

def update(mode, package, program_dir, args_dict, delete_flag, init_dict, arch_dict, log):
    """项目更新
    mode: code|db
    package: /path/file_name
    args_dict: update_dict["update_info"]

    update_result: True|False
    hosts_update_dict: {
        node: True
        }

    """
    ssh_client=remote.ssh()
    update_package_abs=f"{update_package_dir}/{package.split('/')[-1]}"
    update_py_file="update.py"
    trans_files=[
            (package, update_package_abs), 
            (f"./bin/{update_py_file}", f"{remote_code_dir}/{update_py_file}"), 
            ]
    args_dict["pkg_file"]=update_package_abs
    args_dict["delete_flag"]=delete_flag
    update_result=True
    hosts_update_dict={}
    if mode=="code":
        propertiesPath=args_dict.get("propertiesPath")
        if propertiesPath:
            trans_files.append(
                    (f"{program_dir}/{propertiesPath}", f"{update_package_dir}/{propertiesPath}")
                    )
            args_dict["propertiesPath"]=f"{update_package_dir}/{propertiesPath}"
        for node in args_dict["hosts"]:
            state_value=True
            port=init_dict[arch_dict[node]["ip"]]["port"]
            log.logger.info(f"{node}: 传输项目包...")
            for i in trans_files:
                log.logger.debug(f"{i[0]} --> {node}:{i[1]}")
                ssh_client.scp(node, port, "root", i[0], i[1])
            update_command=f"{remote_python_exec} {remote_code_dir}/{update_py_file} {mode}_update '{json.dumps(args_dict)}'"
            log.logger.debug(f"{update_command}")
            status=ssh_client.exec(node, port, update_command)
            for line in status[1]:
                log.logger.info(line.strip())
            if status[1].channel.recv_exit_status()==0:
                log.logger.info(f"{node}: 完成")
            else:
                update_result=False
                state_value=False
                log.logger.error(f"{node}失败")
            hosts_update_dict[node]=state_value
    elif mode=="db":
        state_value=True
        node=args_dict["host"]
        port=init_dict[arch_dict[node]["ip"]]["port"]
        log.logger.info(f"{node}: 传输数据包...")
        for i in trans_files:
            log.logger.debug(f"{i[0]} --> {node}:{i[1]}")
            ssh_client.scp(node, port, "root", i[0], i[1])
        update_command=f"{remote_python_exec} {remote_code_dir}/{update_py_file} {mode}_update '{json.dumps(args_dict)}'"
        log.logger.debug(f"{update_command}")
        status=ssh_client.exec(node, port, update_command)
        for line in status[1]:
            log.logger.info(line.strip())
        if status[1].channel.recv_exit_status()==0:
            log.logger.info(f"{node}: 完成")
        else:
            update_result=False
            state_value=False
            log.logger.error(f"{node}: 失败")
        hosts_update_dict[node]=state_value
    return update_result, hosts_update_dict

def backup(node, port, backup_name, backup_type, backup_dict, backup_version, log):
    """项目备份
    """
    ssh_client=remote.ssh()
    backup_result=True
    backup_dict["back_name"]=backup_name
    try:
        backup_py_file="update.py"
        trans_files=[
                (f"./bin/{update_py_file}", f"{remote_code_dir}/{update_py_file}"), 
                ]
        if test_mode:
            trans_files.append(("./libs/common.py", f"{remote_code_dir}/common.py"))
            trans_files.append(("./libs/env.py", f"{remote_code_dir}/env.py"))
        for i in trans_files:
            log.logger.debug(f"{i[0]} --> {node}:{i[1]}")
            ssh_client.scp(node, port, "root", i[0], i[1])
        backup_command=f"{remote_python_exec} {remote_code_dir}/{backup_py_file} {backup_type}_backup '{json.dumps(backup_dict)}'"
        log.logger.debug(f"{backup_command=}")
        status=ssh_client.exec(node, port, backup_command)
        for line in status[1]:
            log.logger.info(line.strip())
        if status[1].channel.recv_exit_status()==0:
            backup_file=f"{rollback_dir}/{backup_name}"
            rollback_file=f"{rollback_dir}/{backup_version}/{backup_name}"
            log.logger.info(f"{node}: {backup_file} --> {rollback_file}")
            result=ssh_client.get(node, port, "root", backup_file, rollback_file)
            if result:
                if backup_dict.get("propertiesPath"):
                    backup_config_file=f"{rollback_dir}/{backup_dict.get('propertiesPath')}"
                    rollback_config_file=f"{rollback_dir}/{backup_version}/{backup_dict.get('propertiesPath')}"
                    log.logger.info(f"{node}: {backup_config_file} --> {rollback_config_file}")
                    ssh_client.get(node, port, "root", backup_config_file, rollback_config_file)
                log.logger.info(f"{backup_name}备份完成\n")
            else:
                log.logger.error("{backup_name}备份失败, {result}\n")
                backup_result=False
        else:
            backup_result=False
            log.logger.error(f"{backup_name}备份失败\n")
    except Exception as e:
        log.logger.error(f"{backup_name}备份失败: {str(e)}")
        backup_result=False
    return backup_result

if __name__ == "__main__":
    main()
