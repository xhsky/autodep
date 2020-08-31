#!../ext/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import json
from libs.client import Client

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

def host_init(host_dict, conf_dict):
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
        print("本机生成密钥对\n")
    else:
        print("本机已存在密钥对\n")

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
            print(f"主机{i}环境初始化...")
            ip=host_dict[i].get("ip")
            port=host_dict[i].get("port")
            password=host_dict[i].get("root_password")

            host.free_pass_set(ip, port, password)
            print(f"免密码登录设置完成")
            
            # 传输Python
            remote_python3_file=f"/tmp/{local_python3_file.split('/')[-1]}"
            host.scp(ip, port, "root", local_python3_file, remote_python3_file)
            command=f"tar -xf {remote_python3_file} -C /opt/ && echo 0"
            status=host.exec(ip, port, command)
            flag=status[1].read().decode('utf8').strip()
            if flag!='0':
                print(f"Python3安装报错: status[2].read().decode('utf8')")
                exit()
            else:
                print(f"配置Python3环境完成")

            # 执行init.py
            host.scp(ip, port, "root", init_py, "/tmp/init.py")
            status=host.exec(ip, port, f"/opt/python3/bin/python3 /tmp/init.py {i} '{hosts_str}'")

            for line in status[1]:
                 if line is not None:
                     print(line.strip("\n"))
            for line in status[2]:
                 if line is not None:
                     print(line.strip("\n"))

            print("")

def host_msg(host_dict):
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

            #print(f"Error: {i}无法获取主机信息: {status[2].read().decode('utf8')}")
            print(f"{status[1].read().decode('utf8')}")

def main():
    init_file="./config/init.json"
    conf_file="./config/conf.json"
    with open(init_file, 'r') as init_f, open(conf_file, 'r') as conf_f:
        try:
            init_dict=json.load(init_f)
            try:
                conf_dict=json.load(conf_f)
            except json.decoder.JSONDecodeError:
                print(f"Error: 配置文件({conf_file})json格式不正确")
            else:
                print(f"检测配置文件中账号端口等信息, 请稍后")
                flag, connect_msg=connect_test(init_dict)
                if flag==0:
                    print(f"Error: 配置文件({init_file})有误, 请根据返回信息重新配置并初始化\n")
                    for i in connect_msg:
                        print(f"{i}:\t{connect_msg[i]}")
                    exit()
                print("主机初始化..")
                host_init(init_dict, conf_dict)
                print("初始化完成\n\n各主机信息如下:")
                host_msg(init_dict)
        except json.decoder.JSONDecodeError:
            print(f"Error: 配置文件({init_file})json格式不正确")
    
if __name__ == "__main__":
    main()
