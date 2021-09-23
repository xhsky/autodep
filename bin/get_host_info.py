#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import psutil, distro, platform
import os, sys, json
import ntplib, time
import subprocess
from libs.common import Logger, port_connect, exec_command
from libs.env import log_remote_level, interface, normal_code, error_code, support_os

def main():
    try:
        log=Logger({"remote": log_remote_level}, logger_name="host")
        host_info_dict={}

        os_name=f"{distro.id().lower()} {distro.version()}"
        os_support_flag="Supported"
        if os_name not in support_os:
            os_support_flag="Unsupported"
            log.logger.warning(f"当前系统({os_name})不在支持范围({support_os})内")

        os_name=f"{distro.name(pretty=False)} {distro.version(pretty=True, best=True)}"
        kernel_version=platform.platform()
        host_info_dict["os_name"]=f"{os_name}-({os_support_flag})"
        host_info_dict["kernel_version"]=kernel_version
        host_info_dict["cpu_arch"]=platform.machine()

        # 网卡信息
        nic=psutil.net_if_addrs()
        host_info_dict["adapter"]={}
        for adapter in nic:
            ipv4=None
            mac=None
            for snic in nic[adapter]:
                if snic.family.name == "AF_INET":
                    ipv4=snic.address
                elif snic.family.name in ["AF_LINK", "AF_PACKET"]:
                    mac=snic.address
            host_info_dict["adapter"][adapter]={ipv4: mac}

        # disk
        host_info_dict["Disk"]={}
        all_disk=psutil.disk_partitions()
        for i in all_disk:
            mounted=i[1]
            size=psutil.disk_usage(mounted)
            total=size[0]
            used_percent=size[3]
            host_info_dict["Disk"][mounted]=[total, used_percent]

        # cpu
        cpu_count=psutil.cpu_count()
        cpu_used_percent=psutil.cpu_percent(interval=2)
        host_info_dict["CPU"]=[cpu_count, cpu_used_percent]

        # mem
        mem=psutil.virtual_memory()
        mem_total, mem_used_percent=mem[0], mem[2]
        host_info_dict["Mem"]=[mem_total, mem_used_percent]

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
                        host_info_dict["Port"][port]=[pid, process_name]

        # 接口连通测试
        host_info_dict["Interface"]={}
        for interface_name in interface:
            if port_connect(interface[interface_name][0], interface[interface_name][1]):
                host_info_dict["Interface"][interface_name]=True
            else:
                host_info_dict["Interface"][interface_name]=False

        # 时间校准
        c=ntplib.NTPClient()
        check_time=True
        msg=""
        try:
            if time.tzname[time.daylight] != "CST":             # 校验时区
                set_time_zone="timedatectl set-timezone Asia/Shanghai"
                result, msg=exec_command(set_time_zone)
                if not result:
                    check_time=False
            time.tzset()    # 程序内重新获取时区信息
            # 校准时间
            response = c.request('ntp.ntsc.ac.cn', timeout=2)
            ts=response.tx_time
            date_=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
            set_time=f"date -s '{date_}' && hwclock -w"
            log.logger.info(f"{set_time}")
            result, msg=exec_command(set_time)
            if check_time:
                if not result:
                    check_time=False
            host_info_dict["NTP"]={
                    "result": check_time, 
                    "msg": msg
                    }
        except Exception as e:
            host_info_dict["NTP"]={
                    "result": False, 
                    "msg": str(e)
                    }

        log.logger.info(json.dumps(host_info_dict))
        sys.exit(normal_code)
    except Exception as e:
        log.logger.error(str(e))
        sys.exit(error_code)

if __name__ == "__main__":
    main()
