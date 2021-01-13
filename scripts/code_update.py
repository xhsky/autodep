#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 13:55:46
# sky

import sys, os
workdir=os.path.dirname(sys.path[0])
sys.path[0]=workdir
os.chdir(workdir)

import json
import argparse
from libs import common, remote
from libs.env import log_update_level, log_update_file, \
        log_console_level, log_platform_level, \
        remote_pkgs_dir, remote_code_dir, \
        update_status_file, remote_python_exec, \
        test_mode

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["console", "platform"], help="更新方式")
    parser.add_argument("--id", type=str, help="项目id")
    #parser.add_argument("--log_level", type=str, choices=["gz", "jar"], help="更新类型. gz|jar")
    parser.add_argument("--package", type=str, help="更新包. 压缩格式为tar.gz且必须为绝对路径")
    parser.add_argument("--host", type=str, help="更新主机. <host1>:<port>,<host2>:<port>")
    parser.add_argument("--dest", type=str, help="更新地址. /path")
    parser.add_argument("--version", type=str, help="版本")
    args=parser.parse_args()

    project_id=args.id
    version=args.version

    mode_level_dict={
            "file": log_update_level
            }
    if args.mode.lower()=="console":
        mode_level_dict["console"]=log_console_level
        update_status_file_flag=True
    if args.mode.lower()=="platform":
        mode_level_dict["platform"]=log_platform_level
        update_status_file_flag=False
    #print(f"{mode_level_dict}")
    log=common.Logger(mode_level_dict, log_file=log_update_file, project_id=project_id) 

    try:
        package=args.package.strip()
        if not package.startswith("/"):
            log.logger.error("更新包必须为绝对路径")
            sys.exit(1)

        package_all_name=package.split("/")[-1]
        #package_name, package_version=package_all_name[:-7].split("-")
        dest=args.dest
        host_list=[]
        for host_str in args.host.split(","):
            host_port=host_str.split(":")
            host=host_port[0]
            try:
                port=int(host_port[1])
            except IndexError:
                port=22
            host_list.append((host, port))
    except Exception as e:
        log.logger.error(f"参数解析错误. {str(e)}")
        sys.exit(1)

    update_status_dict={
            "project_id": project_id, 
            "mode": "code_update", 
            "version": version, 
            "status":{}
            }
    for node in host_list:
        host=node[0]
        port=node[1]
        
        log.logger.info(f"'{host}'主机更新:") 
        log.logger.info(f"传输更新包...")
        ssh=remote.ssh()
        remote_update_package=f"{remote_pkgs_dir}/{package_all_name}"
        update_py_file="update.py"
        remote_update_py=f"{remote_code_dir}/{update_py_file}"
        try:
            ssh.scp(host, port, "root", package, remote_update_package)
            ssh.scp(host, port, "root", f"./bin/{update_py_file}", remote_update_py)
            if test_mode:
                ssh.scp(host, port, "root", f"./libs/common.py", f"{remote_code_dir}/libs/common.py")
                ssh.scp(host, port, "root", f"./libs/env.py", f"{remote_code_dir}/libs/env.py")
        except Exception as e:
            log.logger.error(f"主机'{host}:{port}'连接有误: {str(e)}")
            sys.exit(1)

        args_dict={
                "tar_file": remote_update_package, 
                "dest_dir": dest, 
                "version": version
                }

        update_command=f"{remote_python_exec} {remote_code_dir}/{update_py_file} '{json.dumps(args_dict)}'"
        log.logger.debug(f"{update_command}")
        status=ssh.exec(host, port, update_command)
        for line in status[1]:
            log.logger.info(line.strip())
        if status[1].channel.recv_exit_status() == 0:
            log.logger.info(f"{host}更新完成\n")
            flag=True
        else:
            log.logger.error(f"{host}更新失败\n")
            flag=False
        update_status_dict["status"][host]=flag

    if update_status_file_flag:
        with open(update_status_file, "w", encoding="utf8") as f:
            json.dump(update_status_dict, f)
            log.logger.info(f"更新信息已写入'{update_status_file}'文件")
    else:
        result, message=common.post_platform(update_status_dict)
        if result:
            log.logger.info("更新信息已发送平台")
        else:
            log.logger.error(f"更新信息发送失败: {message}")

if __name__ == "__main__":
    main()
