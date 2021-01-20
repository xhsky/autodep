#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import psutil
import platform
import os, sys, json
import subprocess
from libs.common import Logger
from libs.env import log_remote_level

def format_size(byte):
    byte=float(byte)
    kb=byte/1024

    if kb >= 1024:
        mb=kb/1024
        if mb>=1024:
            gb=mb/1024 
            return f"{gb:.2f}G"
        else:
            return f"{mb:.2f}M"
    else:
        return f"{kb:.2f}k"

def main():
    try:
        log=Logger({"remote": log_remote_level}, logger_name="host")
        host_info_dict={}

        os_name, hostname, kernel_version=list(platform.uname())[0:3]
        try:
            result=subprocess.run(["lsb_release", "-sd"], capture_output=True, encoding="utf8")
            if result.returncode==0:
                os_name=result.stdout.split()
        except:
            redhat_file="/etc/redhat-release"
            if os.path.exists(redhat_file):
                with open(redhat_file, "r") as f:
                    os_name=f.read().strip()

        #host_info_dict["hostname"]=hostname
        host_info_dict["os_name"]=os_name
        host_info_dict["kernel_version"]=kernel_version

        # disk
        host_info_dict["disk"]={}
        all_disk=psutil.disk_partitions()
        for i in all_disk:
            mounted=i[1]
            size=psutil.disk_usage(mounted)
            total=size[0]
            used_percent=size[3]
            host_info_dict["disk"][mounted]=[format_size(total), used_percent]

        # cpu
        cpu_count=psutil.cpu_count()
        cpu_used_percent=psutil.cpu_percent(interval=2)
        host_info_dict["CPU"]=[cpu_count, cpu_used_percent]

        # mem
        mem=psutil.virtual_memory()
        mem_total, mem_used_percent=mem[0], mem[2]
        host_info_dict["Mem"]=[format_size(mem_total), mem_used_percent]

        # port
        host_info_dict["Port"]={}
        all_port=psutil.net_connections(kind='inet')
        for i in all_port:
            if len(i[3])!=0:
                pid=i[6]
                if pid is not None:
                    if i[5]!="ESTABLISHED":
                        process_name=psutil.Process(pid).name()
                        port=i[3][1]
                        host_info_dict["port"][port]=[pid, process_name]
        log.logger.info(json.dumps(host_info_dict))
        sys.exit(0)
    except Exception as e:
        log.logger.error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
