#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 13:55:46
# sky

import sys, os
import json, tarfile
from libs import remote
from libs.env import update_package_dir, test_mode, \
        remote_python_exec, remote_code_dir, program_unzip_dir

def db_update(package, update_dict, log):
    """
    数据库更新
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

def code_update(package, update_dict, log):
    """
    代码更新
    """

    log.logger.info("开始代码更新")
    args_dict={
            "type": update_dict["update_info"]["type"], 
            "dest": update_dict["update_info"]["dest"], 
            }
    ssh_client=remote.ssh()
    hosts_update_dict={}
    update_result=True
    try:
        for host_str in update_dict["update_info"]["hosts"]:
            state_value=True
            host_and_port=host_str.split(":")
            host=host_and_port[0]
            try:
                port=int(host_and_port[1])
            except IndexError:
                port=22

            log.logger.info(f"'{host}'更新")
            log.logger.info("传输更新包...")
            update_package_abs=f"{update_package_dir}/{package.split('/')[-1]}"

            update_py_file="update.py"
            trans_files=[
                    (package, update_package_abs), 
                    (f"./bin/{update_py_file}", f"{remote_code_dir}/{update_py_file}"), 
                    ]
            propertiesPath=update_dict["update_info"].get("propertiesPath")
            if propertiesPath:
                trans_files.append(
                        (f"{program_unzip_dir}/{propertiesPath}", f"{update_package_dir}/{propertiesPath}")
                        )
                args_dict["propertiesPath"]=f"{update_package_dir}/{propertiesPath}"

            if test_mode:
                trans_files.append(("./libs/common.py", f"{remote_code_dir}/common.py"))
                trans_files.append(("./libs/env.py", f"{remote_code_dir}/env.py"))
            for i in trans_files:
                log.logger.debug(f"{i[0]} --> {host}:{i[1]}")
                ssh_client.scp(host, port, "root", i[0], i[1])
            args_dict["tar_file"]=update_package_abs
            update_command=f"{remote_python_exec} {remote_code_dir}/{update_py_file} '{json.dumps(args_dict)}'"
            log.logger.debug(f"{update_command}")
            status=ssh_client.exec(host, port, update_command)
            for line in status[1]:
                log.logger.info(line.strip())
            if status[1].channel.recv_exit_status()==0:
                log.logger.info(f"{host}更新完成\n")
            else:
                update_result=False
                state_value=False
                log.logger.error(f"{host}更新失败\n")
            hosts_update_dict[host]=state_value
    except Exception as e:
        log.logger.error(f"更新失败: {str(e)}")
        update_result=False
    
    return update_result, hosts_update_dict

if __name__ == "__main__":
    main()
