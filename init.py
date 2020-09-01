#!../ext/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import json, os
from libs.client import Client
from libs.common import Logger

def connect_test(host_dict):
    """ 判断主机配置信息是否正确
    """

    flag=1
    return_msg={}
    for i in host_dict:
        if i != "local_name":
            host=Client()
            ip=host_dict[i].get("ip")
            port=host_dict[i].get("port")
            password=host_dict[i].get("root_password")
            status, msg=host.password_conn(ip, port, password)
            if status!=0:
                flag=0
            return_msg[i]=msg

    return flag, return_msg

def host_init(log, host_dict, conf_dict):
    """主机环境初始化
        * 生成秘钥
        * 免密码登录
        * 设置hostname
        * 配置hosts
        * 关闭firewalld
        * 关闭selinux
        * 配置Python3环境
        * nproc nofile
    """

    host=Client()
    if host.gen_keys():
        log.logger.info("本机生成密钥对\n")
    else:
        log.logger.info("本机已存在密钥对\n")

    hosts={}
    init_py="./bin/init.py"
    hosts_str="\n"
    local_python3_file=conf_dict["location"].get("python3")

    # 获取所有hosts
    for i in host_dict:
        if i != "local_name":
            hosts_str=f"{hosts_str}{host_dict[i].get('ip')} {i}\n"
    # 初始化
    for i in host_dict:
        if i != "local_name":
            log.logger.info(f"主机{i}环境初始化...")
            ip=host_dict[i].get("ip")
            port=host_dict[i].get("port")
            password=host_dict[i].get("root_password")

            host.free_pass_set(ip, port, password)
            log.logger.info(f"免密码登录设置完成")
            
            # 传输Python
            remote_python3_file=f"/tmp/{local_python3_file.split('/')[-1]}"
            host.scp(ip, port, "root", local_python3_file, remote_python3_file)
            command=f"tar -xf {remote_python3_file} -C /opt/ && echo 0"
            status=host.exec(ip, port, command)
            flag=status[1].read().decode('utf8').strip()
            if flag!='0':
                log.logger.error(f"Python3安装报错: status[2].read().decode('utf8')")
                exit()
            else:
                log.logger.info(f"配置Python3环境完成")

            # 执行init.py
            host.scp(ip, port, "root", init_py, "/tmp/init.py")
            status=host.exec(ip, port, f"/opt/python3/bin/python3 /tmp/init.py {i} '{hosts_str}'")

            for line in status[1]:
                 if line is not None:
                     log.logger.info(line.strip("\n"))
            for line in status[2]:
                 if line is not None:
                     log.logger.error(line.strip("\n"))

            print("")

def host_msg(log, host_dict):
    """获取主机信息
    """
    host=Client()
    get_msg_py="./bin/host.py"
    for i in host_dict:
        if i != "local_name":
            ip=host_dict[i].get("ip")
            port=host_dict[i].get("port")

            remote_file=f"/tmp/{get_msg_py.split('/')[-1]}"
            host.scp(ip, port, "root", get_msg_py, remote_file)
            get_msg_command=f"/opt/python3/bin/python3 {remote_file}"
            status=host.exec(ip, port, get_msg_command)

            log.logger.info(f"{status[1].read().decode('utf8')}")

def main():
    conf_file="./config/conf.json"
    init_file="./config/init.json"
    with open(conf_file, 'r') as conf_f, open(init_file, 'r') as init_f:
        try:
            conf_dict=json.load(conf_f)
            # 配置log
            log_dir=conf_dict["log"]["log_dir"]
            log_file=f"{log_dir}/autodep.log"
            log_level=conf_dict["log"]["log_level"]
            os.makedirs(log_dir, exist_ok=1)
            log=Logger(log_file, log_level)
            try:
                init_dict=json.load(init_f)
            except json.decoder.JSONDecodeError:
                log.logger.error(f"配置文件({init_file})json格式不正确")
            else:
                log.logger.info(f"检测配置文件中账号端口等信息, 请稍后")
                flag, connect_msg=connect_test(init_dict)
                if flag==0:
                    log.logger.error(f"Error: 配置文件({init_file})有误, 请根据返回信息重新配置并初始化\n")
                    for i in connect_msg:
                        log.logger.info(f"{i}:\t{connect_msg[i]}")
                    exit()
                log.logger.info("主机初始化..")
                host_init(log, init_dict, conf_dict)
                log.logger.info("初始化完成\n\n各主机信息如下:")
                host_msg(log, init_dict)
        except json.decoder.JSONDecodeError:
            print(f"Error: 配置文件({conf_file})json格式不正确")
    
if __name__ == "__main__":
    main()
