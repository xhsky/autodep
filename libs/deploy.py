#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 17:37:47
# sky

import locale, json, os, time, sys, requests, tarfile, math
from libs.env import logs_dir, log_file, log_file_level, log_console_level, log_platform_level, log_graphics_level, \
        remote_python_transfer_dir, remote_python_install_dir,  remote_python_exec, \
        remote_code_dir, remote_pkgs_dir, \
        interface, test_mode, \
        host_info_file, init_stats_file, install_stats_file, start_stats_file, update_stats_file, \
        update_config_file_name, \
        g_term_rows, g_term_cols, \
        soft_weights_dict, soft_weights_unit_dict, host_weights_unit_dict, \
        located_dir_name, placeholder_software_list

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir, exist_ok=1)

from textwrap import dedent
from libs.common import Logger, post_info, format_size
from libs.remote import ssh, soft
from libs import update

class Deploy(object):
    '''集群部署
    '''
    def __init__(self, conf_file, init_file, arch_file, project_file):
        with open(conf_file, "r", encoding="utf8") as conf_f, open(project_file, "r", encoding="utf8") as project_f:
            self.conf_dict=json.load(conf_f)
            self.soft=self.conf_dict["software"].keys()
            self.project_dict=json.load(project_f)
            self.project_id=self.project_dict['project_id']
            self.project_name=self.project_dict['project_name']
            self.project_env=self.project_dict['project_env']

        self.init_file=init_file
        self.arch_file=arch_file

        self.init_stats_dict={
                "project_id": self.project_id, 
                "mode": "init", 
                "result": True, 
                "stats":{}
                }
        self.install_stats_dict={
                "project_id": self.project_id, 
                "mode": "install", 
                "result": True, 
                "stats":{}
                }
        self.start_stats_dict={
                "project_id": self.project_id, 
                "mode": "start", 
                "result": True, 
                "stats":{}
                }
        self.update_stats_dict={
                "project_id": self.project_id, 
                "mode": "update", 
                "result": True, 
                "stats":{}
                }

    def _to_init_dict(self, all_host_info):
        """
        将获取的环境检测信息转为发送平台的dict
        """
        all_host_dict={}
        for node in all_host_info:
            if all_host_info[node][0] == 0:
                # 将str转为json
                node_info=all_host_info[node][1]
                node_info=node_info[node_info.index("{"):]

                all_host_dict[node]=json.loads(node_info)
            else:
                all_host_dict[node]={
                        "error_info": all_host_info[node][1]
                        } 
        return all_host_dict

    def generate_info(self, mode, info_dict, **kwargs):
        """
        信息生成: 平台, 文件
        """

        if mode=="platform":
            info="状态信息已发送至平台\n"
            error_info="状态信息发送失败\n"
            file_=None
        elif mode=="file":
            info="状态信息已写入文件\n"
            error_info="状态信息写入失败\n"
            file_=kwargs["stats_file"]

        self.log.logger.debug(f"状态信息: {json.dumps(info_dict)}")
        result, message=post_info(mode, info_dict, file_)
        if result:
            self.log.logger.info(info)
        else:
            self.log.logger.error(f"{error_info}: {message}")

    def connect_test(self, init_dict):
        """
            测试init.json的账号, 密码, 端口

            return:
                flag,                       
                connect_msg={
                "status": N, 
                "msg": msg
                }
                
        """
        ssh_client=ssh()
        connect_msg={}
        flag=0
        for node in init_dict:
            #ip=init_dict[node].get("ip")
            port=init_dict[node].get("port")
            password=init_dict[node].get("root_password")
            status, msg=ssh_client.password_conn(node, port, password)
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
        ssh_client=ssh()
        all_host_info={}
        get_msg_py="./bin/get_host_info.py"
        for node in init_dict:
            port=init_dict[node].get("port")

            remote_file=f"{remote_code_dir}/{get_msg_py.split('/')[-1]}"
            ssh_client.scp(node, port, "root", get_msg_py, remote_file)
            get_msg_command=f"{remote_python_exec} {remote_file}"
            self.log.logger.debug(f"获取{node}主机信息: {get_msg_command=}")
            status=ssh_client.exec(node, port, get_msg_command, get_pty=0)

            stdout_msg=status[1].read().strip().decode("utf8")
            stderr_msg=status[2].read().strip().decode("utf8")
            stats_value=status[1].channel.recv_exit_status()
            if  stats_value != 0:
                msg=stdout_msg
            else:
                msg=stderr_msg
            all_host_info[node]=[stats_value, msg]
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
    def _exclude_placeholder_software(self, soft_list):
        """
        从列表中删除占位软件
        """
        for placeholder_software in placeholder_software_list:
            while True:
                if placeholder_software in soft_list:
                    soft_list.remove(placeholder_software)
                else:
                    break
        return soft_list

    def init(self, init_dict, local_python3_file):
        """主机环境初始化
            * 生成秘钥
            * 免密码登录
            * 关闭firewalld
            * 关闭selinux
            * 配置Python3环境
            * nproc nofile
            * 接口连通性测试
        """
        ssh_client=ssh()
        if ssh_client.gen_keys():
            self.log.logger.info("本机生成密钥对\n")
        else:
            self.log.logger.info("本机已存在密钥对\n")

        # 初始化
        init_result=True
        for node in init_dict:
            self.log.logger.info(f"***主机{node}环境初始化***")
            stats_value=True
            stats_message=""

            try:
                port=init_dict[node].get("port")
                password=init_dict[node].get("root_password")

                ssh_client.free_pass_set(node, port, password)
                self.log.logger.info(f"免密码登录设置完成")
                
                # 传输Python
                remote_python3_file=f"{remote_python_transfer_dir}/{local_python3_file.split('/')[-1]}"
                self.log.logger.debug(f"传输Python安装包...")
                ssh_client.scp(node, port, "root", local_python3_file, remote_python3_file)

                command=f"tar -xf {remote_python3_file} -C {remote_python_install_dir}"
                self.log.logger.debug(f"配置Python环境")
                status=ssh_client.exec(node, port, command)
                if status[1].channel.recv_exit_status() != 0:
                    error_info=f"Python3安装报错, 进程退出: {status[2].read().decode('utf8')}"
                    self.log.logger.error(error_info)
                    init_result=error_info
                    stats_value=False
                    stats_message=error_info
                    break
                else:
                    self.log.logger.info(f"配置Python3环境完成")

                # 执行init.py
                init_py="./bin/init.py"
                trans_files_dict={
                        "lib_file": ["./libs/common.py", f"{remote_code_dir}/libs/common.py"],
                        "env_file": ["./libs/env.py", f"{remote_code_dir}/libs/env.py"],
                        "py_file": [init_py, f"{remote_code_dir}/{init_py.split('/')[-1]}"]
                        }
                init_args={
                        #"hostname": node, 
                        #"hosts": hosts_list, 
                        "interface": interface, 
                        }
                soft_control=soft(node, port, ssh_client)
                status=self.control(node, port, "init", trans_files_dict, init_args, ssh_client, soft_control)

                for line in status[1]:
                    self.log.logger.info(line.strip())
                if status[1].channel.recv_exit_status() != 0:
                    error_info=f"{node}远程初始化失败"
                    self.log.logger.error(error_info)
                    init_result=error_info
                    stats_value=False
                    stats_message=error_info
                    break
                else:
                    self.log.logger.info(f"{node}远程初始化完成")
            except Exception as e:
                init_result=str(e)
                stats_value=False
                stats_message=str(e)

            self.init_stats_dict["stats"][node]={
                    "stats_value": stats_value, 
                    "stats_message": stats_message
                    }
        return init_result

    def control(self, ip, port, action, trans_files_dict, args_dict, ssh_client, soft_control):
        for trans_file in trans_files_dict:
            src, dst=trans_files_dict[trans_file]
            self.log.logger.debug(f"传输文件: {trans_file}, {src=}, {dst=}")
            ssh_client.scp(ip, port, "root", src, dst)

        remote_py_file=trans_files_dict["py_file"][1]
        if action=="init":
            status=soft_control.init(remote_py_file, args_dict)
        elif action=="install":
            args_dict["pkg_file"]=trans_files_dict["pkg_file"][1]
            status=soft_control.install(remote_py_file, args_dict)
        elif action=="start":
            status=soft_control.start(remote_py_file, args_dict)
        return status

    def control_bak(self, action, trans_files_dict):
        flag=True
        for node in arch_dict:
            self.log.logger.info(f"*****{node}节点*****")
            ssh_port=init_dict[node].get("port")

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

    def install(self, init_dict, arch_dict):
        if test_mode:
            trans_files_dict={
                    "lib_file": ["./libs/common.py", f"{remote_code_dir}/libs/common.py"], 
                    "env_file": ["./libs/env.py", f"{remote_code_dir}/libs/env.py"]
                    }
        else:
            trans_files_dict={}

        flag=True

        # 获取所有hosts
        hosts_list=[]
        for node in arch_dict:
            hosts_list.append(f"{arch_dict[node].get('ip')} {node}")

        for node in arch_dict:
            ip=arch_dict[node].get("ip")
            self.log.logger.info(f"***{node}({ip})安装***")
            self.log.logger.info(f"安装目录: {arch_dict[node]['located']}")
            self.install_stats_dict["stats"][node]={}
            port=init_dict[arch_dict[node]["ip"]]["port"]
            ssh_client=ssh()

            self.log.logger.info("设置hosts")
            set_hosts_file="set_hosts.py"
            ssh_client.scp(ip, port, "root", f"./bin/{set_hosts_file}", f"{remote_code_dir}/{set_hosts_file}")
            set_hosts_dict={
                    "hostname": node, 
                    "hosts": hosts_list
                    }
            set_hosts_command=f"{remote_python_exec} {remote_code_dir}/{set_hosts_file} '{json.dumps(set_hosts_dict)}'"
            self.log.logger.debug(f"{set_hosts_command=}")
            status=ssh_client.exec(ip, port, set_hosts_command)
            for line in status[1]:
                self.log.logger.info(line.strip())
            if status[1].channel.recv_exit_status() == 0:
                self.log.logger.info(f"{node} hosts设置完成")

                soft_control=soft(ip, port, ssh_client)
                for softname in self._exclude_placeholder_software(arch_dict[node]["software"]):
                    self.log.logger.info(f"{softname}安装...")
                    stats_value=True

                    pkg_file=self.conf_dict["location"].get(softname)
                    trans_files_dict.update(
                            {
                                "py_file": [f"./bin/{softname}.py", f"{remote_code_dir}/{softname}.py"], 
                                "pkg_file": [pkg_file, f"{remote_pkgs_dir}/{pkg_file.split('/')[-1]}"]
                                }
                            )
                    # 去除located结尾的/
                    located_dir=arch_dict[node]["located"]
                    if located_dir.endswith("/"):
                        arch_dict[node]["located"]=located_dir[0:-1]

                    status=self.control(ip, port, "install", trans_files_dict, arch_dict[node], ssh_client, soft_control)
                    for line in status[1]:
                        self.log.logger.info(line.strip())
                    if status[1].channel.recv_exit_status() == 0:
                        self.log.logger.info(f"{softname}安装完成")
                    else:
                        self.log.logger.error(f"{softname}安装失败")
                        stats_value=False
                        flag=False
                    self.install_stats_dict["stats"][node][softname]=stats_value
            else:
                self.log.logger.error(f"{node} hosts设置失败")
                flag=False

        self.install_stats_dict["result"]=flag
        return flag

    def start(self, init_dict, arch_dict):
        if test_mode:
            trans_files_dict={
                    "lib_file": ["./libs/common.py", f"{remote_code_dir}/libs/common.py"], 
                    "env_file": ["./libs/env.py", f"{remote_code_dir}/libs/env.py"]
                    }
        else:
            trans_files_dict={}

        flag=True
        for node in arch_dict:
            self.log.logger.info(f"***{node}启动***")
            self.start_stats_dict["stats"][node]={}
            port=init_dict[arch_dict[node]["ip"]]["port"]
            ssh_client=ssh()
            soft_control=soft(node, port, ssh_client)
            for softname in self._exclude_placeholder_software(arch_dict[node]["software"]):
                self.log.logger.info(f"{softname}启动...")
                stats_value=True

                trans_files_dict.update(
                        {
                            "py_file": [f"./bin/{softname}.py", f"{remote_code_dir}/{softname}.py"]
                            }
                        )
                # 去除located结尾的/
                located_dir=arch_dict[node]["located"]
                if located_dir.endswith("/"):
                    arch_dict[node]["located"]=located_dir[0:-1]

                status=self.control(node, port, "start", trans_files_dict, arch_dict[node], ssh_client, soft_control)
                for line in status[1]:
                    self.log.logger.info(line.strip())
                if status[1].channel.recv_exit_status() == 0:
                    self.log.logger.info(f"{softname}启动完成")
                else:
                    self.log.logger.error(f"{softname}启动失败")
                    stats_value=False
                    flag=False
                self.start_stats_dict["stats"][node][softname]=stats_value

        self.start_stats_dict["result"]=flag
        return flag

    def update(self, package_list):
        """
        """
        if len(package_list)==0:
            self.log.logger.info("使用项目包")
            package_list=self.project_dict['project_data']

        result=True
        for package in package_list:
            package_name=package.split("/")[-1]
            self.log.logger.info(f"{package_name}更新")
            self.update_stats_dict["stats"][package_name]={}
            if os.path.exists(package):
                try:
                    self.log.logger.debug("获取更新配置文件")
                    with tarfile.open(package, "r", encoding="utf8") as tar:
                        tar.extract(update_config_file_name, remote_code_dir)
                        with open(f"{remote_code_dir}/{update_config_file_name}", "r", encoding="utf8") as f:
                            update_dict=json.load(f)
                            self.log.logger.debug(f"更新配置: {update_dict}")
                        mode=update_dict["mode"]
                        if mode=="code":
                            status, hosts_update_dict=update.code_update(package, update_dict, self.log)
                        elif mode=="db":
                            status, hosts_update_dict=update.db_update(package, update_dict, self.log)
                        else:
                            message=f"{mode}类型不匹配"
                            self.log.logger.error(message)
                            hosts_update_dict={}
                            status=False

                        if not status:
                            result=False
                        self.update_stats_dict["stats"][package_name]=hosts_update_dict
                except Exception as e:
                    self.log.logger.error(f"更新失败: {str(e)}")
                    result=False
            else:
                self.log.logger.error(f"该文件{package}不存在")
                result=False
        self.update_stats_dict["result"]=result
        return result

class text_deploy(Deploy):
    '''文本安装'''

    def __init__(self, conf_file, init_file, arch_file, project_file):
        super(text_deploy, self).__init__(conf_file, init_file, arch_file, project_file)
        self.log=Logger({"file": log_file_level, "console": log_console_level}, log_file=log_file)
        self.ssh_client=ssh()

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
            for ip in connect_msg:
                self.log.logger.info(f"{ip}:\t{connect_msg[ip]['msg']}")
            sys.exit()

        local_python3_file=self.conf_dict["location"].get("python3")
        status=super(text_deploy, self).init(init_dict, local_python3_file)
        if status is True:
            self.log.logger.info("初始化完成\n")
            self.log.logger.info("获取主机信息...")
            all_host_info=self.get_host_msg(init_dict)
            self.init_stats_dict["host_info"]=self._to_init_dict(all_host_info)

            for node in all_host_info:
                if all_host_info[node][0] == 0:
                    node_info=all_host_info[node][1]
                    self.log.logger.debug(f"{node_info=}")
                    node_info=node_info[node_info.index("{"):]
                    #self.log.logger.debug(f"{node_info=}")
                    node_info_dict=json.loads(node_info)
                    node_info=dedent(f"""
                    主机: {node}
                    发行版本: \t{node_info_dict['os_name']}
                    内核版本: \t{node_info_dict['kernel_version']}
                    CPU:      \t{node_info_dict['CPU'][0]}({node_info_dict['CPU'][1]}%)
                    内存:     \t{node_info_dict['Mem'][0]}({node_info_dict['Mem'][1]}%)""")
                    for disk in node_info_dict["Disk"]:
                        node_info=f"{node_info}\n磁盘({disk}): \t{node_info_dict['Disk'][disk][0]}({node_info_dict['Disk'][disk][1]}%)"
                    for port in node_info_dict["Port"]:
                        node_info=f"{node_info}\n端口({port}): \t{node_info_dict['Port'][port][1]}/{node_info_dict['Port'][port][0]}"
                    self.log.logger.info(node_info)
                else:
                    self.log.logger.error(all_host_info[node][1])
        else:
            self.log.logger.error(f"初始化失败: {status}")

        # 生成初始化信息至文件
        self.generate_info("file", self.init_stats_dict, stats_file=init_stats_file)

    def install(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群安装...\n")
        result=super(text_deploy, self).install(init_dict, arch_dict)
        if result:
            self.log.logger.info("集群安装完成")
        else:
            self.log.logger.error("集群安装失败")
        self.generate_info("file", self.install_stats_dict, stats_file=install_stats_file)

        return result

    def start(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群启动...\n")
        result=super(text_deploy, self).start(init_dict, arch_dict)
        if result:
            self.log.logger.info("集群启动完成")
        else:
            self.log.logger.error("集群启动失败")
        self.generate_info("file", self.start_stats_dict, stats_file=start_stats_file)

        return result

    def update(self, package_list=[]):
        self.log.logger.info("开始更新...")
        result=super(text_deploy, self).update(package_list)
        if result:
            self.log.logger.info("更新完成")
        else:
            self.log.logger.error("更新失败")
        self.generate_info("file", self.update_stats_dict, stats_file=update_stats_file)
        return result

    def deploy(self):
        """
        install, start, update
        """

        stage_all=["install", "start", "update"]
        stage_method={
                "install": self.install, 
                "start": self.start, 
                "update": self.update
                }
        for stage in stage_all:
            if stage_method[stage]():
                continue
            else:
                self.log.logger.error(f"'{stage}'阶段执行失败")
                sys.exit(1)

class graphics_deploy(Deploy):
    '''文本图形化安装'''

    from dialog import Dialog

    def __init__(self, conf_file, init_file, arch_file, project_file):
        super(graphics_deploy, self).__init__(conf_file, init_file, arch_file, project_file)
        self.log=Logger({"file": log_file_level}, log_file=log_file)

        with open(self.arch_file, "r", encoding="utf8") as arch_f, \
                open(self.init_file, "r", encoding="utf8") as init_f:
            self.init_dict=json.load(init_f)
            self.arch_dict=json.load(arch_f)

        self.soft_weights_unit=soft_weights_unit_dict[self.project_env]

        locale.setlocale(locale.LC_ALL, '')
        self.d = self.Dialog(dialog="dialog", autowidgetsize=1)
        self.d.set_background_title("集群管理")
        self.term_rows, self.term_cols=self.get_term_size()

    def get_term_size(self):
        """
            获取终端尺寸
        """
        term_rows, term_cols=self.d.maxsize(use_persistent_args=False)
        if term_rows < g_term_rows or term_cols < g_term_cols:
            print(f"当前终端窗口({term_rows}, {term_cols})过小({g_term_rows}, {g_term_cols}), 请放大窗口后重试")
            sys.exit(1)
        else:
            return term_rows, term_cols

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

    def get_file_path(self, init_path, title):
        """
        获取选择文件路径
        """
        while True:
            code, file_=self.d.fselect(init_path, height=10, width=60, title=title)
            if code==self.d.OK:
                code=self.d.yesno(f"确认选择文件: {file_} ?", height=6, width=45)
                if code==self.d.OK:
                    if os.path.exists(file_):
                        if os.path.isfile(file_):
                            return file_
                        else:
                            self.d.msgbox(f"该选择'{file_}'不是文件, 请重新选择", height=6, width=45)
                    else:
                        self.d.msgbox(f"该文件'{file_}'不存在, 请重新选择", height=6, width=45)
            else:
                return ""

    def get_config(self, config_file):
        """
        从配置文件中获取配置
        """

        try:
            with open(config_file, "r", encoding="utf8") as f:
                config_dict=json.load(f)
                return config_dict
        except Exception as e:
            self.log.logger.error(f"无法加载{config_file}: {e}")
            return False

    def _exclude_resouce(self, host_info_dict, arch_dict):
        """
        排除已安装软件的资源
        """
        return host_info_dict

    def _host_nums_verifi(self):
        """
        集群主机与模板主机数相同
        """
        self.log.logger.debug("验证架构主机数量...")
        if len(self.init_dict) != len(self.arch_dict):
            return False, "配置主机数量与模板主机数量不一致, 请重新配置"
        else:
            return True, ""

    def _localized_soft_resource_verifi(self):
        """
        从模板中查找是否有已安装软件(国产化软件)
        """
        self.log.logger.debug("适配国产化软件...")

        return True, ""

    def _get_max_disk_name(self):
        """
        获取每个ip剩余空间最大的磁盘目录名称

        return { 
            ip: max_disk_name, 
            ip: max_disk_name, 
        }
        """
        max_disk_dict={}
        for ip in self.host_info_dict:
            disk_sorted=sorted(self.host_info_dict[ip]["Disk"].items(), key=lambda item:item[1][0]*(100-item[1][1]))
            max_disk_dict[ip]=disk_sorted[-1][0]
        return max_disk_dict

    def _resource_used_verifi(self):
        """
        针对各主机当前CPU使用率, 内存使用率, 磁盘(最大)使用率校验(20%)
        """
        self.log.logger.debug("校验主机资源...")
        max_cpu_percent=30
        max_mem_percent=20
        max_disk_percent=20
        max_disk_dict=self._get_max_disk_name()
        for ip in self.host_info_dict:
            cpu_used_percent=self.host_info_dict[ip]["CPU"][1]
            self.log.logger.debug(f"{ip}: {cpu_used_percent=}")
            if cpu_used_percent > max_cpu_percent:
                return False, f"'{ip}'主机CPU使用率异常({cpu_used_percent}%), 请检查后再试"

            mem_used_percent=self.host_info_dict[ip]["Mem"][1]
            self.log.logger.debug(f"{ip}: {mem_used_percent=}")
            if mem_used_percent > max_mem_percent:
                return False, f"'{ip}'主机内存使用率异常({mem_used_percent}%), 请检查后再试"

            disk_used_percent=self.host_info_dict[ip]["Disk"][max_disk_dict[ip]][1]
            self.log.logger.debug(f"{ip}: 最大磁盘目录: {max_disk_dict[ip]}, {disk_used_percent=}")
            if disk_used_percent > max_disk_percent:
                return False, f"'{ip}'主机磁盘({max_disk_name})使用率异常({disk_used_percent}%), 请检查后再试"
        else:
            return True, ""

    def _arch_match(self):
        """
        根据模板中各节点安装软件的权重和 对应 集群中各节点权重(排序对应), 并将将ip赋值给node配置
        """
        ip_weights_dict={}
        node_weights_dict={}
        
        self.log.logger.debug("主机匹配模板...")
        try:
            # 获取节点权重
            for node in self.arch_dict:
                node_weights=0
                for softname in self.arch_dict[node]["software"]:
                    node_weights=node_weights+soft_weights_dict[softname]
                node_weights_dict[node]=node_weights
            self.log.logger.debug(f"{node_weights_dict=}")

            # 获取ip权重
            for ip in self.host_info_dict:
                ip_weights=self.host_info_dict[ip]["CPU"][0]/host_weights_unit_dict["cpu"]+round(self.host_info_dict[ip]["Mem"][0]/host_weights_unit_dict["mem"], 2)
                ip_weights_dict[ip]=ip_weights
            self.log.logger.debug(f"{ip_weights_dict=}")

            # 节点与ip权重排序
            ip_weights_sort=[ x for x, y in sorted(ip_weights_dict.items(), key=lambda item:item[1])]
            node_weights_sort=[ x for x, y in sorted(node_weights_dict.items(), key=lambda item:item[1])]

            # 根据排序对应, 赋值
            for node, ip in zip(node_weights_sort, ip_weights_sort):
                self.arch_dict[node]["ip"]=ip
                self.log.logger.debug(f"{ip} <--> {node}")

            # 选择最大磁盘赋值
            max_disk_dict=self._get_max_disk_name()
            for _ in self.arch_dict:
                max_disk_dir=f"{max_disk_dict[self.arch_dict[_]['ip']]}"
                if max_disk_dir.endswith("/"):
                    located_dir=f"{max_disk_dir}{located_dir_name}"
                else:
                    located_dir=f"{max_disk_dir}/{located_dir_name}"
                self.arch_dict[_]["located"]=located_dir

            return True, ""
        except Exception as e:
            return False, str(e)

    def _resource_verifi(self):
        """
        排序对应后, 比较模板中节点上软件最小配置总量与相应主机的资源总量
        """
        self.log.logger.debug("验证集群资源与模板资源...")
        for node in self.arch_dict:
            ip=self.arch_dict[node]["ip"]
            ip_mem=self.host_info_dict[ip]["Mem"][0]
            ip_cpu=self.host_info_dict[ip]["CPU"][0]
            self.log.logger.debug(f"{node}: {ip_mem=}, {ip_cpu=}")

            node_mem_M=0
            node_cpu=0
            for softname in self.arch_dict[node]["software"]:
                node_mem_M=node_mem_M+soft_weights_dict[softname] * 1024 * self.soft_weights_unit
                node_cpu=node_cpu+soft_weights_dict[softname] * 1 * self.soft_weights_unit
            else:
                self.log.logger.debug(f"{node}: {node_mem_M=}, {node_cpu=}")
                ip_free_mem_M=self._get_free_mem(ip_mem) * 1024 * 1024
                self.log.logger.debug(f"{node}: ip free mem(M): {ip_free_mem_M}, node mem(M): {node_mem_M}")
                if ip_free_mem_M < node_mem_M:            
                    return False, f"'{ip}'主机至少需要{node_mem_M}M内存"
                self.log.logger.debug(f"{node}: ip cpu: {ip_cpu}, node cpu: {node_cpu}")
                if ip_cpu < node_cpu:
                    return False, f"'{ip}'主机至少需要{math.ceil(node_cpu)}核心CPU"
        else:
            return True, ""

    def _software_resource_reallocation(self, node, resource_dict, weights_sum, softname, soft_weights):
        """
        单个软件重新分配资源
        """
        #softname_mem=f"{int(resource_dict['mem'] * soft_weights/weights_sum)}M"
        softname_mem=int(resource_dict['mem'] * soft_weights/weights_sum)

        softname_cpu=int(resource_dict["cpu"] * soft_weights/weights_sum)
        if softname_cpu == 0:
            softname_cpu=1

        if softname=="elasticsearch":
            self.arch_dict[node]["elasticsearch_info"]["jvm_mem"]=format_size(softname_mem, integer=True)
        elif softname=="mysql":
            self.arch_dict[node]["mysql_info"]["db_info"]["innodb_mem"]=format_size(softname_mem, integer=True)
        elif softname=="nginx":
            self.arch_dict[node]["nginx_info"]["worker_processes"]=softname_cpu
        elif softname=="rabbitmq":
            self.arch_dict[node]["rabbitmq_info"]["erlang_mem"]=format_size(softname_mem, integer=True)
        elif softname=="redis":
            self.arch_dict[node]["redis_info"]["db_info"]["redis_mem"]=format_size(softname_mem, integer=True)
        elif softname=="rocketmq":
            self.arch_dict[node]["recketmq_info"]["namesrv_mem"]=format_size(int(softname_mem/3), integer=True)
            self.arch_dict[node]["recketmq_info"]["broker_mem"]=format_size(int(softname_mem/3 * 2), integer=True)
        elif softname=="tomcat":
            self.arch_dict[node]["tomcat_info"]["jvm_mem"]=format_size(softname_mem, integer=True)
        else:
            pass
    
    def _get_free_mem(self, mem_total):
        """
        获取主机可用内存大小
        """
        system_mem_M=mem_total * 0.1 / 1024 / 1024
        if system_mem_M >= 2048:                    # 系统保留内存最多2G
            mem_free=mem_total-2048 * 1024 * 1024
        else:
            mem_free=mem_total * 0.9
        return mem_free

    def _resource_reallocation(self):
        """
        根据现有配置重新分配各软件资源
        """
        self.log.logger.debug("各软件分配资源...")
        for node in self.arch_dict:
            mem_total=self.host_info_dict[self.arch_dict[node]["ip"]]["Mem"][0]
            mem_free=self._get_free_mem(mem_total)
            cpu_cores=self.host_info_dict[self.arch_dict[node]["ip"]]["CPU"][0]
            resource_dict={
                    "mem": mem_free, 
                    "cpu": cpu_cores
                    }
            self.log.logger.debug(f"{node}可分配资源: {resource_dict}")

            # 获取node软件的权重和
            weights_sum=0
            for softname in self.arch_dict[node]["software"]:
                weights_sum=weights_sum+soft_weights_dict[softname]

            # 重新分配各软件资源
            for softname in self.arch_dict[node]["software"]:
                self._software_resource_reallocation(node, resource_dict, weights_sum, softname, soft_weights_dict[softname])
        else:
            return True, ""

    def _cluster_resource_reallocation(self):
        """
        分配资源后, 校验软件集群中各软件配置是否相同. 若不同, 则将集群中各软件重置为最小配置
        """
        self.log.logger.debug("集群资源验证...")
        return True, ""

    def generate_arch(self):
        """
        生成arch.json
        """
        with open(host_info_file, "r", encoding="utf8") as host_f:
            self.host_info_dict=json.load(host_f)

        verifi_funs=[
                self._host_nums_verifi, 
                self._localized_soft_resource_verifi, 
                self._resource_used_verifi, 
                self._arch_match, 
                self._resource_verifi, 
                self._resource_reallocation, 
                self._cluster_resource_reallocation
                ]

        interval=int(100/len(verifi_funs))
        percent=0
        self.d.gauge_start("主机资源校验中...")
        for verifi_fun in verifi_funs:
            time.sleep(1)
            result, msg=verifi_fun()
            percent=percent+interval
            if result:
                self.d.gauge_update(percent, text="架构自动匹配中...", update_text=True)
            else:
                self.d.gauge_stop()
                self.log.logger.error(msg)
                self.d.msgbox(msg)
                return False
        else:
            self.d.gauge_stop()
            self.log.logger.debug(f"回写入文件: {self.arch_file}: {json.dumps(self.arch_dict, ensure_ascii=False)}")
            with open(self.arch_file, "w", encoding="utf8") as f:
                json.dump(self.arch_dict, f, ensure_ascii=False)
            return True

    def show_init_info(self, title, json_file):
        """
            显示各主机信息
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi_1=20
        xi_2=30
        xi_3=45
        xi_4=60
        xi_5=75
        field_length=45
        elements=[]

        with open(json_file, "r", encoding="utf8") as f:
            all_host_info_dict=json.load(f)
        n=0
        for ip in all_host_info_dict:
            n=n+1
            node_info_dict=all_host_info_dict[ip]
            if node_info_dict.get("error_info") is None:
                info=[
                        (f"{ip}: ", n, 1, "", n, xi_1, field_length, 0, HIDDEN), 
                        ("内核版本: ", n+1, tab, node_info_dict["kernel_version"], n+1, xi_2, field_length, 0, READ_ONLY), 
                        ("发行版本: ", n+2, tab, node_info_dict["os_name"], n+2, xi_2, field_length, 0, READ_ONLY), 
                        ("CPU个数: ", n+3, tab, f"{node_info_dict['CPU'][0]}", n+3, xi_1, field_length, 0, READ_ONLY), 
                        ("CPU使用率: ", n+3, xi_2, f"{node_info_dict['CPU'][1]}%", n+3, xi_3, field_length, 0, READ_ONLY), 
                        ("内存大小: ", n+4, tab, format_size(node_info_dict['Mem'][0]), n+4, xi_1, field_length, 0, READ_ONLY), 
                        ("内存使用率: ", n+4, xi_2, f"{node_info_dict['Mem'][1]}%", n+4, xi_3, field_length, 0, READ_ONLY)
                        ]
                elements.extend(info)

                n=n+5
                elements.append(("磁盘: ", n, tab, "", n, xi_1, field_length, 0, HIDDEN))
                for disk in node_info_dict["Disk"]:
                    n=n+1
                    disk_info=[
                            ("挂载目录: ", n, tab*2, disk, n, xi_1, field_length, 0, READ_ONLY),
                            ("磁盘大小: ", n, xi_2, format_size(node_info_dict['Disk'][disk][0]), n, xi_3, field_length, 0, READ_ONLY), 
                            ("磁盘使用率: ", n, xi_4, f"{node_info_dict['Disk'][disk][1]}%", n, xi_5, field_length, 0, READ_ONLY)
                            ]
                    elements.extend(disk_info)

                n=n+1
                elements.append(("端口: ", n, tab, "", n, xi_1, field_length, 0, HIDDEN))
                for port in node_info_dict["Port"]:
                    n=n+1
                    port_info=[
                            ("Port: ", n, tab*2, port, n, xi_1, field_length, 0, READ_ONLY),
                            ("Pid: ", n, xi_2, f"{node_info_dict['Port'][port][0]}", n, xi_3, field_length, 0, READ_ONLY),
                            ("进程名称: ", n, xi_4, node_info_dict['Port'][port][1], n, xi_5, field_length, 0, READ_ONLY)
                            ] 
                    elements.extend(port_info)
            else:
                error_msg=node_info_dict["error_info"]
                elements.append((ip, n, 1, error_msg, n, xi_1, field_length, 0, READ_ONLY))
        elements.append(("", n+1, 1, "", n+1, xi_1, field_length, 0, HIDDEN))
        self.log.logger.debug(f"host info summary: {elements=}")
        code, _=self.d.mixedform(f"请确认集群主机信息:", elements=elements, cancel_label="返回")
        return code

    def init(self, title):
        """
        初始化过程
        """
        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            os.close(read_fd)
            with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)   #self.log_file, self.log_level, "graphical", g_file=wfile)
                self.log.logger.info("监测主机配置, 请稍后...\n")
                flag, connect_msg=self.connect_test(self.init_dict)
                if flag==1:
                    self.log.logger.error("主机信息配置有误, 请根据下方显示信息修改:")
                    for ip in connect_msg:
                        self.log.logger.info(f"{ip}:\t{connect_msg[ip]['msg']}")
                    os._exit(1)

                local_python3_file=self.conf_dict["location"].get("python3")
                status=super(graphics_deploy, self).init(self.init_dict, local_python3_file)
                if status is True:
                    self.log.logger.info("初始化完成\n")
                    self.log.logger.info("获取主机信息...")
                    all_host_info=self.get_host_msg(self.init_dict)
                    with open(host_info_file, "w", encoding="utf8") as f:
                        all_host_dict=self._to_init_dict(all_host_info)
                        json.dump(all_host_dict, f)
                    self.log.logger.info("主机信息已获取, 请查看")
                else:
                    self.log.logger.error(f"初始化失败: {status}")
                    os._exit(1)
            os._exit(0)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=30, width=180)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单")
            self.show_menu()
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试")
            self.show_menu()

        if exit_code==0:
            while True:
                result_code=self.show_init_info(title, host_info_file)
                if result_code==self.d.OK:
                    result_code=self.d.yesno("确认按照检测信息开始集群部署?")
                    if result_code==self.d.OK:
                        if self.generate_arch():
                            self.deploy("集群部署")
                        else:
                            break
                    else:
                        continue
                else:
                    break

    def install(self, title):
        self.log.logger.info("集群安装...\n")
        result=super(graphics_deploy, self).install(self.init_dict, self.arch_dict)
        if result:
            self.log.logger.info("集群安装完成")
        else:
            self.log.logger.error("集群安装失败")
        self.generate_info("file", self.install_stats_dict, stats_file=install_stats_file)

        return result

    def start(self, title):
        self.log.logger.info("集群启动...\n")
        result=super(graphics_deploy, self).start(self.init_dict, self.arch_dict)
        if result:
            self.log.logger.info("集群启动完成")
        else:
            self.log.logger.error("集群启动失败")
        self.generate_info("file", self.start_stats_dict, stats_file=start_stats_file)

        return result

    def update(self, title):
        """
        deploy中项目更新
        """
        self.log.logger.info("开始更新...")
        result=super(graphics_deploy, self).update([])
        if result:
            self.log.logger.info("更新完成")
        else:
            self.log.logger.error("更新失败")
        self.generate_info("file", self.update_stats_dict, stats_file=update_stats_file)
        return result

    def g_update(self, title):
        """
        图形化项目更新
        """
        pass

    def deploy(self, title):
        """
        install, start, update
        """

        stage_all=["install", "start", "update"]
        stage_method={
                "install": self.install, 
                "start": self.start, 
                "update": self.update
                }
        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            os.close(read_fd)
            with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)   
                for stage in stage_all:
                    if stage_method[stage](title):
                        continue
                    else:
                        self.log.logger.error(f"'{stage}'阶段执行失败")
                        os._exit(1)
            os._exit(0)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=30, width=180)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单")
            self.show_menu()
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试")
            self.show_menu()

        if exit_code==0:
            self.d.msgbox("集群部署完成, 将返回菜单")
            self.show_menu()
        else:
            self.d.msgbox("集群部署失败, 将返回菜单")
            self.show_menu()

    def cancel(self, msg):
        self.d.msgbox(f"取消{msg}")
        self.log.logger.info(f"退出{msg}")
        exit()

    def show_menu(self):
        while True:
            menu={
                    "1": "主机检测", 
                    "2": "集群部署", 
                    "3": "集群监控", 
                    "4": "项目更新"
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
                    self.init(menu[tag])
                if tag=="2":
                    self.deploy(menu[tag])
                if tag=="3":
                    self.monitor(menu[tag])
                if tag=="4":
                    self.g_update(menu[tag])
                self.d.infobox(f"{menu[tag]}完成, 将返回主菜单...")
                time.sleep(3)
            else:
                self.cancel("安装")

    def _install_dialog(self):
        """
        安装dialog
        """

        return True

    def show(self):
        if not self._install_dialog():
            print("Error: dialog安装失败, 请手动安装后再执行")
            sys.exit(1)

        introduction=dedent("""
            本程序主要用来自动部署项目集群. 
            部署过程将使用方向键或Tab键进行选择, 【enter】键用来确认.
            是否开始 ?
        """)

        self.log.logger.info("开始文本图形化部署")

        code=self.d.yesno(introduction, height=10, width=100, title="说明")

        if code==self.d.OK:
            self.show_menu()
        else:
            self.cancel("安装")

class platform_deploy(Deploy):
    '''平台安装'''

    def __init__(self, conf_file, init_file, arch_file, project_file):
        super(platform_deploy, self).__init__(conf_file, init_file, arch_file, project_file)
        self.log=Logger({"platform": log_platform_level, "file": log_file_level}, 
                log_file=log_file, logger_name="platform", 
                project_id=self.project_id
                )

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
            sys.exit()

        local_python3_file=self.conf_dict["location"].get("python3")
        status=super(platform_deploy, self).init(init_dict, local_python3_file)
        if status:
            self.log.logger.info("初始化完成\n")
            self.log.logger.info("获取主机信息...")
            all_host_info=self.get_host_msg(init_dict)
            self.init_stats_dict["host_info"]=self._to_init_dict(all_host_info)
        else:
            self.log.logger.error(f"初始化失败: {status}")
        # 信息发送平台
        self.generate_info("platform", self.init_stats_dict)

    def install(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群安装...\n")
        result=super(platform_deploy, self).install(init_dict, arch_dict)
        if result:
            self.log.logger.info("集群安装完成")
        else:
            self.log.logger.error("集群安装失败")
        self.generate_info("platform", self.install_stats_dict)
        return result

    def start(self):
        with open(self.arch_file, "r", encoding="utf8") as arch_f, open(self.init_file, "r", encoding="utf8") as init_f:
            init_dict=json.load(init_f)
            arch_dict=json.load(arch_f)
        self.log.logger.info("集群启动...\n")
        result=super(platform_deploy, self).start(init_dict, arch_dict)
        if result:
            self.log.logger.info("集群启动完成")
        else:
            self.log.logger.error("集群启动失败")
        self.generate_info("platform", self.start_stats_dict)
        return result

    def update(self, package_list=[]):
        self.log.logger.info("开始更新...")
        result=super(platform_deploy, self).update(package_list)
        if result:
            self.log.logger.info("更新完成")
        else:
            self.log.logger.error("更新失败")
        self.generate_info("platform", self.update_stats_dict)
        return result

    def deploy(self):
        """
        install, start, update
        """

        stage_all=["install", "start", "update"]
        stage_method={
                "install": self.install, 
                "start": self.start, 
                "update": self.update
                }
        for stage in stage_all:
            if stage_method[stage]():
                continue
            else:
                self.log.logger.error(f"'{stage}'阶段执行失败")
                sys.exit(1)

if __name__ == "__main__":
    main()
