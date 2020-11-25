#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 17:37:47
# sky

import locale, json, os, time, sys
from dialog import Dialog
from textwrap import dedent
from libs.common import Logger
from libs.client import Client
from libs.install import soft
#from threading import Thread

from libs.env import logs_dir, log_file, log_file_level, log_console_level, \
        remote_python_transfer_dir, remote_python_install_dir,  remote_python_exec, \
        remote_code_dir, remote_pkgs_dir, \
        interface

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir, exist_ok=1)

"""
class MyThread(Thread):
    def __init__(self,func,args=()):
        super(MyThread,self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception:
            return None
"""

class Deploy(object):
    '''集群部署
    '''
    def __init__(self, conf_file, init_file, arch_file, project_file):
        with open(conf_file, "r", encoding="utf8") as conf_f:
            self.conf_dict=json.load(conf_f)
            self.soft=self.conf_dict["software"].keys()

        self.init_file=init_file
        self.arch_file=arch_file
        self.project_file=project_file
        self.ssh=Client()

    def connect_test(self, init_dict):
        connect_msg={}
        flag=0
        for node in init_dict:
            ip=init_dict[node].get("ip")
            port=init_dict[node].get("port")
            password=init_dict[node].get("root_password")
            status, msg=self.ssh.password_conn(ip, port, password)
            if status != 0:
                flag=1
            connect_msg[node]={
                    "status": status, 
                    "msg": msg
                    }
        return flag, connect_msg

    def get_host_msg(self, init_dict):
        """获取主机信息
        """
        all_host_info={}
        get_msg_py="./bin/host.py"
        for i in init_dict:
            ip=init_dict[i].get("ip")
            port=init_dict[i].get("port")

            remote_file=f"{remote_code_dir}/{get_msg_py.split('/')[-1]}"
            self.ssh.scp(ip, port, "root", get_msg_py, remote_file)
            get_msg_command=f"{remote_python_exec} {remote_file}"
            self.log.logger.debug(f"获取{i}主机信息: {get_msg_command=}")
            status=self.ssh.exec(ip, port, get_msg_command)

            stdout_msg=status[1].read().strip().decode("utf8")
            stderr_msg=status[2].read().strip().decode("utf8")
            state_value=status[1].channel.recv_exit_status()
            if  state_value != 0:
                msg=stdout_msg
            else:
                msg=stderr_msg
            all_host_info[i]=[state_value, msg]
        return all_host_info

    def json_ana(init_dict, conf_dict, arch_dict):
        init_host_list=init_dict.keys()

        # arch.json中是否存在未初始化主机
        not_init_host_list=[]
        for i in arch_dict:
            if i not in init_host_list:
                not_init_host_list.append(i)
        if not_init_host_list != []:
            print(f"Error: 未初始化主机列表: {not_init_host_list}")
            exit()

        # 判断主机属性 attr
        attr={"software": list, "located": str}
        for i in arch_dict:
            for j in attr:
                if arch_dict[i].get(j) is None or not isinstance(arch_dict[i].get(j), attr[j]):
                    print(f"Error: '{i}.{j}'配置错误")
                    exit()
        soft_list=conf_dict.get("software").keys()
        check(arch_dict, soft_list, init_host_list)

    def init(self, init_dict, local_python3_file, mode_log):
        """主机环境初始化
            * 生成秘钥
            * 免密码登录
            * 设置hostname
            * 配置hosts
            * 关闭firewalld
            * 关闭selinux
            * 配置Python3环境
            * nproc nofile
            * 接口连通性测试
        """

        try:
            if self.ssh.gen_keys():
                mode_log.logger.info("本机生成密钥对\n")
            else:
                mode_log.logger.info("本机已存在密钥对\n")

            # 获取所有hosts
            hosts_list=[]
            for i in init_dict:
                hosts_list.append(f"{init_dict[i].get('ip')} {i}")
            # 初始化
            for i in init_dict:
                mode_log.logger.info(f"主机{i}环境初始化...")
                ip=init_dict[i].get("ip")
                port=init_dict[i].get("port")
                password=init_dict[i].get("root_password")

                self.ssh.free_pass_set(ip, port, password)
                mode_log.logger.info(f"免密码登录设置完成")
                
                # 传输Python
                remote_python3_file=f"{remote_python_transfer_dir}/{local_python3_file.split('/')[-1]}"
                mode_log.logger.debug(f"传输Python安装包...")
                self.ssh.scp(ip, port, "root", local_python3_file, remote_python3_file)
                command=f"tar -xf {remote_python3_file} -C {remote_python_install_dir}"
                mode_log.logger.debug(f"配置Python环境...")
                mode_log.logger.debug(f"{command=}")
                status=self.ssh.exec(ip, port, command)
                if status[1].channel.recv_exit_status() != 0:
                    mode_log.logger.error(f"Python3安装报错, 进程退出: {status[2].read().decode('utf8')}")
                    sys.exit()
                else:
                    mode_log.logger.info(f"配置Python3环境完成")

                # 执行init.py
                init_py="./bin/init.py"
                self.ssh.scp(ip, port, "root", "./libs/common.py", f"{remote_code_dir}/libs/common.py")
                self.ssh.scp(ip, port, "root", "./libs/env.py", f"{remote_code_dir}/libs/env.py")
                self.ssh.scp(ip, port, "root", init_py, f"{remote_code_dir}/init.py")
                host_str="\n".join(hosts_list)
                init_args={
                        "hostname": i, 
                        "hosts": host_str, 
                        "interface": interface, 
                        }
                command=f"{remote_python_exec} {remote_code_dir}/init.py '{json.dumps(init_args)}'"
                self.log.logger.debug(f"{i}远程初始化...")
                self.log.logger.debug(f"{command=}")
                status=self.ssh.exec(ip, port, command)

                for line in status[1]:
                     mode_log.logger.info(line.strip())
                for line in status[2]:
                     mode_log.logger.error(line.strip())
                if status[1].channel.recv_exit_status() != 0:
                    self.log.logger.error(f"{i}远程初始化失败")

                self.log.logger.info("")
            return "1"
        except Exception as e:
            return e

    '''
    def get_weight(self, soft_weight_dict, soft_install_list):
        """ 返回各软件占服务器的权重

            soft_install_dict={
                "soft_name": weight, 
                "soft_name": weight, 
            }
        """
        soft_install_dict={}
        for i in soft_install_list:
            soft_install_dict[i]=soft_weight_dict[i]
        weight_sum=sum(soft_install_dict.values())+1		# 1为系统权重
        
        for i in soft_install_dict:
            soft_install_dict[i]=round(soft_install_dict[i]/weight_sum, 2)
        return soft_install_dict
    '''

    def control(self, init_dict, arch_dict, action, log):
        flag=True
        for node in arch_dict:
            log.logger.info(f"*****{node}节点*****")
            ssh_port=init_dict[node].get("port")
            Install=soft(node, ssh_port)

            for softname in arch_dict[node]["software"]:
                log.logger.info(f"{softname}{action[0]}...")

                # 去除located结尾的/
                located_dir=arch_dict[node]["located"]
                if located_dir.endswith("/"):
                    arch_dict[node]["located"]=located_dir[0:-1]

                pkg_file=self.conf_dict["location"].get(softname)
                trans_files_dict={
                        "lib_file": ["./libs/common.py", f"{remote_code_dir}/libs/common.py"], 
                        "env_file": ["./libs/env.py", f"{remote_code_dir}/libs/env.py"], 
                        "py_file": [f"./bin/{softname}.py", f"{remote_code_dir}/{softname}.py"], 
                        "pkg_file": [pkg_file, f"{remote_pkgs_dir}/{pkg_file.split('/')[-1]}"]
                        }
                args_dict=arch_dict.get(node)

                if action[1]=="install":
                    status=Install.install(trans_files_dict, args_dict)
                elif action[1]=="start":
                    status=Install.start(trans_files_dict["py_file"][1], args_dict)

                for line in status[1]:
                    log.logger.info(line.strip())
                if status[1].channel.recv_exit_status() != 0:
                    log.logger.error(f"{softname}{action[0]}失败")
                    flag=False
                else:
                    log.logger.info(f"{softname}{action[0]}完成")
        return flag

    def install(self, init_dict, arch_dict, log):
        action=("安装", "install")
        result=self.control(init_dict, arch_dict, action, log)
        return result

    def start(self, init_dict, arch_dict, log):
        action=("启动", "start")
        result=self.control(init_dict, arch_dict, action, log)
        return result

class text_deploy(Deploy):
    '''文本安装'''

    def __init__(self, conf_file, init_file, arch_file, project_file):
        super(text_deploy, self).__init__(conf_file, init_file, arch_file, project_file)
        self.log=Logger({"file": log_file_level, "console": log_console_level}, log_file=log_file)

    def check(self):
        '''
            校验配置文件
        '''
        return True, msg

    def init(self):
        with open(self.init_file, "r", encoding="utf8") as f:
            init_dict=json.load(f)

        self.log.logger.info("监测主机配置, 请稍后...\n")
        flag, connect_msg=self.connect_test(init_dict)
        if flag==1:
            self.log.logger.error("主机信息配置有误, 请根据下方显示信息修改:")
            for node in connect_msg:
                self.log.logger.info(f"{node}:\t{connect_msg[node]['msg']}")
            sys.exit()

        local_python3_file=self.conf_dict["location"].get("python3")
        status=super(text_deploy, self).init(init_dict, local_python3_file, self.log)
        if status=="1":
            self.log.logger.info("初始化结束\n")
            self.log.logger.info("各主机信息如下:")
            all_host_info=self.get_host_msg(init_dict)
            for node in all_host_info:
                if all_host_info[node][0] == 0:
                    self.log.logger.debug(all_host_info[node][1])
                    node_info_dict=json.loads(all_host_info[node][1][6:])
                    node_info=dedent(f"""
                    主机名: {node}
                    发行版本: \t{node_info_dict['os_name']}
                    内核版本: \t{node_info_dict['kernel_version']}
                    CPU:      \t{node_info_dict['CPU'][0]}({node_info_dict['CPU'][1]}%)
                    内存:     \t{node_info_dict['Mem'][0]}({node_info_dict['Mem'][1]}%)""")
                    for disk in node_info_dict["disk"]:
                        node_info=f"{node_info}\n磁盘({disk}): \t{node_info_dict['disk'][disk][0]}({node_info_dict['disk'][disk][1]}%)"
                    for port in node_info_dict["port"]:
                        node_info=f"{node_info}\n端口({port}): \t{node_info_dict['port'][port][1]}/{node_info_dict['port'][port][0]}"
                    self.log.logger.info(node_info)
                else:
                    self.log.logger.error(all_host_info[node][1])
        else:
            self.log.logger.error(f"初始化失败: {status}")

    def install(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群安装...\n")
        result=super(text_deploy, self).install(init_dict, arch_dict, self.log)
        if result:
            self.log.logger.info("集群安装完成")
        else:
            self.log.logger.error("集群安装失败")

    def start(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群启动...\n")
        result=super(text_deploy, self).start(init_dict, arch_dict, self.log)
        if result:
            self.log.logger.info("集群启动完成")
        else:
            self.log.logger.error("集群启动失败")

class graphics_deploy(Deploy):
    '''文本图形化安装'''

    def __init__(self, conf_file, init_file, arch_file, project_file):
        super(graphics_deploy, self).__init__(conf_file, init_file, arch_file, project_file)
        self.log=Logger(self.log_file, self.log_level, "file")

        #self.g_log=Logger(log_file, log_level, "file")
        locale.setlocale(locale.LC_ALL, '')
        self.d = Dialog(dialog="dialog", autowidgetsize=1)
        self.d.set_background_title("集群部署")

    def trans_fields_to_dict(self, fields):
        info_dict={}
        for index, item in enumerate(fields):
            if index % 4 == 0:
                info_dict[item]={
                        "ip": fields[index+1], 
                        "root_password": fields[index+2], 
                        "port": fields[index+3]
                        }
        return info_dict

    def show_host_msg(self, title, host_info_dict):
        if host_info_dict=={}:
            elements=[
                    ("IP:", 1, 1, "192.168.0.1", 1, 15, 16, 16), 
                    ("root用户密码:", 2, 1, "password", 2, 15, 16, 16), 
                    ("ssh端口:", 3, 1, "22", 3, 15, 16, 16), 
                    ("设置主机名:", 4, 1, "node", 4, 15, 16, 16), 
                    ]
            code, fields=self.d.form(f"请填写集群中主机信息\n第1台主机:", elements=elements, title=title, extra_button=True, extra_label="继续添加", ok_label="添加完毕", cancel_label="上一步")
            # 交换IP和主机名顺序
            nodename=fields[-1] ; del fields[-1]
            fields.insert(0, nodename)
        else:
            elements=[]
            n=0
            for i in host_info_dict:
                n=n+1
                elements.append((f"{n:2}. 主机名: ", n, 1, i, n, 13, 10, 10))
                elements.append(("IP: ", n, 25, host_info_dict[i]["ip"], n, 29, 16, 16))
                elements.append(("root用户密码: ", n, 47, host_info_dict[i]["root_password"], n, 61, 15, 15))
                elements.append(("ssh端口: ", n, 78, str(host_info_dict[i]["port"]), n, 87, 5, 6))
            code, fields=self.d.form(f"填写主机信息:", elements=elements, title=title, extra_button=True, extra_label="继续添加", ok_label="添加完毕", cancel_label="上一步")
        self.log.logger.debug(f"主机信息: {code=}, {fields=}")
        return code, fields

    def add_soft_elements(self, softname, elements, tab, xi, field_length, READ_ONLY, n, soft_dict):
        item=""
        if softname=="nginx":
            soft_elements=[
                    (f"{softname}代理主机: ", n+1, 2*tab, ",".join(soft_dict["nginx_info"]["proxy_hosts"]), n+1, xi, field_length, 0, READ_ONLY)
                    ]
        elif softname=="jdk" or softname=="tomcat" or softname=="ffmpeg":
            soft_elements=[]
            item="无"
        elif softname=="glusterfs":
            soft_elements=[]
            server_elements=[]
            client_elements=[]
            show_client_info=0
            if soft_dict["glusterfs_info"].get("server_info") is not None:
                show_client_info=1
                server_elements=[
                        ("服务端配置: ", n+1, 2*tab, "", n+1, xi, field_length, 0, READ_ONLY), 
                        ("集群成员: ", n+2, 3*tab, ",".join(soft_dict["glusterfs_info"]["server_info"].get("members")), n+2, xi, field_length, 0, READ_ONLY), 
                        ("服务端卷目录: ", n+3, 3*tab, soft_dict["glusterfs_info"]["server_info"].get("volume_dir"), n+3, xi, field_length, 0, READ_ONLY)
                        ]
            if soft_dict["glusterfs_info"].get("client_info") is not None:
                if show_client_info==1:
                    n=n+len(server_elements)
                client_elements=[
                        ("客户端配置: ", n+1, 2*tab, "", n, xi, field_length, 0, READ_ONLY),
                        ("挂载源主机: ", n+2, 3*tab, soft_dict["glusterfs_info"]["client_info"].get("mounted_host"), n+2, xi, field_length, 0, READ_ONLY),
                        ("本机挂载目录: ", n+3, 3*tab, soft_dict["glusterfs_info"]["client_info"].get("mounted_dir"), n+3, xi, field_length, 0, READ_ONLY)
                        ]
                if show_client_info==1:
                    n=n-len(server_elements)
            soft_elements.extend(server_elements)
            soft_elements.extend(client_elements)
        elif softname=="mysql":
            soft_elements=[
                    ("管理员密码: ", n+1, 2*tab, soft_dict["mysql_info"]["db_info"].get("root_password"), n+1, xi, field_length, 0, READ_ONLY), 
                    ("server id: ", n+2, 2*tab, str(soft_dict["mysql_info"]["db_info"].get("server_id")), n+2, xi, field_length, 0, READ_ONLY), 
                    ("数据库: ", n+3, 2*tab, ",".join(soft_dict["mysql_info"]["db_info"].get("business_db")), n+3, xi, field_length, 0, READ_ONLY), 
                    ("用户: ", n+4, 2*tab, ",".join(soft_dict["mysql_info"]["db_info"].get("business_user")), n+4, xi, field_length, 0, READ_ONLY), 
                    ("密码: ", n+5, 2*tab, ",".join(soft_dict["mysql_info"]["db_info"].get("business_password")), n+5, xi, field_length, 0, READ_ONLY)
                    ]
            if soft_dict["mysql_info"].get("cluster_info") is not None:
                role=soft_dict["mysql_info"]["cluster_info"].get("role")
                soft_elements.append(("角色: ", n+6, 2*tab, role, n+6, xi, field_length, 0, READ_ONLY))
                if role=="slave":
                    soft_elements.append(("同步主机: ", n+7, 2*tab, soft_dict["mysql_info"]["cluster_info"]["sync_host"], n+7, xi, field_length, 0, READ_ONLY))
                    soft_elements.append(("同步数据库: ", n+8, 2*tab, ",".join(soft_dict["mysql_info"]["cluster_info"]["sync_dbs"]), n+8, xi, field_length, 0, READ_ONLY))
        elif softname=="redis":
            soft_elements=[
                    ("密码: ", n+1, 2*tab, soft_dict["redis_info"]["db_info"].get("redis_password"), n+1, xi, field_length, 0, READ_ONLY)
                    ]
            if soft_dict["redis_info"].get("cluster_info") is not None:
                role=soft_dict["redis_info"]["cluster_info"].get("role")
                soft_elements.append(("角色: ", n+2, 2*tab, role, n+2, xi, field_length, 0, READ_ONLY))
                soft_elements.append(("同步主机: ", n+3, 2*tab, soft_dict["redis_info"]["cluster_info"]["master_host"], n+3, xi, field_length, 0, READ_ONLY))
        elif softname=="elasticsearch":
            soft_elements=[
                    ("集群名称: ", n+1, 2*tab, soft_dict["elasticsearch_info"].get("cluster_name"), n+1, xi, field_length, 0, READ_ONLY), 
                    ("集群成员: ", n+2, 2*tab, ",".join(soft_dict["elasticsearch_info"].get("members")), n+2, xi, field_length, 0, READ_ONLY)
                    ]
        elif softname=="rabbitmq":
            soft_elements=[
                    ("集群名称: ", n+1, 2*tab, soft_dict["rabbitmq_info"].get("cluster_name"), n+1, xi, field_length, 0, READ_ONLY), 
                    ("节点类型: ", n+2, 2*tab, soft_dict["rabbitmq_info"].get("node_type"), n+2, xi, field_length, 0, READ_ONLY), 
                    ("集群成员: ", n+3, 2*tab, ",".join(soft_dict["rabbitmq_info"].get("members")), n+3, xi, field_length, 0, READ_ONLY)
                    ]
            if soft_dict["rabbitmq_info"].get("vhosts") is not None:
                soft_elements.append(("虚拟机: ", n+4, 2*tab, ",".join(soft_dict["rabbitmq_info"].get("vhosts")), n+4, xi, field_length, 0, READ_ONLY))
                soft_elements.append(("用户: ", n+5, 2*tab, ",".join(soft_dict["rabbitmq_info"].get("users")), n+5, xi, field_length, 0, READ_ONLY))
                soft_elements.append(("密码: ", n+6, 2*tab, ",".join(soft_dict["rabbitmq_info"].get("passwords")), n+6, xi, field_length, 0, READ_ONLY))
        else:
            soft_elements=[]

        elements.append((f"{softname}配置: ", n, tab, item, n, xi, field_length, 0, READ_ONLY))
        elements.extend(soft_elements)
        length=len(soft_elements)
        n=n+length+1
        return n, elements

    def show_arch_msg(self, title, arch_dict):
        if arch_dict != {}:
            HIDDEN = 0x1
            READ_ONLY = 0x2
            tab=3           # 
            xi=30
            field_length=45
            elements=[]
            n=0
            for node in arch_dict:
                self.log.logger.debug(f"for: {n=}")
                n=n+1
                info=[
                        (f"{node}: ", n, 1, "", n, xi, field_length, 0, HIDDEN), 
                        ("安装软件: ", n+1, tab, ",".join(arch_dict[node]["software"]), n+1, xi, field_length, 0, READ_ONLY), 
                        ("安装目录: ", n+2, tab, arch_dict[node]["located"], n+2, xi, field_length, 0, READ_ONLY)
                        ]
                elements.extend(info)
                n=n+3
                for softname in arch_dict[node]["software"]:
                    n, elements=self.add_soft_elements(softname, elements, tab, xi, field_length, READ_ONLY, n, arch_dict[node])

            elements.append(("", n, 1, "", n, xi, field_length, 0, HIDDEN))
            self.log.logger.debug(f"arch summary: {elements=}")
            code, fields=self.d.mixedform(f"集群配置信息:", elements=elements, title=title, no_cancel=1)

    def read_config(self, file_name_list):
        '''
            从配置文件中读取配置信息
        '''
        result=[]
        for i in file_name_list:
            if i=="project":
                with open(self.project_file, "r", encoding="utf8") as f:
                    project_name=f.read().strip()
                    if project_name == "":
                        project_name="XX项目"
                    result.append(project_name)
            if i=="init":
                with open(self.init_file, "r", encoding="utf8") as init_f:
                        init_json=init_f.read().strip()
                if init_json != "":
                    try:
                        init_dict=json.loads(init_json)
                    except json.decoder.JSONDecodeError:
                        self.d.msgbox(f"配置文件({self.init_file})为非json格式, 请更改格式或清空(非删除)该文件重新配置.\n"
                                "请在修改后重新启动本程序, 本次安装将退出...", title=title)
                        exit()
                else:
                    init_dict={}
                result.append(init_dict)
            if i=="arch":
                with open(self.arch_file, "r", encoding="utf8") as arch_f:
                    arch_json=arch_f.read().strip()
                if arch_json != "":
                    try:
                        arch_dict=json.loads(arch_json)
                    except json.decoder.JSONDecodeError:
                        self.d.msgbox(f"配置文件({self.arch_file})为非json格式, 请更改格式或清空(非删除)该文件重新配置.\n"
                                "请在修改后重新启动本程序, 本次安装将退出...", title=title)
                        exit()
                else:
                    arch_dict={}
                result.append(arch_dict)
        return result

    def config_project(self, project_name, title):
        '''
            配置项目名称
        '''
        code, input_text=self.d.inputbox("请输入本项目名称", init=project_name, title=title)
        if code==self.d.OK:
            with open(self.project_file, "w", encoding="utf8") as f:
                f.write(input_text)
            self.log.logger.debug(f"项目名'{input_text}'写入文件'{self.project_file}'")

    def config_init(self, init_dict, title):
        '''
            配置init.json
        '''
        while True:                     # 添加node信息
            code, fields=self.show_host_msg(title, init_dict)
            init_dict=self.trans_fields_to_dict(fields)
            if code==self.d.OK:
                with open(self.init_file, "w", encoding="utf8") as f:
                    json.dump(init_dict, f)
                self.log.logger.info(f"写入{self.init_file}配置文件")
                break
            elif code=="extra":
                init_dict[""]={            # 添加一个空的主机信息
                        "ip": "", 
                        "root_password":"", 
                        "port":""
                        }         
            else:
                break

    def config_arch(self, init_dict, arch_dict, title):
        '''
            配置arch.json
        '''
        menu_node_choices=[]
        for node in init_dict:
            menu_node_choices.append((node, ""))

        # 删除不存在init_dict中的arch_dict的node
        for node in list(arch_dict.keys()):
            if node not in init_dict:
                arch_dict.pop(node)
                self.log.logger.info(f"{node}不存在于初始化主机中, 已自动删除")

        while True:
            self.show_arch_msg(title, arch_dict)
            code, node=self.d.menu("选择主机以安装软件:", choices=menu_node_choices, title=title, extra_button=True, extra_label="配置完成", ok_label="选择", cancel_label="上一步")
            if code==self.d.OK:
                self.log.logger.info(f"选择主机: {node}")

                if arch_dict.get(node) is None:
                    arch_dict[node]={}

                while True:
                    soft_choices=[]         # 显示软件列表(已安装及未安装)
                    for softname in self.soft:
                        software_list=arch_dict[node].get("software")
                        if software_list is None or softname not in software_list:
                            soft_choices.append((softname, "", 0))
                        else:
                            soft_choices.append((softname, "", 1))

                    code, install_soft=self.d.checklist(f"请选择在'{node}'安装的软件:\n'*'代表已选择", 
                            choices=soft_choices, title=title, cancel_label="上一步")
                    if code==self.d.OK:
                        self.log.logger.info(f"选择安装软件: {install_soft}")
                        arch_dict[node]["software"]=install_soft
                        while True:
                            install_dir=arch_dict[node].get("located")
                            if install_dir is None:
                                install_dir="/data"

                            code, install_dir=self.d.inputbox(f"请在'{node}'主机上指定安装目录", init=install_dir, title=title, cancel_label="上一步")
                            if code==self.d.OK:
                                self.log.logger.info(f"选择安装目录: {install_dir}")
                                arch_dict[node]["located"]=install_dir
                                for softname in install_soft:
                                    soft_dict=self.config_soft(softname, node, arch_dict[node])
                                    self.log.logger.debug(f"{node=}, {soft_dict=}")
                                    arch_dict[node].update(soft_dict)
                                    self.log.logger.debug(f"{arch_dict=}")
                                # 以node为单位写入配置文件
                                with open(self.arch_file, "w", encoding="utf8") as f:
                                    json.dump(arch_dict, f)
                                self.log.logger.debug(f"ALL: {arch_dict=}")
                                self.log.logger.info(f"写入{self.arch_file}配置文件")
                                self.d.msgbox(f"{node}软件配置完成")
                                return 0
                            else:
                                break
                    elif code==self.d.CANCEL:
                        break
                    else:
                        return 1
            elif code=="extra":
                if arch_dict=={}:
                    self.d.msgbox("尚未进行集群配置")
                    continue
                with open(self.arch_file, "w", encoding="utf8") as f:
                    json.dump(arch_dict, f)
                self.log.logger.debug(f"ALL: {arch_dict=}")
                self.log.logger.info(f"写入{self.arch_file}配置文件")
                break
            else:
                break

    def config(self):
        '''集群配置
        1. 配置项目名称
        2. 配置init.json
        3. 配置arch.json
        '''

        while True:
            self.log.logger.info(f"开始集群配置")
            config_menu={
                    "1": "项目名称", 
                    "2": "集群主机", 
                    "3": "集群架构"
                    }
            code, tag=self.d.menu(f"集群配置:", 
                    choices=[
                        ("1", config_menu["1"]), 
                        ("2", config_menu["2"]), 
                        ("3", config_menu["3"])
                        ], 
                    title="配置菜单"
                    )
            if code==self.d.OK:
                self.log.logger.info(f"选择{config_menu[tag]}")
                if tag=="1":
                    project_name=self.read_config(["project"])[0]
                    self.config_project(project_name, config_menu[tag])
                if tag=="2":
                    init_dict=self.read_config(["init"])[0]
                    self.config_init(init_dict, config_menu[tag])
                if tag=="3":
                    init_dict, arch_dict=self.read_config(["init", "arch"])
                    while True:
                        self.log.logger.debug(f"重新返回: {arch_dict=}")
                        status=self.config_arch(init_dict, arch_dict, config_menu[tag])
                        self.log.logger.debug(f"返回值: {status=}")
                        if status==0:
                            continue
                        else:
                            break
            else:
                self.show_menu()

    def config_soft(self, softname, nodename, soft_dict):
        '''
            单个软件配置
        '''
        title=f"{softname}配置"

        if softname=="nginx":
            if soft_dict.get("nginx_info") is not None:
                upstream_nodes=", ".join(soft_dict["nginx_info"].get("proxy_hosts"))
            else:
                upstream_nodes=""

            elements=[
                    ("负载转发的主机名: ", 1, 1, upstream_nodes, 1, 18, 25, 0)
                    ]
            code, upstream_nodes=self.d.form(f"填写{softname}配置信息:", elements=elements, title=title)
            if code==self.d.OK:
                self.log.logger.debug(f"{softname=}, {upstream_nodes=}")
                soft_dict["nginx_info"]={
                        "proxy_hosts": upstream_nodes[0].split(",")
                        }
            else:
                self.cancel("安装")
        elif softname=="glusterfs":
            glusterfs_type_relations={
                    "server_info": "服务端", 
                    "client_info": "客户端"
                    }
            glusterfs_info_dict=soft_dict.get("glusterfs_info")
            glusterfs_type=[]
            glusterfs_is_None=0
            server_flag=0
            client_flag=0
            if glusterfs_info_dict is None:
                glusterfs_is_None=1
            elif glusterfs_info_dict.get("server_info") is not None:
                server_flag=1
            elif glusterfs_info_dict.get("client_info") is not None:
                client_flag=1

            glusterfs_type.append((glusterfs_type_relations["server_info"], "", server_flag))
            glusterfs_type.append((glusterfs_type_relations["client_info"], "", client_flag))

            code, glusterfs_type=self.d.checklist(f"请选择安装类型:", choices=glusterfs_type, title=title)
            if code==self.d.OK:
                self.log.logger.debug(f"{softname=}, {glusterfs_type=}")
                if glusterfs_is_None==1:
                    soft_dict["glusterfs_info"]={}
                else:
                    for i in glusterfs_info_dict:
                        self.log.logger.debug(f"{i=}, {soft_dict=}")
                        if glusterfs_type_relations[i] not in glusterfs_type:
                            soft_dict["glusterfs_info"].pop(i)

                for i in glusterfs_type:
                    if i=="服务端":
                        if soft_dict["glusterfs_info"].get("server_info") is None:
                            volume_dir="/data/volume"
                            members={nodename}
                        else:
                            volume_dir=soft_dict["glusterfs_info"]["server_info"]["volume_dir"]
                            members=soft_dict["glusterfs_info"]["server_info"]["members"]

                        elements=[
                                ("集群成员节点: ", 1, 1, ",".join(members), 1, 20, 25, 0), 
                                ("卷(volume)目录路径: ", 2, 1, volume_dir, 2, 20, 25, 0), 
                                ]
                        code, server_fields=self.d.form(f"填写{softname}配置信息:", elements=elements, title=title)
                        if code==self.d.OK:
                            self.log.logger.debug(f"{softname=}, {server_fields=}")
                            if soft_dict["glusterfs_info"].get("server_info") is None:
                                soft_dict["glusterfs_info"]["server_info"]={}
                            soft_dict["glusterfs_info"]["server_info"]["members"]=server_fields[0].split(",")
                            soft_dict["glusterfs_info"]["server_info"]["volume_dir"]=server_fields[1].strip()
                    elif i=="客户端":
                        if soft_dict["glusterfs_info"].get("client_info") is None:
                            mounted_host=""
                            mounted_dir="/data/mounted"
                        else:
                            mounted_host=soft_dict["glusterfs_info"]["client_info"]["mounted_host"]
                            mounted_dir=soft_dict["glusterfs_info"]["client_info"]["mounted_dir"]

                        elements=[
                                ("挂载源主机: ", 1, 1, mounted_host, 1, 20, 25, 0), 
                                ("本机挂载目录", 2, 1, mounted_dir, 2, 20, 25, 0), 
                                ]
                        code, client_fields=self.d.form(f"填写{softname}配置信息:", elements=elements, title=title)
                        if code==self.d.OK:
                            self.log.logger.debug(f"{softname=}, {client_fields=}")
                            if soft_dict["glusterfs_info"].get("client_info") is None:
                                soft_dict["glusterfs_info"]["client_info"]={}
                            soft_dict["glusterfs_info"]["client_info"]["mounted_host"]=client_fields[0].strip()
                            soft_dict["glusterfs_info"]["client_info"]["mounted_dir"]=client_fields[1].strip()
        elif softname=="jdk" or softname=="tomcat" or softname=="ffmpeg":
            pass
        elif softname=="elasticsearch":
            if soft_dict.get("elasticsearch_info") is None:
                soft_dict["elasticsearch_info"]={}
                cluster_name="es_cluster"
                members=[nodename]
            else:
                cluster_name=soft_dict["elasticsearch_info"]["cluster_name"]
                members=soft_dict["elasticsearch_info"]["members"]

            code, es_type=self.d.menu(f"请选择安装类型:", choices=[("stand", ""), ("cluster", "")], title=title)
            if code==self.d.OK:
                if es_type=="stand":
                    field_length=-25
                else:
                    field_length=25
                elements=[
                        ("集群名称: ", 1, 1, cluster_name, 1, 12, field_length, 0), 
                        ("集群成员: ", 2, 1, ", ".join(members), 2, 12, field_length, 0), 
                        ]
                code, fields=self.d.form(f"填写{softname}信息:", elements=elements, title=title)
                self.log.logger.debug(f"{softname=}, {fields=}")
                if code==self.d.OK:
                    if es_type=="stand":
                        soft_dict["elasticsearch_info"]["cluster_name"]=cluster_name
                        soft_dict["elasticsearch_info"]["members"]=members
                    else:
                        soft_dict["elasticsearch_info"]["cluster_name"]=fields[0]
                        soft_dict["elasticsearch_info"]["members"]=fields[1].split(",")
        elif softname=="mysql":
            if soft_dict.get("mysql_info") is None:
                soft_dict["mysql_info"]={}
                soft_dict["mysql_info"]["db_info"]={}
                root_password="DreamSoft_123"
                server_id="1"
                business_db=""
                business_user=""
                business_password=""
            else:
                root_password=soft_dict["mysql_info"]["db_info"]["root_password"]
                server_id=soft_dict["mysql_info"]["db_info"]["server_id"]
                business_db=soft_dict["mysql_info"]["db_info"]["business_db"]
                business_user=soft_dict["mysql_info"]["db_info"]["business_user"]
                business_password=soft_dict["mysql_info"]["db_info"]["business_password"]

            code, role=self.d.menu("选择安装类型:", choices=[("stand", ""), ("master", ""), ("slave", "")], title=title)
            if code==self.d.OK:
                self.log.logger.debug(f"{softname=}, {role=}")
                elements=[
                        ("MySQL管理员密码: ", 1, 1, root_password, 1, 20, 35, 0), 
                        ("Server ID(唯一): ", 2, 1, str(server_id),2, 20, 35, 0), 
                        ("数据库名: ", 3, 1, ",".join(business_db), 3, 20, 35, 0), 
                        ("用户名: ", 4, 1, ",".join(business_user), 4, 20, 35, 0), 
                        ("密码: ", 5, 1, ",".join(business_password), 5, 20, 35, 0)
                        ]
                cluster_flag=1
                if role=="stand":
                    cluster_flag=0

                if cluster_flag==1:
                    if soft_dict["mysql_info"].get("cluster_info") is None:
                        soft_dict["mysql_info"]["cluster_info"]={}
                        if role=="slave":
                            sync_host=""
                            sync_dbs=""
                    else:
                        if role=="slave":       # 获取原slave信息
                            if soft_dict["mysql_info"]["cluster_info"].get("role")=="slave":
                                sync_host=soft_dict["mysql_info"]["cluster_info"]["sync_host"]
                                sync_dbs=soft_dict["mysql_info"]["cluster_info"]["sync_dbs"]
                            else:
                                sync_host=""
                                sync_dbs=""

                    elements.append(("角色:", 6, 1, role, 6, 20, -35, 0))
                    if role=="slave":
                        elements.append(("同步主机:", 7, 1, sync_host, 7, 20, 35, 0))
                        elements.append(("同步数据库:", 8, 1, ",".join(sync_dbs), 8, 20, 35, 0))

                code, fields=self.d.form(f"填写MySQL({role})信息:", elements=elements, title=title)
                if code==self.d.OK:
                    self.log.logger.debug(f"{softname=}, {fields=}")
                    soft_dict["mysql_info"]["db_info"]["root_password"]=fields[0].strip()
                    soft_dict["mysql_info"]["db_info"]["server_id"]=int(fields[1].strip())
                    soft_dict["mysql_info"]["db_info"]["business_db"]=fields[2].split(",")
                    soft_dict["mysql_info"]["db_info"]["business_user"]=fields[3].split(",")
                    soft_dict["mysql_info"]["db_info"]["business_password"]=fields[4].split(",")
                    if role != "stand":
                        soft_dict["mysql_info"]["cluster_info"]["role"]=role
                        if role=="slave":
                            soft_dict["mysql_info"]["cluster_info"]["sync_host"]=fields[5].strip()
                            soft_dict["mysql_info"]["cluster_info"]["sync_dbs"]=fields[6].split(",")
        elif softname=="rabbitmq":
            if soft_dict.get("rabbitmq_info") is None:
                soft_dict["rabbitmq_info"]={}
                cluster_name="mq_cluster"
                node_type="disc"
                members=[nodename]
                vhosts=["/vhost"]
                users=["dream"]
                passwords=["dream"]
            else:
                cluster_name=soft_dict["rabbitmq_info"]["cluster_name"]
                node_type=soft_dict["rabbitmq_info"]["node_type"]
                members=soft_dict["rabbitmq_info"]["members"]
                vhosts=soft_dict["rabbitmq_info"]["vhosts"]
                users=soft_dict["rabbitmq_info"]["users"]
                passwords=soft_dict["rabbitmq_info"]["passwords"]

            code, mq_type=self.d.menu(f"请选择安装类型:", choices=[("stand", ""), ("cluster", "")], title=title)
            if code==self.d.OK:
                self.log.logger.debug(f"{softname=}, {mq_type=}")
                if mq_type=="stand":
                    field_length=-25
                elif mq_type=="cluster":
                    field_length=25
                elements=[
                        ("集群名称: ", 1, 1, cluster_name, 1, 15, field_length, 20), 
                        ("集群成员: ", 2, 1, ",".join(members), 2, 15, field_length, 20), 
                        ("当前节点类型: ", 3, 1, node_type, 3, 15, field_length, 20), 
                        ("虚拟机名称: ", 4, 1, ",".join(vhosts), 4, 15, 25, 20), 
                        ("用户名: ", 5, 1, ",".join(users), 5, 15, 25, 20), 
                        ("密码: ", 6, 1, ",".join(passwords), 6, 15, 25, 20)
                        ]
                code, fields=self.d.form(f"填写{softname}信息:", elements=elements, title=title)
                if code==self.d.OK:
                    self.log.logger.debug(f"{softname=}, {fields=}")
                    if mq_type=="stand":
                        stand_fields=[cluster_name, ",".join(members), node_type]
                        stand_fields.extend(fields)
                        fields=stand_fields
                        self.log.logger.debug(f"{softname=}, {fields=}")
                    soft_dict["rabbitmq_info"]["cluster_name"]=fields[0].strip()
                    soft_dict["rabbitmq_info"]["members"]=fields[1].split(",")
                    soft_dict["rabbitmq_info"]["node_type"]=fields[2].strip()
                    soft_dict["rabbitmq_info"]["vhosts"]=fields[3].split(",")
                    soft_dict["rabbitmq_info"]["users"]=fields[4].split(",")
                    soft_dict["rabbitmq_info"]["passwords"]=fields[5].split(",")
        elif softname=="redis":
            if soft_dict.get("redis_info") is None:
                soft_dict["redis_info"]={}
                soft_dict["redis_info"]["db_info"]={}
                redis_password="b840fc02d524045429941cc15f59e41cb7be6c599"
            else:
                redis_password=soft_dict["redis_info"]["db_info"]["redis_password"]

            code, redis_type=self.d.menu(f"请选择安装类型:", choices=[("stand", ""), ("cluster", "")], title=title)
            if code==self.d.OK:
                self.log.logger.debug(f"{softname=}, {redis_type=}")
                role="stand"
                elements=[
                    ("redis密码: ", 1, 1, redis_password, 1, 15, 45, 45)
                        ]
                if redis_type=="cluster":
                    if soft_dict["redis_info"].get("cluster_info") is None:
                        soft_dict["redis_info"]["cluster_info"]={}
                        master_host=""
                    else:
                        master_host=soft_dict["redis_info"]["cluster_info"]["master_host"]

                    code, role=self.d.menu(f"请选择{nodename}角色:", choices=[("master", ""), ("slave", "")], title=title)
                    if code==self.d.OK:
                        if role=="master":
                            master_host=nodename
                            field_length=-15
                        elif role=="slave":
                            field_length=15
                        elements.append(("角色: ", 2, 1, role, 2, 15, -15, 0))
                        elements.append(("master节点: ", 3, 1, master_host, 3, 15, field_length, 0))

                code, fields=self.d.form(f"填写{softname}({role})信息:", elements=elements, title=title)
                if code==self.d.OK:
                    self.log.logger.debug(f"{softname=}, {role=}, {fields=}")
                    soft_dict["redis_info"]["db_info"]["redis_password"]=fields[0]
                    if role!="stand":
                        soft_dict["redis_info"]["cluster_info"]["role"]=role
                        if role=="master":
                            soft_dict["redis_info"]["cluster_info"]["master_host"]=master_host
                        elif role=="slave":
                            soft_dict["redis_info"]["cluster_info"]["master_host"]=fields[1]

        return soft_dict

    def init(self, title):
        with open(self.init_file, "r", encoding="utf8") as f:
            init_dict=json.load(f)

        self.log.logger.info("监测主机配置, 请稍后...\n")
        flag, connect_msg=self.connect_test(init_dict)
        if flag==1:
            self.log.logger.error("主机信息配置有误, 请根据下方显示信息修改:")
            for node_msg in connect_msg:
                self.log.logger.info(f"{node_msg[0]}:\t{node_msg[2]}")
            exit()

        local_python3_file=self.conf_dict["location"].get("python3")
        read_fd, write_fd = os.pipe()
        child_pid = os.fork()
        if child_pid == 0:
            os.close(read_fd)
            with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                g_log=Logger(self.log_file, self.log_level, "graphical", g_file=wfile)
                super(graphics_deploy, self).init(init_dict, local_python3_file, g_log)
            os._exit(0)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=30, width=180)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            pass

    def install(self, title):
        pass

    def start(self, title):
        pass

    def cancel(self, msg):
        self.d.msgbox(f"取消{msg}")
        self.log.logger.info(f"退出{msg}")
        exit()

    def show_menu(self):
        while True:
            menu={
                    "1": "配置向导", 
                    "2": "集群初始化", 
                    "3": "集群安装", 
                    "4": "集群启动"
                    }

            code,tag=self.d.menu(f"若是首次进行部署, 请从\'{menu['1']}\'开始:", 
                    choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ("3", menu["3"]),
                        ("4", menu["4"])
                        ], 
                    title="菜单"
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.config()
                if tag=="2":
                    self.init(menu[tag])
                if tag=="3":
                    self.install(menu[tag])
                if tag=="4":
                    self.start(menu[tag])
                self.d.infobox(f"{menu[tag]}完成, 将返回主菜单...")
                time.sleep(3)
            else:
                self.cancel("安装")

    def show(self):
        introduction=dedent("""
            本程序主要用来自动部署项目集群. 
            部署过程将使用方向按键进行选择, 【enter】键用来确认.
            是否开始部署 ?
        """)

        self.log.logger.info("开始文本图形化部署")

        code=self.d.yesno(introduction, height=10, width=60, title="说明")

        if code==self.d.OK:
            self.show_menu()
        else:
            self.cancel("安装")

class platform_deploy(Deploy):
    '''平台安装'''

    def __init__(self, conf_file, init_file, arch_file, project_file):
        super(text_deploy, self).__init__(conf_file, init_file, arch_file, project_file)
        self.log=Logger(["file", "console", "paltform"], self.log_level, self.log_file)

    def check(self):
        '''
            校验配置文件
        '''
        pass

    def init(self):
        with open(self.init_file, "r", encoding="utf8") as f:
            init_dict=json.load(f)

        self.log.logger.info("监测主机配置, 请稍后...\n")
        flag, connect_msg=self.connect_test(init_dict)
        if flag==1:
            self.log.logger.error("主机信息配置有误, 请根据下方显示信息修改:")
            for node_msg in connect_msg:
                self.log.logger.info(f"{node_msg[0]}:\t{node_msg[2]}")
            exit()

        local_python3_file=self.conf_dict["location"].get("python3")
        status=super(text_deploy, self).init(init_dict, local_python3_file, self.log)
        if status=="OK":
            self.log.logger.info("初始化完成\n")
            self.log.logger.info("各主机信息如下:")
            self.get_host_msg(init_dict, self.log)
        else:
            self.log.logger.error(f"初始化失败: {status}")

    def install(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群安装...\n")
        super(text_deploy, self).install(init_dict, arch_dict, self.log)

    def start(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群启动...\n")
        super(text_deploy, self).install(init_dict, arch_dict, self.log)

    
if __name__ == "__main__":
    main()
