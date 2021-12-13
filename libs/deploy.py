#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 17:37:47
# sky

import locale, json, os, time, sys, tarfile, math, shutil, copy, psutil, socket
from libs.env import logs_dir, log_file, log_file_level, log_console_level, log_platform_level, log_graphics_level, \
        remote_python_transfer_dir, remote_python_install_dir,  remote_python_exec, remote_python_dir, \
        remote_code_dir, remote_pkgs_dir, ext_dir, autodep_dir, backup_dir, \
        interface, test_mode, resource_verify_mode, backup_abs_file_format, rollback_abs_file_format, backup_soft_type, \
        host_info_file, hosts_file, local_file, init_stats_file, install_stats_file, start_stats_file, update_stats_file, run_stats_file, \
        rollback_dir, rollback_version_file, \
        g_term_rows, g_term_cols, \
        tool_service_code, portless_service_code, \
        located_dir_name, located_dir_link, autocheck_dst, report_dir, report_file_list, \
        init_file, arch_file, stand_alone_file, project_file, update_init_file, update_arch_file, start_file, stop_file, deploy_file, ext_file, localization_file, backup_version_file, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code, \
        local_license_path, node_license_path, \
        localization_soft_port, localization_test_soft

for dir_ in autodep_dir:
    if not os.path.exists(dir_):
        os.makedirs(dir_, exist_ok=1)

from textwrap import dedent
from libs.common import Logger, post_info, format_size, port_connect, exec_command, pkg_install
from libs.remote import ssh, soft

if test_mode:                       # 是否启用测试模式: 代码文件在install, run, start, stop, update阶段重复传输
    trans_files_dict={
            "lib_file": ["./libs/common.py", f"{remote_code_dir}/libs/common.py"], 
            "env_file": ["./libs/env.py", f"{remote_code_dir}/libs/env.py"]
            }
else:
    trans_files_dict={}

class Deploy(object):
    '''集群部署
    '''
    def __init__(self):
        self.ssh_client=ssh()

    def read_config(self, config_name_list):
        """从默认配置文件中读取配置信息 
        config_name_list: ["project", "init", "arch"]

        return:
            False, str  //  True, [project_dict, init_dict, arch_dict]
        """
        config_dict_list=[]
        for config in config_name_list:
            # 判断配置名称
            if config=="init":
                config_file=init_file
            elif config=="arch":
                config_file=arch_file
            elif config=="start":
                config_file=start_file
            elif config=="stop":
                config_file=stop_file
            elif config=="host":
                config_file=host_info_file
            elif config=="update_arch":
                config_file=update_arch_file
            elif config=="update_init":
                config_file=update_init_file
            #elif config=="check":
            #    config_file=check_file
            elif config=="project":
                config_file=project_file
            elif config=="localization":
                config_file=localization_file
            elif config=="backup_version":
                config_file=backup_version_file
            elif config=="rollback_version":
                config_file=rollback_version_file
            elif config=="ext":
                config_file=ext_file
            elif config=="local":
                config_file=local_file
            elif config=="hosts":
                config_file=hosts_file
            elif config=="stand_alone":
                config_file=stand_alone_file
            result, config_json=self.read_json(config_file)
            if result:
                config_dict_list.append(config_json)
            else:
                return False, f"{config}: {config_json[config_file]}"
        else:
            return True, config_dict_list

    def read_json(self, config_file):
        """从josn中读取文件
        """
        try: 
            with open(config_file, "r", encoding="utf8") as f:
                config_json=json.load(f)
            return True, config_json
        except Exception as e:
            return False, {config_file: str(e)}

    def write_config(self, dict_, file_):
        """将dict以json格式写入文件
        """
        try: 
            with open(file_, "w", encoding="utf8") as f:
                json.dump(dict_, f, ensure_ascii=False, indent=2)
            return True, ""
        except Exception as e:
            return False, str(e)

    def get_host_msg(self, init_dict):
        """获取主机信息
        return:
            get_result: bool 
            all_host_info: { "node": {}, }
        """
        all_host_info_dict={}
        get_result=True
        get_msg_py="./bin/get_host_info.py"
        self.log.logger.info("获取主机信息中, 请稍后...")
        for node in init_dict:
            port=init_dict[node].get("port")
            if port==0:
                local_flag=True
            else:
                local_flag=False

            remote_file=f"{remote_code_dir}/{get_msg_py.split('/')[-1]}"
            result, msg=self.ssh_client.scp(get_msg_py, remote_file, node, port)
            if result:
                get_msg_command=f"{remote_python_exec} {remote_file}"
                self.log.logger.info(f"获取{node}主机信息...")
                self.log.logger.debug(f"{get_msg_command=}")
                obj, status=self.ssh_client.exec(get_msg_command, node, port)
                result_code=self.ssh_client.returncode(obj, local_flag)
                msg=status[1].read().strip()
                if isinstance(msg, bytes):
                    node_info=msg.decode("utf8")
                else:
                    node_info=msg
                if result_code==normal_code:
                    self.log.logger.info(f"{node}已获取")
                    node_info=node_info[node_info.index("{"):]      # 将获取的环境检测信息转为发送平台的dict
                    node_info=json.loads(node_info)
                else:
                    self.log.logger.error(f"{node}获取失败: {msg}")
                    get_result=False
                all_host_info_dict[node]=node_info
            else:
                get_result=False
        return get_result, all_host_info_dict

    def json_to_init_dict_bak(self, all_host_info):
        """将获取的环境检测信息转为发送平台的dict
        """
        all_host_dict={}
        for node in all_host_info:
            if all_host_info[node][0] == normal_code:
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
        """信息生成: 平台, 文件
        """
        if mode=="platform_info":
            info="状态信息已发送至平台\n"
            error_info="状态信息发送失败\n"
            file_=None
        if mode=="platform_check":
            info="巡检报告已发送至平台\n"
            error_info="巡检报告发送失败\n"
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
        """测试init.json的账号, 密码, 端口
        return:
            result,                       
            connect_msg={
            "status": N, 
            "msg": msg
            }
        """
        ssh_client=ssh()
        connect_test_result={}
        result=True
        for node in init_dict:
            port=init_dict[node].get("port")
            password=init_dict[node].get("root_password")
            status, msg=ssh_client.password_conn(node, port, password)
            if status != normal_code:
                result=False
            connect_test_result[node]={
                    "result": status, 
                    "err_msg": msg
                    }
        return result, connect_test_result

    def str_to_title(self, str_, level):
        """将字符串转为标题字符串
        """
        N=3
        if level==1:
            character="#"
        elif level==2:
            character="*"
        elif level==3:
            character="-"
        else:
            character=""

        characters=f"{character}" * N
        str_=f"{characters}{str_}{characters}"
        return str_

    def _format_size(self, size):
        """将字符串大小转为数字
        """
        if size.isdigit():
            return int(size)
        elif size[-2:].isalpha():
            if size[-2:].lower() == "gb":
                return int(size[:-2]) * 1024 * 1024 * 1024
            elif size[-2:].lower() == "mb":
                return int(size[:-2]) * 1024 * 1024
        elif size[-1].isalpha():
            if size[-1].lower() == "g":
                return int(size[:-1]) * 1024 * 1024 * 1024
            elif size[-1].lower() == "m":
                return int(size[:-1]) * 1024 * 1024
            
    def _get_soft_weights(self, arch_dict, node, softname):
        """获取单个软件权重(内存)
        return mem(byte), cpu
        """
        if softname=="elasticsearch":
            mem=arch_dict[node]["elasticsearch_info"]["jvm_mem"]
        elif softname=="mysql":
            mem=arch_dict[node]["mysql_info"]["db_info"]["innodb_mem"]
        elif softname=="nginx" or softname=="dps":
            mem="1G"
            #self.arch_dict[node]["nginx_info"]["worker_processes"]=softname_cpu
        elif softname=="rabbitmq":
            mem=arch_dict[node]["rabbitmq_info"]["erlang_mem"]
        elif softname=="redis":
            mem=arch_dict[node]["redis_info"]["db_info"]["redis_mem"]
        elif softname=="dch":
            mem=arch_dict[node]["dch_info"]["db_info"]["dch_mem"]
        elif softname=="rocketmq":
            mem1=arch_dict[node]["rocketmq_info"]["namesrv_mem"]
            mem2=arch_dict[node]["rocketmq_info"]["broker_mem"]
            mem=str(self._format_size(mem1)+self._format_size(mem2))
        elif softname=="tomcat":
            mem=arch_dict[node]["tomcat_info"]["jvm_mem"]
        elif softname=="nacos":
            mem=arch_dict[node]["nacos_info"]["jvm_mem"]
        elif softname.startswith("program"):
            mem=arch_dict[node][f"{softname}_info"].get("jvm_mem")
            if mem is None:     # sql文件
                mem="0G"
        else:
            mem="0G"
        cpu=1
        return self._format_size(mem), cpu

    def _get_soft_port_list(self, arch_dict, node, softname):
        """获取单个软件的端口列表
            return:
                port_list:
                    [11, 22]    - 软件端口列表
                    [0]         - glusterfs-client, autocheck等无端口有服务软件
                    [1]         - 工具类无端口软件
        """
        port_list=[]
        if softname=="elasticsearch":
            for port_name in arch_dict[node]["elasticsearch_info"]["port"]:
                port_list.append(arch_dict[node]["elasticsearch_info"]["port"][port_name])
        elif softname=="mysql":
            port_list.append(arch_dict[node]["mysql_info"]["db_info"]["mysql_port"])
        elif softname=="nginx":
            for port in arch_dict[node]["nginx_info"]["vhosts_info"]:
                port_list.append(int(port))
        elif softname=="dps":
            for port in arch_dict[node]["dps_info"]["vhosts_info"]:
                port_list.append(int(port))
        elif softname=="rabbitmq":
            for port_name in arch_dict[node]["rabbitmq_info"]["port"]:
                port_list.append(arch_dict[node]["rabbitmq_info"]["port"][port_name])
        elif softname=="redis":
            port_list.append(arch_dict[node]["redis_info"]["db_info"]["redis_port"])
            if arch_dict[node]["redis_info"].get("sentinel_info"):
                port_list.append(arch_dict[node]["redis_info"]["sentinel_info"]["sentinel_port"])
        elif softname=="dch":
            port_list.append(arch_dict[node]["dch_info"]["db_info"]["dch_port"])
            if arch_dict[node]["dch_info"].get("sentinel_info"):
                port_list.append(arch_dict[node]["dch_info"]["sentinel_info"]["sentinel_port"])
        elif softname=="glusterfs-server":
            #for port_name in arch_dict[node]["glusterfs-server_info"]["port"]:
            #    port_list.append(arch_dict[node]["glusterfs-server_info"]["port"][port_name])
            port_list.append(arch_dict[node]["glusterfs-server_info"]["port"]["volume_port"])
        elif softname=="rocketmq":
            for port_name in arch_dict[node]["rocketmq_info"]["port"]:
                port_list.append(arch_dict[node]["rocketmq_info"]["port"][port_name])
        elif softname=="tomcat":
            for port_name in arch_dict[node]["tomcat_info"]["port"]:
                port_list.append(arch_dict[node]["tomcat_info"]["port"][port_name])
        elif softname.startswith("program"):
            jvm_port=arch_dict[node][f"{softname}_info"].get("port")
            if jvm_port is None:
                port_list.append(tool_service_code)
            else:
                port_list.append(jvm_port)
        elif softname=="nacos":
            port_list.append(arch_dict[node]["nacos_info"]["web_port"])
            if arch_dict[node]["nacos_info"].get("cluster_info") is not None:
                port_list.append(arch_dict[node]["nacos_info"]["cluster_info"]["raft_port"])
        elif softname=="autocheck" or softname=="glusterfs-client" or softname=="keepalived":
            port_list.append(portless_service_code)
        elif softname=="dameng" or softname=="shentong" or softname=="kingbase":
            port_list.append(arch_dict[node][f"{softname}_info"]["db_port"])
        else:
            port_list.append(tool_service_code)
        return port_list

    def _get_max_disk_name(self, host_info_dict):
        """获取每个ip剩余空间最大的磁盘目录名称
        return { 
            ip: max_disk_name, 
            ip: max_disk_name, 
        }
        """
        max_disk_dict={}
        for ip in host_info_dict:
            disk_sorted=sorted(host_info_dict[ip]["Disk"].items(), key=lambda item:item[1][0]*(100-item[1][1]), reverse = True)
            max_disk_dict[ip]=disk_sorted[0][0]
        return max_disk_dict

    def _get_backup_file(self, ip, port, backup_version, softname):
        """获取备份文件
        return:
            True, filename|err
        """
        src_file=backup_abs_file_format.format(backup_dir=backup_dir, backup_version=backup_version, softname=softname)
        dst_file=rollback_abs_file_format.format(rollback_dir=rollback_dir, backup_version=backup_version, softname=softname)
        result, msg=self.ssh_client.get(ip, port, "root", src_file, dst_file)
        return result, msg

    def get_soft_info(self, softname, ext_dict, info_type):
        """根据软件名称获取对应软件的信息
        softname: 
        ext_dict:
        info_type: file|py|type

        return:
            ../ext/soft-version.tar.gz    # file
            ./bin/soft.py                 # py
            program                       # type
        """
        if softname.lower().startswith("program"):
            type_name, product_name, module_name=softname.split("_")
            if info_type=="file":
                file_name=ext_dict[type_name][product_name][module_name]["file"]
                if file_name.startswith("/"):
                    soft_file=file_name
                else:
                    soft_file=f"{ext_dir}/{product_name}/{file_name}"
                soft_info_str=soft_file
            elif info_type=="py":
                py_name=ext_dict[type_name][product_name][module_name]["py"]
                soft_py=f"./bin/{py_name}"
                soft_info_str=soft_py
            elif info_type=="type":
                soft_type=ext_dict[type_name][product_name][module_name]["type"]
                soft_info_str=soft_type
        else: 
            if info_type=="file":
                file_name=ext_dict[softname].get("file")
                if file_name is not None:
                    if file_name.startswith("/"):
                        soft_file=file_name
                    else:
                        soft_file=f"{ext_dir}/{file_name}"
                else:
                    soft_file=file_name
                soft_info_str=soft_file
            elif info_type=="py":
                py_name=ext_dict[softname]["py"]
                soft_py=f"./bin/{py_name}"
                soft_info_str=soft_py
            elif info_type=="type":
                soft_type=ext_dict[softname]["type"]
                soft_info_str=soft_type
        return soft_info_str

    def set_ext_softname(self, ext_dict, softname, filename):
        """设置ext内软件的安装包名称
        return:
            ext_dict
        """
        if softname.lower().startswith("program"):
            type_name, product_name, module_name=softname.split("_")
            ext_dict[type_name][product_name][module_name]["file"]=filename
        else:
            ext_dict[softname]["file"]=filename
        return ext_dict

    def rollback_arch_file(self):
        """将版本备份的文件(arch.json)回滚至config目录: 还原原程序配置, 删除新加的程序软件
        """
        result, config_list=self.read_config(["rollback_version", "arch", "ext"])
        if result:
            rollback_version, arch_dict, ext_dict=config_list
            backup_version=self.trans_date_to_backup_version(rollback_version)
            arch_backup_file=f"{rollback_dir}/{backup_version}/{arch_file.split('/')[-1]}"
            result, arch_backup_dict=self.read_json(arch_backup_file)
            if result:
                arch_rollback_dict=copy.deepcopy(arch_dict)
                for node in arch_dict:
                    for softname in arch_dict[node]["software"]:
                        soft_type=self.get_soft_info(softname, ext_dict, "type")
                        if soft_type in backup_soft_type:
                            if node in arch_backup_dict:
                                if softname in arch_backup_dict[node]["software"]:
                                    arch_rollback_dict[node][f"{softname}_info"]=arch_backup_dict[node].get(f"{softname}_info")
                                else:
                                    arch_rollback_dict[node]["software"].remove(softname)
                                    if arch_dict[node].get(f"{softname}_info") is not None:
                                        arch_rollback_dict[node].pop(f"{softname}_info")
                            else:
                                arch_rollback_dict[node]["software"].remove(softname)
                result, msg=self.write_config(arch_rollback_dict, arch_file)
                if result:
                    self.log.logger.info("arch_file回滚完成")
                    return True, {"result": "ok"}
                else:
                    return False, {"result": msg}
            else:
                return False, {"result": arch_backup_dict}
        else:
            return False, {"result": config_list}

    def rollback_update_file(self):
        """将版本备份的文件(ext.json, update_arch.json, init.json)回滚至config目录
        return:
            True, ""|err
        """
        config_list=[update_arch_file, ext_file]
        result, msg=self.rollback_file(config_list)
        return result, msg

    def rollback_file(self, config_list):
        """文件拷贝
        """
        try:
            result, config=self.read_config(["rollback_version"])
            if result:
                rollback_version=config[0]
                backup_version=self.trans_date_to_backup_version(rollback_version)
                for config_file in config_list:
                    src_file=f"{rollback_dir}/{backup_version}/{config_file.split('/')[-1]}"
                    self.log.logger.debug(f"cp {src_file} {config_file}")
                    shutil.copyfile(src_file, config_file)
                return True, ""
            else:
                return False, config
        except Exception as e:
            return False, str(e)

    def node_adapter_ip(self, arch_dict, host_info_dict, localization_dict):
        """根据模板中各节点安装软件的权重和 对应 集群中各节点权重和(排序对应), 并将ip/located赋值给node配置
        return:
            True|False,
            arch_dict|non_resource_dict
        """
        self.log.logger.info("自动匹配node和ip")

        # 获取未使用ip的node和ip, 且绑定指定ip(国产化软件ip)到node
        self.log.logger.debug("将国产化软件ip绑定到node")
        arch_no_ip_list=[]
        host_info_no_ip_list=list(host_info_dict.keys())
        for node in arch_dict:
            if localization_dict.get(node) is not None and localization_dict[node].get("ip") is not None:
                ip=localization_dict[node]["ip"]
                arch_dict[node]["ip"]=ip
                host_info_no_ip_list.remove(ip)
                # softname_info合并到arch_dict
                for softname in localization_dict[node]["software"]:
                    if softname != "autocheck":
                        arch_dict[node][f"{softname}_info"].update(localization_dict[node][f"{softname}_info"])
                self.log.logger.debug(f"{ip} <--> {node}")
            else:
                arch_no_ip_list.append(node)
        self.log.logger.debug(f"{arch_no_ip_list=}")
        self.log.logger.debug(f"{host_info_no_ip_list=}")

        localization_node_weights_dict={}
        localization_ip_weights_dict={}
        node_weights_dict={}
        ip_weights_dict={}
        self.log.logger.debug("获取节点权重: [node_mem_weights, node_cpu_weights]")
        #for node in arch_no_ip_list:
        for node in arch_dict:
            node_mem_weights=0
            node_cpu_weights=0
            for softname in arch_dict[node]["software"]:
                mem, cpu=self._get_soft_weights(arch_dict, node, softname)
                node_mem_weights=node_mem_weights+mem
                node_cpu_weights=node_cpu_weights+cpu
            else:
                if node in arch_no_ip_list:
                    localization_node_weights_dict[node]=[node_mem_weights, node_cpu_weights]
                node_weights_dict[node]=[node_mem_weights, node_cpu_weights]
        self.log.logger.debug(f"{node_weights_dict=}, {localization_node_weights_dict=}")

        self.log.logger.debug("获取ip权重: [ip_mem_weights, ip_cpu_weights]")
        #for ip in host_info_no_ip_list:
        for ip in host_info_dict:
            ip_mem=host_info_dict[ip]["Mem"][0]
            ip_cpu=host_info_dict[ip]["CPU"][0]
            if ip in host_info_no_ip_list:
               localization_ip_weights_dict[ip]=[ip_mem, ip_cpu]
            ip_weights_dict[ip]=[ip_mem, ip_cpu]
        self.log.logger.debug(f"{ip_weights_dict=}")

        self.log.logger.debug("node与ip适配:")
        # 节点与ip权重排序
        localization_ip_weights_sort=[ x for x, y in sorted(localization_ip_weights_dict.items(), key=lambda item:item[1][0])]
        localization_node_weights_sort=[ x for x, y in sorted(localization_node_weights_dict.items(), key=lambda item:item[1][0])]

        # 根据排序对应, 赋值
        for node, ip in zip(localization_node_weights_sort, localization_ip_weights_sort):
            arch_dict[node]["ip"]=ip
            self.log.logger.debug(f"{ip} <--> {node}")

        self.log.logger.info("选择最大磁盘:")
        max_disk_dict=self._get_max_disk_name(host_info_dict)
        for node in arch_dict:
            max_disk_dir=f"{max_disk_dict[arch_dict[node]['ip']]}"
            if max_disk_dir.endswith("/"):
                located_dir=f"{max_disk_dir}{located_dir_name}"
            else:
                located_dir=f"{max_disk_dir}/{located_dir_name}"
            arch_dict[node]["located"]=located_dir
            self.log.logger.debug(f"{node} located_dir <--> {located_dir}")

        ## 资源大小验证
        non_resource_dict={}
        non_resource_flag=False
        if resource_verify_mode:
            self.log.logger.debug("资源校验...")
            for node in arch_dict:
                ip=arch_dict[node]["ip"]
                self.log.logger.debug(f"{node} check {ip}")
                mem=ip_weights_dict[ip][0]-node_weights_dict[node][0]
                cpu=ip_weights_dict[ip][1]-node_weights_dict[node][1]
                if mem < 0:
                    non_resource_flag=True
                    if non_resource_dict.get(ip) is None:
                        non_resource_dict[ip]={}
                    non_resource_dict[ip]["Mem"]=node_weights_dict[node][0]
                if cpu < 0:
                    non_resource_flag=True
                    if non_resource_dict.get(ip) is None:
                        non_resource_dict[ip]={}
                    non_resource_dict[ip]["CPU"]=node_weights_dict[node][1]
            self.log.logger.debug("资源校验完成")
        else:
            self.log.logger.warning("资源校验未开启")

        if non_resource_flag:
            return False, non_resource_dict
        else:
            return True, arch_dict

    def account_verifi(self, init_dict):
        """init_dict格式校验
        return:
            True: not_pass_init_dict: {
                    "ip": "str"
                    }
        """
        for ip in init_dict:
            pass
        return True, {}

    def remote_exec(self, ip, port, softname, remote_py_file, action, trans_files_dict, args_dict):
        """远程执行相关软件
        return
            obj: 
            status: stdin, stdout, stderr
        """
        for trans_file in trans_files_dict:
            src, dst=trans_files_dict[trans_file]
            self.log.logger.debug(f"传输文件: {trans_file}, {src=}, {dst=}")
            self.ssh_client.scp(src, dst, ip, port)

        soft_control=soft(ip, port, self.ssh_client)
        if action=="init":
            obj, status=soft_control.init(remote_py_file)
        elif action=="install":
            if trans_files_dict.get("pkg_file"):
                args_dict["pkg_file"]=trans_files_dict["pkg_file"][1]
            obj, status=soft_control.install(remote_py_file, softname, args_dict)
        elif action=="run":
            obj, status=soft_control.run(remote_py_file, softname, args_dict)
        elif action=="start":
            obj, status=soft_control.start(remote_py_file, softname, args_dict)
        elif action=="stop":
            obj, status=soft_control.stop(remote_py_file, softname, args_dict)
        elif action=="sendmail":
            obj, status=soft_control.sendmail(remote_py_file, args_dict)
        elif action=="monitor":
            obj, status=soft_control.monitor(remote_py_file, softname, args_dict)
        elif action=="backup":
            obj, status=soft_control.backup(remote_py_file, softname, args_dict)
        elif action=="test":
            obj, status=soft_control.test(remote_py_file, softname, args_dict)
        return obj, status

    def nodes_control(self, control_dict, action, action_msg, init_dict, arch_dict, ext_dict):
        """对control_dict中节点的软件执行action操作
            control_dict={
                "node1":["soft1", "soft2"], 
                "node2":["soft1", "soft2"]
            }

            return:
                control_result: True|False              # 整体运行结果
                control_stats_dict: {                   # 运行结果
                    "node1":{
                        "soft1": code
                        "soft2": code
                        }
                }
        """
        control_result=True
        control_stats_dict={}
        self.log.logger.info(f"{action_msg}节点: {list(control_dict.keys())}")
        for node in control_dict:
            self.log.logger.info(self.str_to_title(f"{node}节点{action_msg}", 3))
            control_stats_dict[node]={}
            ip=arch_dict[node]["ip"]
            port=init_dict[arch_dict[node]["ip"]]["port"]
            self.log.logger.info(f"{action_msg}软件: {control_dict[node]}")
            for softname in control_dict[node]:
                self.log.logger.info(f"{softname}{action_msg}...")
                control_trans_files_dict=copy.deepcopy(trans_files_dict)
                py_file=self.get_soft_info(softname, ext_dict, "py")
                remote_py_file=f"{remote_code_dir}/{py_file.split('/')[-1]}"
                if test_mode or action=="install" or action=="test":
                    control_trans_files_dict.update(
                            {
                                "py_file": [py_file, remote_py_file]
                                }
                            )
                pkg_file=self.get_soft_info(softname, ext_dict, "file")
                if action=="install" and pkg_file is not None:          # install阶段无pkg文件的情况
                    remote_pkg_file=f"{remote_pkgs_dir}/{pkg_file.split('/')[-1]}"
                    control_trans_files_dict.update(
                            {
                                "pkg_file": [pkg_file, remote_pkg_file]
                                }
                            )
                obj, status=self.remote_exec(ip, port, softname, remote_py_file, action, control_trans_files_dict, arch_dict[node])
                for line in status[1]:
                    self.log.logger.info(line.strip())
                if port==0:
                    local_flag=True
                else:
                    local_flag=False
                result_code=self.ssh_client.returncode(obj, local_flag)
                if result_code==normal_code:
                    self.log.logger.info(f"{softname}{action_msg}完成")
                elif result_code==activated_code:
                    self.log.logger.warning(f"{softname}运行中")
                elif result_code==stopped_code:
                    self.log.logger.warning(f"{softname}未启动")
                else:
                    self.log.logger.error(f"{softname}{action_msg}失败")
                    control_result=False
                control_stats_dict[node][softname]=result_code
        return control_result, control_stats_dict

    def remote_init_bak(self, init_dict, ext_dict):
        """主机环境初始化
            * 生成秘钥
            * 免密码登录
            * 关闭firewalld
            * 关闭selinux
            * 配置Python3环境
            * nproc nofile
        """
        if self.ssh_client.gen_keys():
            self.log.logger.info("本机生成密钥对")
        else:
            self.log.logger.info("本机已存在密钥对")

        # 初始化
        init_result=True
        init_stats_dict={}
        self.log.logger.info(f"初始化主机: {list(init_dict.keys())}")
        for node in init_dict:
            self.log.logger.info(self.str_to_title(f"主机{node}环境初始化", 3))
            stats_value=True
            stats_message=""
            try:
                port=init_dict[node].get("port")
                password=init_dict[node].get("root_password")

                self.ssh_client.free_pass_set(node, port, password)
                result, msg=self.ssh_client.key_conn(node, port)
                if result:
                    self.log.logger.info(f"免密码登录设置完成")
                else: 
                    self.log.logger.error(f"免密码登录失败: {msg}")
                    msg=Exception(msg)
                    raise msg
                
                # 传输Python
                local_python3_file=self.get_soft_info("python3", ext_dict, "file")
                remote_python3_file=f"{remote_python_transfer_dir}/{local_python3_file.split('/')[-1]}"
                self.log.logger.debug(f"传输Python安装包...")
                self.ssh_client.scp(node, port, "root", local_python3_file, remote_python3_file)

                command=f"tar -xf {remote_python3_file} -C {remote_python_install_dir}"
                self.log.logger.debug(f"配置Python环境")
                status=self.ssh_client.exec(node, port, command)
                if status[1].channel.recv_exit_status() != 0:
                    error_info=f"Python3安装报错, 进程退出: {status[2].read().decode('utf8')}"
                    self.log.logger.error(error_info)
                    init_result=False
                    stats_value=False
                    stats_message=error_info
                    break
                else:
                    self.log.logger.info(f"配置Python3环境完成")

                # 执行init.py
                init_py=self.get_soft_info("init", ext_dict, "py")
                remote_py_file=f"{remote_code_dir}/{init_py.split('/')[-1]}"
                trans_files_dict={
                        "lib_file": ["./libs/common.py", f"{remote_code_dir}/libs/common.py"],
                        "env_file": ["./libs/env.py", f"{remote_code_dir}/libs/env.py"],
                        "py_file": [init_py, remote_py_file]
                        }
                status=self.remote_exec(node, port, "init", remote_py_file, "init", trans_files_dict, None)

                for line in status[1]:
                    self.log.logger.info(line.strip())
                if status[1].channel.recv_exit_status() != normal_code:
                    error_info=f"{node}远程初始化失败"
                    self.log.logger.error(error_info)
                    init_result=False
                    stats_value=False
                    stats_message=error_info
                    break
                else:
                    self.log.logger.info(f"{node}远程初始化完成")
            except Exception as e:
                init_result=False
                stats_value=False
                stats_message=str(e)

            init_stats_dict[node]={
                    "stats_value": stats_value, 
                    "stats_message": stats_message
                    }
        return init_result, init_stats_dict

    def install_python(self, local_python3_file, remote_python3_file, node, port):
        """本地/远程安装python
        """
        python_result=True
        msg=""
        self.log.logger.info(f"传输Python安装包...")
        result, info=self.ssh_client.scp(local_python3_file, remote_python3_file, ip=node, port=port)
        if result:
            self.log.logger.info(f"配置Python环境")
            command=f"tar -xf {remote_python3_file} -C {remote_python_install_dir} && echo 'export LD_LIBRARY_PATH={remote_python_dir}/lib:$LD_LIBRARY_PATH' >> /etc/profile.d/python.sh"
            obj, status=self.ssh_client.exec(command, ip=node, port=port)
            if port==0:
                local_flag=True
            else:
                local_flag=False
            if self.ssh_client.returncode(obj, local_flag)!=0:
                err=status[2].read().strip()
                if isinstance(err, bytes):
                    err_msg=err.decode('utf8')
                else:
                    err_msg=err
                msg=f"Python解压报错, 进程退出: {err_msg}"
                python_result=False
        else:
            msg=f"Python安装包传输失败: {info}"
            python_result=False
        return python_result, msg

    def init(self, init_dict, ext_dict, local_flag):
        """主机环境初始化
            * 生成秘钥
            * 免密码登录
            * 关闭firewalld
            * 关闭selinux
            * 配置Python3环境
            * exec init.py
        return:
            init_result: bool    # 执行结果
            init_stats_dict:
                {
                }
        """
        if not local_flag:
            if self.ssh_client.gen_keys():
                self.log.logger.info("本机生成密钥对")
            else:
                self.log.logger.info("本机已存在密钥对")

        # 初始化
        init_result=True
        init_stats_dict={}
        self.log.logger.info(f"初始化主机: {list(init_dict.keys())}")
        for node in init_dict:
            self.log.logger.info(self.str_to_title(f"主机{node}环境初始化", 3))
            stats_value=True
            stats_message=""
            try:
                if local_flag:
                    port=0
                else:
                    port=init_dict[node].get("port")
                    password=init_dict[node].get("root_password")

                    self.ssh_client.free_pass_set(node, port, password)
                    result, msg=self.ssh_client.key_conn(node, port)
                    if result:
                        self.log.logger.info(f"免密码登录设置完成")
                    else: 
                        self.log.logger.error(f"免密码登录失败: {msg}")
                
                # 安装Python
                local_python3_file=self.get_soft_info("python3", ext_dict, "file")
                remote_python3_file=f"{remote_python_transfer_dir}/{local_python3_file.split('/')[-1]}"
                result, err_msg=self.install_python(local_python3_file, remote_python3_file, node, port)
                if result:
                    self.log.logger.info(f"配置Python3环境完成")
                else:
                    err_msg=Exception(err_msg)
                    raise msg

                # 执行init.py
                init_py=self.get_soft_info("init", ext_dict, "py")
                remote_py_file=f"{remote_code_dir}/{init_py.split('/')[-1]}"
                trans_files_dict={
                        "lib_file": ["./libs/common.py", f"{remote_code_dir}/libs/common.py"],
                        "env_file": ["./libs/env.py", f"{remote_code_dir}/libs/env.py"],
                        "py_file": [init_py, remote_py_file]
                        }
                obj, status=self.remote_exec(node, port, "init", remote_py_file, "init", trans_files_dict, None)

                for line in status[1]:
                    self.log.logger.info(line.strip())
                if self.ssh_client.returncode(obj, local_flag)!=normal_code:
                    error_info=f"{node}初始化失败"
                    err_msg=Exception(err_msg)
                    raise msg
                else:
                    self.log.logger.info(f"{node}初始化完成")
            except Exception as e:
                init_result=False
                stats_value=False
                stats_message=str(e)
                self.log.logger.error(stats_message)

            init_stats_dict[node]={
                    "stats_value": stats_value, 
                    "stats_message": stats_message
                    }
        return init_result, init_stats_dict

    def localization_test(self, init_dict, ext_dict, localization_dict):
        """国产化软件配置测试
        return 
            localization_stats_dict={
                "node1":
                    "soft1": result_code
            }
        """
        # 构建control_dict并去掉autocheck信息
        control_dict={}
        for node in localization_dict:
            for softname in localization_dict[node]["software"]:
                if softname in localization_test_soft:
                    if control_dict.get(node) is None:
                        control_dict[node]=[]
                    control_dict[node].append(softname)

        #autocheck_name="autocheck"
        #for node in localization_dict:
        #    if [autocheck_name] == localization_dict[node]["software"]:
        #        continue
        #    else:
        #        if autocheck_name in localization_dict[node]["software"]:
        #            localization_dict[node]["software"].remove(autocheck_name)
        #        control_dict[node]=localization_dict[node]["software"]

        localization_result, localization_stats_dict=self.nodes_control(control_dict, "test", "配置信息检测", \
                init_dict, localization_dict, ext_dict)
        return localization_result, localization_stats_dict

    def install(self, init_dict, arch_dict, ext_dict, hosts_list):
        """软件安装
        para:
            hosts_list: ["ip node", "ip node"]
        return:
            install_stats_dict={
                "node1":{
                    "soft1": True|False
                }
            }
        """
        # 为主机域名配置添加参数
        for node in arch_dict:
            arch_dict[node]["software"].insert(0, "set_hosts")
            arch_dict[node]["hosts_info"]={}
            arch_dict[node]["hosts_info"]["hostname"]=node
            arch_dict[node]["hosts_info"]["hosts"]=hosts_list

        # 构造需要启动的节点及软件结构
        control_dict={}
        for node in arch_dict:
            control_dict[node]=arch_dict[node]["software"]

        install_result, install_stats_dict=self.nodes_control(control_dict, "install", "安装", \
                init_dict, arch_dict, ext_dict)

        return install_result, install_stats_dict

    def run(self, init_dict, arch_dict, ext_dict):
        """按类别, 启动软件并初始化

        return:
            run_result: True|False
            run_stats_dict={
                "node1": {
                    "soft1": code
                }
            }
        """
        # 构造需要启动的节点及软件结构
        control_dict={}
        for node in arch_dict:
            control_dict[node]=arch_dict[node]["software"]
        soft_type_dict=self._divide_service(control_dict, ext_dict)

        run_result=True
        run_stats_dict={}
        for soft_type in soft_type_dict:
            if len(soft_type_dict[soft_type]) != 0:
                self.log.logger.info(self.str_to_title(f"{soft_type}服务运行", 2))
                run_result, type_stats_dict=self.nodes_control(soft_type_dict[soft_type], "run", "运行", init_dict, arch_dict, ext_dict)
                run_stats_dict[soft_type]=type_stats_dict
                if run_result:
                    continue
                else:
                    break
        return run_result, run_stats_dict

    def _divide_service(self, control_dict, ext_dict):
        """将需要控制的软件分为基础服务和项目服务, 并排序
        env: mysql, redis, jdk, rocketmq, erlang, rabbitmq, es, ffmpeg, glusterfs-server, nginx
        sql: nacos_sql, program-sql
        platform: gluterfs-client, nacos
        program: jar
        frontend: frontend
        check: autocheck

        control_dict={
            "node1": [sof1, soft2], 
            "node2": [sof1, soft2]
        }
        ext_dict: ext.json

        return:
            soft_type_dict={
                "env": {
                    "node1": [soft1, soft2], 
                    "node2": [soft1, soft2]
                }, 
                "platform": {
                    "node1": [soft1, soft2], 
                    "node2": [soft1, soft2]
                }, 
                ...
            }
        """

        soft_type_dict={}
        soft_type_list=["env", "sql", "platform", "program", "frontend", "check"]       # 指定软件类型顺序
        for soft_type in soft_type_list:        # dict插入有序
            soft_type_dict[soft_type]={}

        for node in control_dict:
            for softname in control_dict[node]:
                soft_type=self.get_soft_info(softname, ext_dict, "type")
                if soft_type_dict[soft_type].get(node) is None:
                    soft_type_dict[soft_type][node]=[]
                soft_type_dict[soft_type][node].append(softname)
        ## 删除空key
        #for soft_type in soft_type_dict:
        #    if soft_type_dict[soft_type] == {}:
        #        soft_type_dict.pop(soft_type)
        return soft_type_dict

    def start(self, control_dict, init_dict, arch_dict, ext_dict):
        """按类别, 软件start
            control_dict={
                "node1":["soft1", "soft2"], 
                "node2":["soft1", "soft2"]
            }
            return:
                start_stats_dict={
                    "node1":{
                        "soft1": code
                    }
                }
        """
        soft_type_dict=self._divide_service(control_dict, ext_dict)
        start_result=True
        start_stats_dict={}
        for soft_type in soft_type_dict:
            if len(soft_type_dict[soft_type]) != 0:
                self.log.logger.info(self.str_to_title(f"{soft_type}服务启动", 2))
                start_result, start_stats_dict=self.nodes_control(soft_type_dict[soft_type], "start", "启动", init_dict, arch_dict, ext_dict)
                if start_result:
                    continue
                else:
                    break
        return start_result, start_stats_dict

    def stop(self, control_dict, init_dict, arch_dict, ext_dict):
        """按类别, 软件stop
            control_dict={
                "node1":["soft1", "soft2"], 
                "node2":["soft1", "soft2"]
            }
            return:
                stop_stats_dict={
                    "node1":{
                        "soft1": code
                    }
                }
        """
        soft_type_dict=self._divide_service(control_dict, ext_dict)
        stop_result=True
        stop_stats_dict={}
        for soft_type in reversed(soft_type_dict):      # 反序关闭
            if len(soft_type_dict[soft_type]) != 0:
                self.log.logger.info(self.str_to_title(f"{soft_type}服务停止", 2))
                stop_result, stop_stats_dict=self.nodes_control(soft_type_dict[soft_type], "stop", "停止", init_dict, arch_dict, ext_dict)
                if stop_result:
                    continue
                else:
                    break
        return stop_result, stop_stats_dict

    def _get_program_above_type_dict(self, arch_dict, ext_dict):
        """获取program类型以上的软件结构
        """
        control_dict={}
        for node in arch_dict:
            control_dict[node]=arch_dict[node]["software"]
        soft_type_dict=self._divide_service(control_dict, ext_dict)

        program_above_type_dict={}
        flag=0
        for soft_type in soft_type_dict:
            if soft_type=="program" or flag==1:
                flag=1
                program_above_type_dict[soft_type]=soft_type_dict[soft_type]
        return program_above_type_dict

    def program_stop(self, init_dict, arch_dict, ext_dict):
        """项目关闭
        """
        program_above_type_dict=self._get_program_above_type_dict(arch_dict, ext_dict)
        self.log.logger.debug(f"{program_above_type_dict=}")
        stop_result=True
        stop_stats_dict={}
        for soft_type in reversed(program_above_type_dict):
            if len(program_above_type_dict[soft_type]) != 0:
                self.log.logger.info(self.str_to_title(f"{soft_type}服务关闭", 2))
                stop_result, type_stats_dict=self.nodes_control(program_above_type_dict[soft_type], "stop", "停止", init_dict, arch_dict, ext_dict)
                stop_stats_dict[soft_type]=type_stats_dict
                if stop_result:
                    continue
                else:
                    break
        return stop_result, stop_stats_dict

    def create_backup_version(self):
        """创建备份版本号
        return: 202110100202
        """
        backup_version=time.strftime('%Y%m%d%H%M', time.localtime())
        return backup_version

    def trans_backup_version_to_date(self, backup_version_list):
        """将备份版本号列表转为时间格式显示
        """
        rollback_date_list=[]
        for backup_version in backup_version_list:
            rollback_version=time.strftime('%Y-%m-%d %H:%M',time.strptime(backup_version,'%Y%m%d%H%M'))
            rollback_date_list.append(rollback_version)
        return rollback_date_list

    def trans_date_to_backup_version(self, rollback_date):
        """将回滚版本时间转为备份版本格式
        """
        backup_version=time.strftime('%Y%m%d%H%M',time.strptime(rollback_date, '%Y-%m-%d %H:%M'))
        return backup_version

    def program_backup(self, init_dict, arch_dict, ext_dict, backup_version):
        """项目备份, 用于回滚
            项目包
            arch.josn
            ext.josn
            update_arch.json
        """
        backup_result=True
        backup_stats_dict={}

        rollback_version_dir=f"{rollback_dir}/{backup_version}"
        try:
            self.log.logger.info(f"建立备份目录: {rollback_version_dir}")
            os.makedirs(rollback_version_dir, exist_ok=1)
            arch_backup_file=f"{rollback_version_dir}/{arch_file.split('/')[-1]}"
            self.log.logger.debug(f"cp {arch_file} {arch_backup_file}")
            shutil.copyfile(arch_file, arch_backup_file)
            self.log.logger.debug(f"建立update_arch.json")
            update_arch_dict=copy.deepcopy(arch_dict)
            for node in update_arch_dict:
                for softname in update_arch_dict[node]["software"][:]:
                    soft_type=self.get_soft_info(softname, ext_dict, "type")
                    if soft_type not in backup_soft_type:
                        update_arch_dict[node]["software"].remove(softname)
            backup_update_update_file=f"{rollback_version_dir}/{update_arch_file.split('/')[-1]}"
            result, msg=self.write_config(update_arch_dict, backup_update_update_file)
            if not result:
                return False, {"Error": str(e)}
        except Exception as e:
            return False, {"Error": str(e)}

        control_dict={}
        for node in arch_dict:
            control_dict[node]=arch_dict[node]["software"]
        soft_type_dict=self._divide_service(control_dict, ext_dict)

        # 只选择一份备份
        backup_type_node_dict={}
        for soft_type in reversed(soft_type_dict):      # sql最后再备份
            if soft_type in backup_soft_type:
                if soft_type not in backup_type_node_dict:
                    backup_type_node_dict[soft_type]={}
                for node in soft_type_dict[soft_type]:
                    if node not in backup_type_node_dict[soft_type]:
                        backup_type_node_dict[soft_type][node]=[]
                    for softname in soft_type_dict[soft_type][node]:
                        for backup_node in backup_type_node_dict[soft_type]:
                            if softname in backup_type_node_dict[soft_type][backup_node]:
                                break
                        else:
                            backup_type_node_dict[soft_type][node].append(softname)

        # 删除空的soft_type和node
        for soft_type in list(backup_type_node_dict.keys()):
            if len(backup_type_node_dict[soft_type])==0:
                backup_type_node_dict.pop(soft_type)
            else:
                for node in list(backup_type_node_dict[soft_type]):
                    if len(backup_type_node_dict[soft_type][node])==0:
                        backup_type_node_dict[soft_type].pop(node)
        self.log.logger.debug(f"{backup_type_node_dict=}")

        for soft_type in backup_type_node_dict:
            for node in backup_type_node_dict[soft_type]:
                arch_dict[node]["backup_version"]=backup_version
            self.log.logger.info(self.str_to_title(f"{soft_type}服务备份", 2))
            result, type_stats_dict=self.nodes_control(backup_type_node_dict[soft_type], "backup", "备份", init_dict, arch_dict, ext_dict)
            backup_stats_dict[soft_type]=type_stats_dict
            if result:
                self.log.logger.info(f"{soft_type}服务备份完成")
                continue
            else:
                self.log.logger.error(f"{soft_type}服务备份失败, {type_stats_dict}")
                backup_result=False
                break
        else:
            self.log.logger.info(f"本地备份完成")
            for soft_type in backup_type_node_dict:
                self.log.logger.info(self.str_to_title(f"{soft_type}服务远程备份(回滚)", 2))
                backup_stats_dict[soft_type]={}
                for node in backup_type_node_dict[soft_type]:
                    backup_stats_dict[soft_type][node]={}
                    port=init_dict[arch_dict[node]["ip"]]["port"]
                    for softname in backup_type_node_dict[soft_type][node]:
                        result, msg=self._get_backup_file(node, port, backup_version, softname)
                        backup_stats_dict[soft_type][node][softname]=msg
                        if result:
                            ext_dict=self.set_ext_softname(ext_dict, softname, msg)
                            self.log.logger.info(f"{node}: {softname}服务远程备份完成")
                            continue
                        else:
                            self.log.logger.error(f"{node}: {softname}服务远程备份失败")
                            break
                            backup_result=False
                else:
                    continue
                break
            else:
                result, msg=self.write_config(ext_dict, f"{rollback_version_dir}/{ext_file.split('/')[-1]}")
                if result:
                    self.log.logger.info(f"全部备份完成")
                else:
                    self.log.logger.error(msg)
                    
        return backup_result, backup_stats_dict

    def config_merge(self, init_dict, arch_dict, update_init_dict, update_arch_dict):
        """更新的配置文件合并入init.json和arch.josn
        """
        if len(update_init_dict) != 0:
            init_dict.update(update_init_dict)

        for node in update_arch_dict:
            if node not in arch_dict:
                arch_dict[node]=update_arch_dict[node]
            else:
                for softname in update_arch_dict[node]["software"]:
                    if softname not in arch_dict[node]["software"]:
                        arch_dict[node]["software"].append(softname)
                    softname_info_dict=update_arch_dict[node].get(f"{softname}_info")
                    if  softname_info_dict is not None:
                        arch_dict[node][f"{softname}_info"]=softname_info_dict
        merge_dict={}
        merge_result=True
        for config_list in [
                (init_dict, init_file), 
                (arch_dict, arch_file)
                ]:
            result, msg=self.write_config(config_list[0], config_list[1])
            if not result:
                merge_result=False
                self.log.logger.error(msg)
                merge_dict[init_file]=msg
        else:
            return merge_result, merge_dict

    def program_update(self, init_dict, arch_dict, ext_dict, update_arch_dict, set_hosts_flag):
        """项目更新
        """
        if set_hosts_flag:
            hosts_list=[]               # 获取所有的hosts
            for node in arch_dict:
                hosts_list.append(f"{arch_dict[node].get('ip')} {node}")
            for node in arch_dict:          # 为主机域名配置添加参数
                if node not in update_arch_dict:
                    update_arch_dict[node]={}
                    update_arch_dict[node]["software"]=[]
                update_arch_dict[node]["software"].insert(0, "set_hosts")
                arch_dict[node]["hosts_info"]={}
                arch_dict[node]["hosts_info"]["hostname"]=node
                arch_dict[node]["hosts_info"]["hosts"]=hosts_list

        control_dict={}
        for node in update_arch_dict:
            control_dict[node]=update_arch_dict[node]["software"]

        update_result, update_stats_dict=self.nodes_control(control_dict, "install", "更新", \
                init_dict, arch_dict, ext_dict)
        return update_result, update_stats_dict

    def updated_soft_run(self, init_dict, update_arch_dict, ext_dict):
        """更新的软件运行
        """
        run_result, run_stats_dict=super(graphics_deploy, self).run(init_dict, update_arch_dict, ext_dict)
        return run_result, run_stats_dict

    def program_start(self, init_dict, arch_dict, ext_dict):
        """项目启动
        """
        program_above_type_dict=self._get_program_above_type_dict(arch_dict, ext_dict)
        self.log.logger.debug(f"{program_above_type_dict=}")
        start_result=True
        start_stats_dict={}
        for soft_type in program_above_type_dict:
            if len(program_above_type_dict[soft_type]) != 0:
                self.log.logger.info(self.str_to_title(f"{soft_type}服务启动", 2))
                start_result, type_stats_dict=self.nodes_control(program_above_type_dict[soft_type], "start", "启动", init_dict, arch_dict, ext_dict)
                start_stats_dict[soft_type]=type_stats_dict
                if start_result:
                    continue
                else:
                    break
        return start_result, start_stats_dict

    def get_soft_status(self, init_dict, arch_dict, ext_dict):
        """获取软件状态
        return:
            {
            "node1": {
                "softname1": activated_code|stopped_code|abnormal_code|error_code,     # 启动, 未启动, 启动但不正常, 代码错误
                "softname2": activated_code|stopped_code|abnormal_code,     # 启动, 未启动, 启动但不正常
            }
            }
        """
        soft_stats_dict={}
        for node in arch_dict:
            soft_stats_dict[node]={}
            for softname in arch_dict[node]["software"]:
                port_status=[]
                port_list=self._get_soft_port_list(arch_dict, node, softname)
                self.log.logger.debug(f"{node}, {softname=}, {port_list=}")
                if port_list[0]==portless_service_code:
                    portless_dict={
                            node: [softname]
                            }
                    monitor_result, portless_service_stats_dict=self.nodes_control(portless_dict, "monitor", "状态", init_dict, arch_dict, ext_dict)
                    if monitor_result:
                        soft_stats_dict[node][softname]=portless_service_stats_dict[node][softname]
                    else:
                        soft_stats_dict[node][softname]=error_code
                elif port_list[0]==tool_service_code:
                    pass
                else:
                    try:
                        for port in port_list:
                            port_status.append(port_connect(node, int(port)))
                        if True not in port_status:
                            softname_status=stopped_code
                        elif False not in port_status:
                            softname_status=activated_code
                        else:
                            softname_status=abnormal_code
                        soft_stats_dict[node][softname]=softname_status
                    except Exception:
                        soft_stats_dict[node][softname]=error_code
        return soft_stats_dict

    def get_backup_info(self, arch_dict, type_):
        """获取备份信息
        return:
            backup_info_dict={
                "node":{
                    "key": {
                        "local_backup_dir": "/path", 
                        "remote_backup_dir": "node1:/path"
                    }
                }
            }

            backup_info_dict={
                "backup_dir":""
            }
        """
        backup_info_dict={}
        if type_=="crontab":
            backup_tool_name="backup_tool"
            for node in arch_dict:
                if backup_tool_name in arch_dict[node]["software"]:
                    backup_config_dict=arch_dict[node][f"{backup_tool_name}_info"]
                    backup_info_dict[node]={}
                    for backup_str in backup_config_dict:
                        for key in backup_config_dict[backup_str]:
                            if key != "type":
                                if backup_config_dict[backup_str][key].get("remote_backup") is None:
                                    remote_backup_dir="未设置"
                                else:
                                    remote_backup_host=backup_config_dict[backup_str][key]["remote_backup"]["remote_backup_host"]
                                    remote_backup_dir=f"{remote_backup_host}:{backup_config_dict[backup_str][key]['remote_backup']['remote_backup_dir']}"
                                backup_info_dict[node][f"{backup_str}_{key}"]={
                                        "local_backup_dir": backup_config_dict[backup_str][key]["backup_dir"], 
                                        "remote_backup_dir": remote_backup_dir
                                        }
        elif type_=="update":
            if os.path.exists(backup_dir):
                backup_info_dict={
                        "backup_dir": backup_dir
                        }
        else:
            self.log.logger.warning(f"未识别的类型: {type_}")
        return backup_info_dict

    def tar_report(self, init_dict, arch_dict, check_stats_dict):
        """获取巡检报告并打包发送
        """
        # 删除旧报告
        try:
            os.makedirs(report_dir, exist_ok=1)
            for file_ in os.listdir(report_dir):
                os.remove(f"{report_dir}/{file_}")

            self.log.logger.debug("获取巡检报告")
            ssh_client=ssh()
            for node in check_stats_dict:
                port=init_dict[arch_dict[node]["ip"]]["port"]
                if check_stats_dict[node]:
                    for file_ in report_file_list:
                        remote_file=f"{located_dir_link}/{autocheck_dst}/report/{file_}"
                        local_file=f"{report_dir}/{node}_{file_}"
                        try:
                            ssh_client.get(node, port, "root", remote_file, local_file)
                            self.log.logger.debug(f"geted: {node}:{remote_file} --> {local_file}")
                        except FileNotFoundError:
                            pass
                    else:
                        self.log.logger.info(f"已获取{node}节点巡检报告")
            self.log.logger.info("合并巡检报告")
            for file_ in report_file_list:
                with open(f"{report_dir}/{file_}", "a", encoding="utf8") as write_f:
                    for report_file in os.listdir(report_dir)[:]:
                        if report_file.endswith(file_):
                            with open(f"{report_dir}/{report_file}", "r", encoding="utf8") as read_f:
                                write_f.write(read_f.read())
                                write_f.write("\n\n")
            else:
                tarfile_=f"{report_dir}/report-{time.strftime('%Y%m%d%H%M', time.localtime())}.tar.gz"
                with tarfile.open(tarfile_, "w:gz") as tar:
                    for file_ in report_file_list:
                        tar.add(f"{report_dir}/{file_}")
        except Exception as e:
            self.log.logger.error(f"巡检报告: {str(e)}")
            tarfile_=None
        return tarfile_

    def check(self, check_dict, init_dict, arch_dict, ext_dict):
        """获取巡检信息
        check_dict={
            "nodes":["node1", "node2"]
        }

        return:
            run_result: True|False
            run_stats_dict={
                "node1": {
                    "soft1": True|False
                }
            }
        """
        control_dict={}
        for node in check_dict["nodes"]:
            control_dict[node]=["autocheck"]

        check_result, check_stats_dict=self.nodes_control(control_dict, "sendmail", "巡检", init_dict, arch_dict, ext_dict)
        tarfile_=self.tar_report(init_dict, arch_dict, check_stats_dict)
        return check_result, check_stats_dict, tarfile_

    def get_backup_version_list(self):
        """获取备份列表
        """
        backup_version_list=[]
        if os.path.exists(backup_version_file):
            result, config_list=self.read_config(["backup_version"])
            if result:
                backup_version_list=config_list[0]
        return backup_version_list

    def get_rollback_version_list(self):
        """获取回滚列表
        """
        backup_version_list=self.get_backup_version_list()
        rollback_version_list=self.trans_backup_version_to_date(backup_version_list)
        return rollback_version_list

    def get_local_ip_list(self):
        '''获取本机ip列表
        return (ip1, ip2)
        '''
        local_ip_list=[]
        nic=psutil.net_if_addrs()
        for adapter in nic:
            for snic in nic[adapter]:
                if snic.family.name=="AF_INET":
                    if adapter!="lo" or snic.address!="127.0.0.1":
                        local_ip_list.append(snic.address)
        return local_ip_list

    def program_license_register(self, src_license, dst_license, init_dict, arch_dict):
        '''license注册
        para:
            src_license:  /path
            dst_license:  /path
        return:
            register_result: bool
            register_dict:{node: bool, node: bool}
        '''
        register_dict={}
        register_result=True
        for node in arch_dict:
            for softname in arch_dict[node]["software"]:
                if softname.startswith("program_"):
                    port=init_dict[arch_dict[node]["ip"]]["port"]
                    self.log.logger.info(f"{node}节点注册license")
                    self.log.logger.debug(f"copy {src_license} {node}:{dst_license}")
                    result, msg=self.ssh_client.scp(src_license, dst_license, node, port)
                    register_dict[node]=result
                    if not result:
                        self.log.logger.error(f"{node}节点注册失败: {msg}")
                        register_result=False
                    break
        return register_result, register_dict

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
            self.init_stats_dict["host_info"]=self.json_to_init_dict(all_host_info)

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
        self.log.logger.info("集群安装...")
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
        self.log.logger.info("集群启动...")
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
    os.environ["DIALOGRC"]="./libs/dialogrc"       # 指定dialog的颜色配置文件

    def __init__(self):
        """检测dialog安装, 初始化dialog
        """
        super(graphics_deploy, self).__init__()
        self.log=Logger({"file": log_file_level}, log_file=log_file)
        self.log.logger.info("文本图形化")

        # 安装dialog
        if not self._install_dialog():
            print("Error: dialog安装失败, 请手动安装后再执行")
            sys.exit(error_code)

        locale.setlocale(locale.LC_ALL, '')
        self.d = self.Dialog(dialog="dialog", autowidgetsize=1)
        self.d.set_background_title("项目部署")
        self.term_rows, self.term_cols=self.get_term_size()

    def get_term_size(self):
        """获取合适的终端尺寸
        """
        term_rows, term_cols=self.d.maxsize(use_persistent_args=False)
        if term_rows < g_term_rows or term_cols < g_term_cols:
            print(f"当前终端窗口({term_rows}, {term_cols})过小({g_term_rows}, {g_term_cols}), 请放大窗口后重试")
            sys.exit(error_code)
        else:
            self.log.logger.debug(f"当前窗口大小为({term_rows}, {term_cols})")
            return int(term_rows * 0.8), int(term_cols * 0.8)

    '''
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

    def config(self):
        """集群配置
        1. 配置项目名称
        2. 配置init.json
        3. 配置arch.json
        """

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

    def config_arch(self, init_dict, arch_dict, title):
        """
            配置arch.json
        """
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

    def config_soft(self, softname, nodename, soft_dict):
        """
            单个软件配置
        """
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
        """排除已安装软件的资源
        """
        return host_info_dict

    def _host_nums_verifi(self):
        """集群主机与模板主机数相同
        """
        self.log.logger.debug("验证架构主机数量...")
        if len(self.init_dict) != len(self.arch_dict):
            return False, "配置主机数量与模板主机数量不一致, 请重新配置"
        else:
            return True, ""

    def _localized_soft_resource_verifi(self):
        """从模板中查找是否有已安装软件(国产化软件)
        """
        self.log.logger.debug("适配国产化软件...")

        return True, ""

    def _resource_used_verifi(self):
        """针对各主机当前CPU使用率, 内存使用率, 磁盘(最大)使用率校验(20%)
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

    def _get_free_mem(self, mem_total):
        """获取主机可用内存大小
        """
        system_mem_M=mem_total * 0.1 / 1024 / 1024
        if system_mem_M >= 2048:                    # 系统保留内存最多2G
            mem_free=mem_total-2048 * 1024 * 1024
        else:
            mem_free=mem_total * 0.9
        return mem_free

    def _resource_reallocation(self):
        """根据现有配置重新分配各软件资源
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
        """分配资源后, 校验软件集群中各软件配置是否相同. 若不同, 则将集群中各软件重置为最小配置
        """
        self.log.logger.debug("集群资源验证...")
        return True, ""

    def generate_arch(self):
        """补充arch.json
            1. located
            2. ip
        """
        verifi_funs=[
                self._host_nums_verifi, 
                #self._localized_soft_resource_verifi, 
                #self._resource_used_verifi, 
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
    def config_check_bak(self, title):
        """配置巡检接收人
        """
        result, config_list=self.read_config(["host", "arch", "project"])
        if not result:
            self.d.msgbox(f"{config_list}")
            return
        host_info_dict, arch_dict, project_dict=config_list

        mail_list=[]
        sms_list=[]
        for node in host_info_dict:
            mail_list.append(host_info_dict[node]["Interface"]["mail"])
            sms_list.append(host_info_dict[node]["Interface"]["sms"])
        self.log.logger.debug(f"{mail_list=}, {sms_list=}")

        mail_flag=False
        if True in mail_list:
            mail_flag=True

        sms_flag=False
        if True in sms_list:
            sms_flag=True

        if mail_flag==False and sms_flag==False:
            self.d.msgbox("服务器无法连接外部接口, 不能配置自动巡检及预警", title="警告")
            return
        else:
            check_dict=self._get_check_info(arch_dict, project_dict)
            self.log.logger.debug(f"{check_dict=}")
            while True:
                code, check_info_list=self.edit_check_config(title, check_dict)
                self.log.logger.debug(f"{check_info_list=}")
                if code==self.d.OK:
                    code=self.show_check_config(title, check_info_list)
                    if code==self.d.OK:
                        result, msg=self._set_check_info(arch_dict, project_dict, check_info_list)
                        if result:
                            break
                        else:
                            self.log.logger.error(msg)
                            self.d.msgbox(msg, title="警告")
                            continue
                    else:
                        continue
                else:
                    return
    def _get_check_info_bak(self, arch_dict, project_dict):
        """获取check_dict
        return: 
            check_dict={
                "project_name": "", 
                "timing": "18:30", 
                "sender": "", 
                "mail_list": [], 
                "sms_list": []
            }
        """
        project_name=project_dict.get("project_name")
        if project_name is None:
            project_name="xx项目"

        sender="xxx"
        timing="20:30"
        node_name=list(arch_dict.keys())[0]

        mail_list=[]
        inspection_info_dict=arch_dict[node_name]["autocheck_info"].get("inspection_info")
        if inspection_info_dict is not None:
            sender=inspection_info_dict.get("inspection_sender")
            timing=inspection_info_dict.get("inspection_time")
            mail_list=inspection_info_dict.get("inspection_receive")
        check_dict={
            "project_name": project_name, 
            "timing": timing, 
            "sender": sender, 
            "mail_list": mail_list
        }

        sms_list=[]
        warning_info_dict=arch_dict[node_name]["autocheck_info"].get("warning_info")
        if warning_info_dict is not None:
            sms_info_dict=warning_info_dict.get("sms_info")
            if sms_info_dict is not None:
                sms_list=sms_info_dict.get("sms_receive")
        check_dict["project_name"]=project_name
        check_dict["sms_list"]=sms_list

        return check_dict
    def get_file_path(self, init_path, title):
        """获取选择文件路径
        """
        while True:
            code, file_=self.d.fselect(init_path, height=8, width=65, title=title)
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
    def init_bak(self, title, init_dict):
        """图形: 初始化
        """
        result, config_list=self.read_config(["init"])
        if result:
            init_dict=config_list[0]
        else:
            init_dict={}

        # 填写init.json并校验, 选填check.json
        while True:
            code, init_dict=self.config_init(title, init_dict)
            if code==self.d.OK:             # 初始化按钮
                result, dict_=self.account_verifi(init_dict)                # 校验init.dict
                if not result:
                    continue
                else:
                    code=self.show_host_account_info(title, init_dict)      # 显示init_dict(确认主机信息)
                    if code==self.d.OK:                                     # 确认
                        for _ in init_dict:                                 # 更改port类型为int
                            init_dict[_]["port"]=int(init_dict[_]["port"])
                        result, msg=self.write_config(init_dict, init_file)
                        if result:
                            code=self.d.yesno("是否需要配置巡检信息", title="消息")
                            if code==self.d.OK:
                                if self.config_check(title):
                                    break
                                else:
                                    continue
                            else:
                                break
                        else:
                            self.log.logger.error(msg)
                            self.d.msgbox(msg)
                            return False
                    else:       # 修改按钮
                        continue
            else: # 取消按钮
                return False

        # 开始初始化
        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            os.close(read_fd)
            with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)

                self.log.logger.info("检测主机配置, 请稍后...\n")
                result, connect_test_result=self.connect_test(init_dict)
                if not result:
                    self.log.logger.error("主机信息配置有误, 请根据下方显示信息修改:")
                    for node in connect_test_result:
                        if connect_test_result[node]["result"] != normal_code:
                            self.log.logger.error(f"{node}:\t{connect_test_result[node]['err_msg']}")
                    os._exit(error_code)
                result, config_list=self.read_config(["ext"])
                if result:
                    ext_dict=config_list[0]
                else:
                    self.log.logger.error(f"初始化失败: {config_list}")
                    os._exit(error_code)
                status, dict_=super(graphics_deploy, self).init(init_dict, ext_dict)
                if status is True:
                    self.log.logger.info("初始化完成\n")
                    self.log.logger.info("获取主机信息中, 请稍后...")
                    all_host_info=self.get_host_msg(init_dict)
                    self.log.logger.debug(f"主机信息: {all_host_info}")
                    all_host_dict=self.json_to_init_dict(all_host_info)
                    result, msg=self.write_config(all_host_dict, host_info_file)
                    if not result:
                        self.log.logger.error(msg)
                        os._exit(error_code)
                    else:
                        self.log.logger.info("主机信息已获取, 请查看")
                else:
                    self.log.logger.error(f"初始化失败: {dict_}")
                    os._exit(error_code)
            os._exit(normal_code)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=25, width=170, scrollbar=True)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单", width=40, height=5)
            self.show_menu()
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试", width=40, height=5)
            self.show_menu()

        flag=True           # 初始化结果值
        if exit_code==normal_code:
            time.tzset()    # 主机信息获取过程中会重置时区, 程序内重新获取时区信息

            # 显示主机资源信息
            _, config_list=self.read_config(["host"])
            host_info_dict=config_list[0]
            code=self.show_hosts_info(host_info_dict)

            # 补充arch_dict和project_dict
            if code==self.d.OK:    # 开始部署按钮
                # 将check_dict信息写入arch_dict和project_dict
                result, config_list=self.read_config(["arch", "project"])
                if result:
                    arch_dict, project_dict=config_list
                    result, config_list=self.read_config(["check"])
                    if result:      # 配置巡检
                        check_dict=config_list[0]
                        result, msg=self._set_check_info(arch_dict, project_dict, check_dict)
                        if not result:
                            self.log.logger.error(msg)
                            self.d.msgbox(msg, title="错误")
                            return False
                    # 资源校验适配
                    result, dict_=self.resource_verifi(arch_dict, host_info_dict)
                    if result:
                        self.log.logger.debug(f"写入arch配置")
                        self.write_config(dict_, arch_file)
                    else:
                        self._show_non_resource(dict_)
                        flag=False
                else:
                    self.log.logger.error(config_list)
                    self.d.msgbox(config_list, title="警告", width=80, height=6)
                    flag=False
            else:                           # 终止部署按钮
                flag=False
        else:
            flag=False
        return flag
    def upper_part_init_fun_bak(self, title, config_fun, init_dict):
        """配置init dict, 校验, 选配check_dict
            title:
            config_fun: self.config_init, self.config_update_init
            init_dict: {}
        """
        while True:
            result, init_dict=config_fun(title, init_dict)
            self.log.logger.debug(f"{init_dict=}")
            if result:
                result, dict_=self.account_verifi(init_dict)                # 校验init.dict
                if not result:
                    return False, dict_, {}
                else:
                    check_dict=self.config_check(title)
                    return True, init_dict, check_dict
            else:
                return False, {}, {}
    def program_update_bak(self):
        """图形: deploy中项目更新
        """
        self.log.logger.info("开始项目部署...")
        result, config_list=self.read_config(["update", "init", "arch"])
        if result:
            update_dict, init_dict, arch_dict=config_list
            result, dict_=super(graphics_deploy, self).update(update_dict, program_unzip_dir, False, init_dict, arch_dict)  # 使用父类的update
            if result:
                self.log.logger.info("项目部署完成")
            else:
                self.log.logger.error("项目部署失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_
    '''

    def edit_added_host_account_info(self, title, init_list, add_init_list):
        """编辑增加的主机账号信息
        """
        READ_ONLY = 0x2
        first_node_xi_length=20
        ip_field_length=15
        password_field_length=15
        port_field_length=5

        elements=[]
        n=0
        for account_info in init_list:
            n=n+1
            elements.append(("IP:", n, 1, account_info[0], n, 5, 0, 0))
            elements.append(("root用户密码:", n, 22, account_info[1], n, 36, 0, 0))
            elements.append(("ssh端口: ", n, 52, str(account_info[2]), n, 61, 0, 0))
        for add_account_info in add_init_list:
            n=n+1
            if len(add_account_info)==0:
                ip=f"{'.'.join(account_info[0].split('.')[:-1])}."
                password=account_info[1]
                port=account_info[2]
            else:
                ip=add_account_info[0]
                password=add_account_info[1]
                port=add_account_info[2]
            elements.append(("IP:", n, 1, ip, n, 5, ip_field_length, 0))
            elements.append(("root用户密码:", n, 22, password, n, 36, password_field_length, 0))
            elements.append(("ssh端口: ", n, 52, str(port), n, 61, port_field_length, 0))
        code, fields=self.d.form(f"填写新增的{len(add_init_list)}台主机信息:", elements=elements, title=title, ok_label="初始化", cancel_label="取消")
        self.log.logger.debug(f"新增主机信息: {code=}, {fields=}")
        return code, fields

    def edit_host_account_info(self, title, init_list, local_flag):
        """编辑主机账号信息
        para:
            title: str
            init_list: ((ip, pwd, port), )
            local_flag: bool
        return:
            init_fields: [ip, pwd, port, ip2, pwd2, port2]
        """
        first_node_xi_length=20
        ip_field_length=15
        password_field_length=15
        SHOW=0x0
        HIDDEN = 0x1
        READ_ONLY = 0x2
        if local_flag:
            port_field_length=5
            port=0
            ATTRIBUTE=READ_ONLY
        else:
            port_field_length=5
            port=22
            ATTRIBUTE=SHOW

        if len(init_list) == 0:
            local_ip_list=self.get_local_ip_list()
            if len(local_ip_list)==0:
                self.showmsg("当前主机未配置ip", "Error")
                self.cancel()
            while True:
                if len(local_ip_list)==1:
                    elements=[
                            ("IP:", 1, 1, local_ip_list[0], 1, first_node_xi_length, ip_field_length, 0, SHOW), 
                            ("root用户密码:", 2, 1, "", 2, first_node_xi_length, password_field_length, 0, SHOW), 
                            ("ssh端口:", 3, 1, str(port), 3, first_node_xi_length, port_field_length, 0, ATTRIBUTE), 
                            ]
                    if local_flag:
                        code, init_fields=self.d.mixedform(f"请填写本机信息:", elements=elements, title=title, ok_label="初始化", cancel_label="取消", height=7)
                    else:
                        code, init_fields=self.d.mixedform(f"请填写集群中主机信息\n\n本机:", elements=elements, title=title, extra_button=True, extra_label="继续添加", ok_label="初始化", cancel_label="取消", height=9)
                    break
                else:
                    choices_list=[]
                    for ip in local_ip_list:
                        choices_list.append((ip, ""))
                    _, ip=self.d.menu("请选择本机IP:", choices=choices_list, title=title, ok_label="选择", no_cancel=True)
                    self.log.logger.debug(f"选择{ip=}")
                    local_ip_list=[ip]
                    continue
        else:
            elements=[]
            n=0
            for account_info in init_list:
                n=n+1
                elements.append(("IP:", n, 1, account_info[0], n, 5, ip_field_length, 0, SHOW))
                elements.append(("root用户密码:", n, 22, account_info[1], n, 36, password_field_length, 0, SHOW))
                elements.append(("ssh端口: ", n, 52, str(account_info[2]), n, 61, port_field_length, 0, ATTRIBUTE))
            if local_flag:
                code, init_fields=self.d.mixedform(f"填写本机信息:", elements=elements[:3], title=title, ok_label="初始化", cancel_label="取消")
            else:
                code, init_fields=self.d.mixedform(f"填写集群主机信息:", elements=elements, title=title, extra_button=True, extra_label="继续添加", ok_label="初始化", cancel_label="取消")
        self.log.logger.debug(f"主机信息: {code=}, {init_fields=}")
        return code, init_fields

    def edit_check_config_bak(self, title, check_dict):
        """配置巡检信息

        check_dict={
            "project_name": "", 
            "timing": "18:30", 
            "sender": "", 
            "mail_list": [], 
            "sms_list": []
        }
        """
        xi=20
        receive_length=200
        field_length=15
        n=1
        elements=[
                ("项目名称:", n, 1, check_dict.get("project_name"), n, xi, field_length, 0), 
                ("定时巡检时间:", n+1, 1, check_dict.get("timing"), n+1, xi, 6, 0), 
                ("巡检发送人:", n+2, 1, check_dict.get("sender"), n+2, xi, field_length, 0), 
                ("邮箱地址:", n+3, 1, ",".join(check_dict.get("mail_list")), n+3, xi, receive_length, 0), 
                ("手机号:", n+4, 1, ",".join(check_dict.get("sms_list")), n+4, xi, receive_length, 0), 
                ]
        code, fields=self.d.form(f"配置巡检信息:\n注: 多个邮箱地址或手机号使用','分割", elements=elements, title=title, width=80, height=13, ok_label="确认", cancel_label="不配置")
        self.log.logger.debug(f"巡检信息: {code=}, {fields=}")
        return code, fields

    def edit_localization_config(self, title, stage, node, softname, soft_manaul_dict):
        """配置国产化软件(包含autocheck)信息
        return bool, soft_manaul_dict
        """
        first_xi_length=20
        ip_field_length=15
        field_length=15
        password_field_length=15
        port_field_length=5
        command_field_length=50
        elements=[]
        if softname=="dameng" or softname=="shentong" or softname=="kingbase":
            elements.append((f"软件名:", 1, 1, softname, 1, first_xi_length, 0, 0))
            elements.append(("服务器IP:", 2, 1, soft_manaul_dict["db_ip"], 2, first_xi_length, ip_field_length, 0))
            elements.append(("软件安装用户名:", 3, 1, soft_manaul_dict["system_user"], 3, first_xi_length, field_length, 0))
            elements.append(("dba用户名:", 4, 1, soft_manaul_dict["dba_user"], 4, first_xi_length, field_length, 0))
            elements.append(("dba密码:", 5, 1, soft_manaul_dict["dba_password"], 5, first_xi_length, password_field_length, 0))
            elements.append(("端口:", 6, 1, str(soft_manaul_dict["db_port"]), 6, first_xi_length, 0, 0))
            elements.append((f"{softname}启动命令:", 7, 1, soft_manaul_dict["start_command"], 7, first_xi_length, command_field_length, 0))
            elements.append((f"{softname}关闭命令:", 8, 1, soft_manaul_dict["stop_command"], 8, first_xi_length, command_field_length, 0))
            msg=f"{node}填写软件信息:"
        elif softname=="autocheck":
            field_length=15
            receive_length=80
            elements.append(("项目名称:", 1, 1, soft_manaul_dict.get("project_name"), 1, first_xi_length, field_length, 0))
            elements.append(("定时巡检时间:", 2, 1, soft_manaul_dict.get("timing"), 2, first_xi_length, 6, 0))
            elements.append(("巡检发送人:", 3, 1, soft_manaul_dict.get("sender"), 3, first_xi_length, field_length, 0))
            elements.append(("邮箱地址:", 4, 1, ",".join(soft_manaul_dict.get("mail_list")), 4, first_xi_length, receive_length, 0))
            elements.append(("手机号:", 5, 1, ",".join(soft_manaul_dict.get("sms_list")), 5, first_xi_length, receive_length, 0))
            msg=f"{node}配置巡检信息:\n注: 多个邮箱地址或手机号使用','分割"
        elif softname=="keepalived":
            elements.append(("虚拟IP/MASK:", 1, 1, soft_manaul_dict.get("virtual_addr"), 1, ip_field_length+3, ip_field_length+3, 0))
            msg=f"{node}配置keepalived信息:\n注: 格式为192.168.0.3/24"
        else:
            pass
        code, fields=self.d.form(msg, elements=elements, title=f"{title}: 手动配置({stage})", ok_label="继续", cancel_label="取消")
        self.log.logger.debug(f"软件配置信息: {code=}, {fields=}")
        if code==self.d.OK:     # 继续
            if softname=="dameng" or softname=="shentong" or softname=="kingbase":
                soft_manaul_dict["db_ip"]=fields[0]
                soft_manaul_dict["system_user"]=fields[1]
                soft_manaul_dict["dba_user"]=fields[2]
                soft_manaul_dict["dba_password"]=fields[3]
                soft_manaul_dict["start_command"]=fields[4]
                soft_manaul_dict["stop_command"]=fields[5]
            elif softname=="autocheck":
                soft_manaul_dict["project_name"]=fields[0]
                soft_manaul_dict["timing"]=fields[1]
                soft_manaul_dict["sender"]=fields[2]
                soft_manaul_dict["mail_list"]=fields[3].split(",")
                soft_manaul_dict["sms_list"]=fields[4].split(",")
            elif softname=="keepalived":
                soft_manaul_dict["virtual_addr"]=fields[0]
            return True, soft_manaul_dict
        else:                   # 取消
            return False, ()

    def show_host_account_info(self, title, init_dict):
        """显示并确认主机账号信息
        para:
            title: 
            init_dict:
        return 
            code: 确认/修改
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        first_node_xi_length=20
        ip_field_length=15
        password_field_length=15
        port_field_length=5
        elements=[]
        n=0
        for ip in init_dict:
            n=n+1
            elements.append(("IP:", n, 1, ip, n, 5, ip_field_length, 0, READ_ONLY))
            elements.append(("root用户密码:", n, 22, init_dict[ip]["root_password"], n, 36, password_field_length, 0, READ_ONLY))
            elements.append(("ssh端口: ", n, 52, str(init_dict[ip]["port"]), n, 61, port_field_length, 0, READ_ONLY))
        code, _=self.d.mixedform(f"确认主机信息:", elements=elements, title=title, ok_label="确认", cancel_label="修改")
        return code

    def show_check_config_bak(self, title, check_info_list):
        """显示巡检接收信息
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        xi=20
        receive_length=200
        field_length=15
        n=1
        elements=[
                ("项目名称:", n, 1, check_info_list[0], n, xi, field_length, 0, READ_ONLY), 
                ("定时巡检时间:", n+1, 1, check_info_list[1], n+1, xi, 6, 0, READ_ONLY), 
                ("发送者:", n+2, 1, check_info_list[2], n+2, xi, field_length, 0, READ_ONLY), 
                ("邮箱地址:", n+3, 1, check_info_list[3], n+3, xi, receive_length, 0, READ_ONLY), 
                ("手机号:", n+4, 1, check_info_list[4], n+4, xi, receive_length, 0, READ_ONLY), 
                ]
        code, _ = self.d.mixedform(f"巡检信息:", elements=elements, title=title, width=80, ok_label="确认", cancel_label="修改")
        return code

    def show_localization_config(self, title, localization_dict):
        """显示国产化软件配置信息并确认
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        xi=25
        receive_length=200
        field_length=15
        n=0
        tab=3
        elements=[]
        ip_field_length=15
        password_field_length=15
        port_field_length=5
        command_field_length=50
        for node in localization_dict:
            n+=1
            elements.append((f"{node}:", n, 1, "", n, xi, field_length, 0, HIDDEN))
            for softname in localization_dict[node]["software"]:
                soft_dict=localization_dict[node][f"{softname}_info"]
                if softname=="dameng" or softname=="shentong" or softname=="kingbase":
                    elements.append((f"{softname}:", n+1, tab, "", n+1, xi, field_length, 0, HIDDEN))
                    elements.append(("服务器IP:", n+2, 2*tab, soft_dict["db_ip"], n+2, xi, ip_field_length, 0, READ_ONLY))
                    elements.append(("软件安装用户名:", n+3, 2*tab, soft_dict["system_user"], n+3, xi, field_length, 0, READ_ONLY))
                    elements.append(("dba用户名:", n+4, 2*tab, soft_dict["dba_user"], n+4, xi, field_length, 0, READ_ONLY))
                    elements.append(("dba密码:", n+5, 2*tab, soft_dict["dba_password"], n+5, xi, password_field_length, 0, READ_ONLY))
                    elements.append(("端口:", n+6, 2*tab, str(soft_dict["db_port"]), n+6, xi, port_field_length, 0, READ_ONLY))
                    elements.append((f"{softname}启动命令:", n+7, 2*tab, soft_dict["start_command"], n+7, xi, command_field_length, 0, READ_ONLY))
                    elements.append((f"{softname}关闭命令:", n+8, 2*tab, soft_dict["stop_command"], n+8, xi, command_field_length, 0, READ_ONLY))
                    n=n+8
                elif softname=="autocheck":
                    elements.append((f"{softname}:", n+1, tab, "", n+1, xi, field_length, 0, HIDDEN))
                    elements.append(("项目名称:", n+2, 2*tab, soft_dict.get("project_name"), n+2, xi, field_length, 0, READ_ONLY))
                    elements.append(("定时巡检时间:", n+3, 2*tab, soft_dict.get("timing"), n+3, xi, 6, 0, READ_ONLY)) 
                    elements.append(("巡检发送人:", n+4, 2*tab, soft_dict.get("sender"), n+4, xi, field_length, 0, READ_ONLY))
                    elements.append(("邮箱地址:", n+5, 2*tab, ",".join(soft_dict.get("mail_list")), n+5, xi, receive_length, 0, READ_ONLY))
                    elements.append(("手机号:", n+6, 2*tab, ",".join(soft_dict.get("sms_list")), n+6, xi, receive_length, 0, READ_ONLY))
                    n=n+6
                elif softname=="keepalived":
                    elements.append((f"{softname}:", n+1, tab, "", n+1, xi, field_length, 0, HIDDEN))
                    elements.append(("虚拟IP/MASK:", n+2, 2*tab, soft_dict.get("virtual_addr"), n+2, xi, ip_field_length+3, 0, READ_ONLY))
                    n=n+2
                else:
                    pass
        elements.append((" ", n+1, 1, "", n+1, xi, field_length, 0, HIDDEN))
        code, _ = self.d.mixedform(f"配置信息确认:", elements=elements, title=title, width=80, ok_label="初始化", cancel_label="修改")
        if code==self.d.OK:
            return True
        else:
            return False

    def show_hosts_info(self, all_host_info_dict):
        """显示各主机信息
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi_1=17
        xi_2=25
        xi_3=38
        xi_4=50
        xi_5=62
        field_length=60
        elements=[]

        n=0
        for ip in all_host_info_dict:
            n=n+1
            node_info_dict=all_host_info_dict[ip]
            if node_info_dict.get("error_info") is None:
                info=[
                        (f"{ip}: ", n, 1, "", n, xi_1, field_length, 0, HIDDEN), 
                        ("内核版本: ", n+1, tab, node_info_dict["kernel_version"], n+1, xi_1-3, field_length, 0, READ_ONLY), 
                        ("发行版本: ", n+2, tab, node_info_dict["os_name"], n+2, xi_1-3, field_length, 0, READ_ONLY), 
                        ("CPU架构: ", n+3, tab, f"{node_info_dict['cpu_arch']}", n+3, xi_1-2, field_length, 0, READ_ONLY), 
                        ("CPU个数: ", n+3, xi_2, f"{node_info_dict['CPU'][0]}", n+3, xi_3, field_length, 0, READ_ONLY), 
                        ("CPU使用率: ", n+3, xi_4, f"{node_info_dict['CPU'][1]}%", n+3, xi_5, field_length, 0, READ_ONLY), 
                        ("内存大小: ", n+4, tab, format_size(node_info_dict['Mem'][0]), n+4, xi_1-2, field_length, 0, READ_ONLY), 
                        ("内存使用率: ", n+4, xi_2, f"{node_info_dict['Mem'][1]}%", n+4, xi_3, field_length, 0, READ_ONLY)
                        ]
                elements.extend(info)

                n=n+5
                elements.append(("磁盘: ", n, tab, "", n, xi_1, field_length, 0, HIDDEN))
                for disk in node_info_dict["Disk"]:
                    n=n+1
                    disk_info=[
                            ("挂载目录: ", n, tab*2, disk, n, xi_1-1, field_length, 0, READ_ONLY),
                            ("磁盘大小: ", n, xi_2+3, format_size(node_info_dict['Disk'][disk][0]), n, xi_3, field_length, 0, READ_ONLY), 
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

                n=n+1
                elements.append(("接口: ", n, tab, "", n, xi_1, field_length, 0, HIDDEN))
                for interface_name in node_info_dict["Interface"]:
                    n=n+1
                    interface_info=[
                            (f"{interface_name}: ", n, tab*2, str(node_info_dict["Interface"][interface_name]), n, xi_2, field_length, 0, READ_ONLY),
                            ] 
                    elements.extend(interface_info)

                n=n+1
                if node_info_dict["NTP"]["result"]:
                    msg="True"
                else:
                    msg=node_info_dict["NTP"]["msg"]
                elements.append(("NTP: ", n, tab, msg, n, xi_1, field_length, 0, READ_ONLY))

                n=n+1
            else:
                error_msg=node_info_dict["error_info"]
                elements.append((ip, n, 1, error_msg, n, xi_1, field_length, 0, READ_ONLY))
        elements.append(("", n+1, 1, "", n+1, xi_1, field_length, 0, HIDDEN))
        #self.log.logger.debug(f"host info summary: {elements=}")
        code, _ = self.d.mixedform(f"请确认集群主机信息:", elements=elements, ok_label="开始部署", cancel_label="终止部署")
        return code

    def show_arch_summary(self, title, arch_dict, msg, ok_label, cancel_label):
        """显示arch_dict
        """
        return self.edit_arch_ip_and_located(title, arch_dict, located_is_show=True, readonly=True, msg=msg, ok_label=ok_label, cancel_label=cancel_label)

    def _show_non_resource(self, non_resource_dict):
        """显示资源不足的信息
        para:
            non_resource_dict:
                {
                    ip:{
                        "Mem": N, 
                        "CPU": N
                    }
                }
        """
        msg=""
        for ip in non_resource_dict:
            msg=f"{msg}\n* 主机({ip})至少需要:"
            mem=non_resource_dict[ip].get("Mem")
            cpu=non_resource_dict[ip].get("CPU")
            if mem:
                msg=f"{msg} {format_size(mem)}内存"
            if cpu:
                msg=f"{msg} {cpu}核心CPU"

        self.log.logger.error(f"资源不足: {msg}")
        self.d.msgbox(msg, title="资源不足", width=70, height=10)

    def _show_not_pass_init(self, not_pass_init_dict):
        """显示不标准的init配置
        """
        pass

    def _get_local_arch_dict(self, arch_dict, local_node):
        """在arch_dict中只保留local_node
        """
        for node in arch_dict.copy():
            if node != local_node:
                arch_dict.pop(node)
        return arch_dict

    def _trans_init_dict_to_init_list(self, init_dict):
        """将init_dict转为有序的list显示
        para: 
            init_dict
        return 
            init_list: ((ip, pwd, port), )
        """
        init_list=[]
        for ip in init_dict:
            init_list.append((ip, init_dict[ip]["root_password"], init_dict[ip]["port"]))
        return init_list

    def _trans_init_list_to_init_dict(self, init_list):
        """将init_list转为init_dict
        para:
            init_list: [(ip, pwd, port), (ip, pwd, port)]
        return:
            init_dict: {
                "ip": {
                    "root_password": pwd, 
                    "port": port
                }, 
             }
        """
        init_dict={}
        for account_info in init_list:
            ip=account_info[0]
            pwd=account_info[1]
            port=account_info[2]
            if ip != "":             # ip信息为空, 则删除
                init_dict[ip]={
                        "root_password": pwd, 
                        "port": int(port)
                        }
        return init_dict

    def _trans_init_fields_to_init_list(self, init_fields):
        """ 将fields list转为init_list
        para: 
            init_fields: [ip, pwd, port, ip, pwd, port]
        return 
            init_list: [(ip, pwd, port), (ip, pwd, port)]
        """
        init_list=[]
        for index, item in enumerate(init_fields):
            if index % 3 == 0:
                account_info=(init_fields[index], init_fields[index+1], int(init_fields[index+2]))
                init_list.append(account_info)
        return init_list

    def _trans_init_fields_to_init_dict(self, init_fields):
        """将init_fields转为init_dict
        para: 
            init_fields: [ip, pwd, port, ip, pwd, port] 转为
        return:
            init_dict: {
                "ip": {
                    "root_password": pwd, 
                    "port": port
                }
             }
        """
        init_list=self._trans_init_fields_to_init_list(init_fields)
        init_dict=self._trans_init_list_to_init_dict(init_list)
        return init_dict

    def get_hosts_list(self, arch_dict):
        """ 获取所有hosts
        return:
            hosts_list: ["ip node", "ip node"]
        """
        hosts_list=[]
        for node in arch_dict:
            hosts_list.append(f"{arch_dict[node].get('ip')} {node}")
        return hosts_list

    def check_local_node(self, local_ip, arch_dict):
        """校验本机ip是否在arch中
        return: local_node
        """
        for node in arch_dict:
            if local_ip == arch_dict[node]["ip"]:
                local_node=node
                break
        else:
            local_node=""
        return local_node

    def config_init(self, title, init_dict, local_flag):
        """配置init_dict
        para:
            title:
            init_dict:
            local_flag: 是否本地部署(只配置一个ip信息)
        return:
            bool: 确认/取消 
            init_dict
        """
        init_list=self._trans_init_dict_to_init_list(init_dict)
        while True:                     # 添加node信息
            code, init_fields=self.edit_host_account_info(title, init_list, local_flag)
            if code==self.d.OK:
                init_dict=self._trans_init_fields_to_init_dict(init_fields)
                code=self.show_host_account_info(title, init_dict)
                if code==self.d.OK:
                    return True, init_dict
                else:                       # 修改
                    init_list=self._trans_init_dict_to_init_list(init_dict)
                    continue
            elif code==self.d.EXTRA:        # 继续添加按钮
                init_list=self._trans_init_fields_to_init_list(init_fields)
                new_ip=f'{".".join(init_list[-1][0].split(".")[:-1])}.'
                new_pwd=init_list[-1][1]
                new_port=init_list[-1][2]
                new_account_info=(new_ip, new_pwd, new_port)          # 添加一个空的主机信息
                init_list.append(new_account_info)
            else:                           # 取消
                return False, {}

    def config_update_init(self, title, init_dict, not_init_node_num):
        """配置update_init_dict
        return:
            bool, add_init_dict
        """
        add_init_list=[]
        for _ in range(not_init_node_num):
            add_init_list.append(())
        init_list=self._trans_init_dict_to_init_list(init_dict)
        while True:
            code, add_init_fields=self.edit_added_host_account_info(title, init_list, add_init_list)
            if code==self.d.OK:
                add_init_dict=self._trans_init_fields_to_init_dict(add_init_fields)
                code=self.show_host_account_info(title, add_init_dict)
                if code==self.d.OK:
                    return True, add_init_dict
                else:
                    add_init_list=self._trans_init_dict_to_init_list(add_init_dict)
                    continue
            else:
                return False, {}

    def config_check_bak(self, title, arch_dict):
        """配置check_dict
        return:
            check_dict          # {}代表不配置
        """
        self.log.logger.debug("检测巡检配置:")
        check_dict=self._get_check_info(arch_dict)
        self.log.logger.debug(f"{check_dict=}")
        if len(check_dict)!=0:
            while True:
                code, check_info_list=self.edit_check_config(title, check_dict)
                self.log.logger.debug(f"{check_info_list=}")
                if code==self.d.OK:         # 确认
                    code=self.show_check_config(title, check_info_list)
                    if code==self.d.OK:     # 确认
                        check_dict={
                                "project_name": check_info_list[0], 
                                "timing": check_info_list[1], 
                                "sender": check_info_list[2], 
                                "mail_list": [] if check_info_list[3] == "" else check_info_list[3].split(","), 
                                "sms_list": [] if check_info_list[4] == "" else check_info_list[4].split(",")
                                }
                        return check_dict
                    else:                   # 修改
                        continue
                else:   # 不配置
                    return {}
        return {}

    def stream_show(func):
        """输出流装饰器
        """
        def wrapper(self, title, **kwargs):
            read_fd, write_fd = os.pipe()
            child_pid = os.fork()

            if child_pid == 0:          # 进入子进程
                try:
                    os.close(read_fd)
                    with os.fdopen(write_fd, mode="w", buffering=1) as wfile:
                        self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)
                        result, result_dict=func(self, title, **kwargs)
                        #status, dict_=super(graphics_deploy, self).init(init_dict, ext_dict)
                        if result is True:
                            self.log.logger.info(f"{title}完成\n")
                        else:
                            self.log.logger.error(f"{title}失败: {result_dict}")
                            os._exit(error_code)
                    os._exit(normal_code)
                except Exception as e:
                    self.log.logger.error(str(e))
                    os._exit(error_code)
            os.close(write_fd)
            self.d.programbox(fd=read_fd, title=title, height=25, width=170, scrollbar=True)
            exit_info = os.waitpid(child_pid, 0)[1]
            if os.WIFEXITED(exit_info):
                exit_code = os.WEXITSTATUS(exit_info)
                return True, exit_code
            elif os.WIFSIGNALED(exit_info):
                self.d.msgbox(f"子进程被被信号'{exit_code}中断', 将返回菜单", width=40, height=5)
                return False, error_code
            else:
                self.d.msgbox("发生莫名错误, 请返回菜单重试", width=40, height=5)
                return False, error_code
        return wrapper

    @stream_show
    def init(self, title, **kwargs):
        """初始化过程显示
            * 检测主机账号配置
            * init
            * 获取主机信息
            * 主机信息写入文件
            * 验证国产化软件配置
        """
        init_result=True
        local_flag=kwargs.get("local_flag")
        init_dict=kwargs["init_dict"]
        ext_dict=kwargs["ext_dict"]
        localization_dict=kwargs["localization_dict"]

        if local_flag:
            self.log.logger.debug("local部署, 不检测主机配置信息")
        else:
            self.log.logger.info("检测主机配置, 请稍后...\n")
            result, connect_test_result=self.connect_test(init_dict)
            if not result:
                self.log.logger.error("主机信息配置有误, 请根据下方显示信息修改:")
                for node in connect_test_result:
                    if connect_test_result[node]["result"] != normal_code:
                        self.log.logger.error(f"{node}:\t{connect_test_result[node]['err_msg']}")
                return False, {}

        result, dict_=super(graphics_deploy, self).init(init_dict, ext_dict, local_flag)
        if result is True:
            self.log.logger.info("初始化完成\n")
            get_result, all_host_info_dict=self.get_host_msg(init_dict)
            if get_result:
                time.tzset()                                    # 主机信息获取过程中会重置时区, 程序内重新获取时区信息

                self.log.logger.debug(f"写入{all_host_info_dict=}")
                result, msg=self.write_config(all_host_info_dict, host_info_file) # 进程间通信, 写入文件
                if not result:
                    self.log.logger.error(msg)
                    init_result=False
                    return init_result, {}

                if len(localization_dict) == 0:
                    self.log.logger.info("主机信息已获取, 请查看")
                else:
                    self.log.logger.info("主机信息已获取")
                    self.log.logger.info("软件配置信息检测...")
                    result, dict_=super(graphics_deploy, self).localization_test(init_dict, ext_dict, localization_dict)
                    if result is True:
                        self.log.logger.info("软件配置信息检测完成\n")
                    else:
                        self.log.logger.error(f"软件配置有误: {dict_}")
                        init_result=False
            else:
                init_result=False
                self.log.logger.error(f"主机信息获取失败: {all_host_info_dict}")
        else:
            self.log.logger.error(f"初始化失败: {dict_}")
            init_result=False
        return init_result, {}

    def adaptation_config(self, arch_dict, host_info_dict, localization_dict, init_dict):
        """适应配置文件, 并校验资源
        return:
            result: bool
            arch_dict
        """
        self.log.logger.info("适配配置文件:")
        # 将巡检信息写入arch_dict
        arch_dict=self._set_check_info(arch_dict, localization_dict)

        # 将keepalived写入arch_dict
        arch_dict=self._set_keepalived_info(arch_dict, localization_dict)

        # 资源校验适配
        result, arch_dict=self.node_adapter_ip(arch_dict, host_info_dict, localization_dict)

        # 为arch_dict中的备份信息添加参数
        if result:
            arch_dict=self._set_backup_tool_remote_info(arch_dict, init_dict)

        return result, arch_dict

    def manual_config(self, title, arch_dict):
        """图形: 国产化软件(未安装软件)配置
        return
            result: bool, 
            localization_dict:
                {
                    "node":{
                        "software": ["dameng", "shentong"], 
                        "ip": xxx, 
                        "dameng_info": {
                            "db_ip": ip, 
                            "system_user": user, 
                            "dba_user": sysdba, 
                            "dba_password": xxxx, 
                            "db_port": port, 
                            "start_command": xxxx, 
                            "stop_command": xxx
                        }
                        "shentong_info": {
                            "db_ip": ip, 
                            "system_user": user, 
                            "dba_user": sysdba, 
                            "dba_password": xxxx, 
                            "db_port": port, 
                            "start_command": xxxx, 
                            "stop_command": xxx
                        }
                    }
                }
        """
        self.log.logger.debug("检测手动配置信息:")
        localization_source_dict=self._get_localization_info()

        localization_dict={}
        autocheck_flag=False     # 是否已添加autocheck的标志, localization_dict里只存在一份autocheck
        keepalived_flag=False    # 是否已添加keepalived的标志, localization_dict里只存在一份keepalived
        # 配置软件默认值
        for node in arch_dict:
            for softname in arch_dict[node]["software"]:
                if softname in localization_soft_port:
                    if softname=="autocheck":
                        if not autocheck_flag:
                            soft_default_info={
                                    "project_name": "", 
                                    "timing": "18:30", 
                                    "sender": "", 
                                    "mail_list": [], 
                                    "sms_list": []
                                    }
                            autocheck_flag=True
                        else:
                            continue
                    elif softname=="keepalived":
                        if not keepalived_flag:
                            soft_default_info={
                                    "virtual_addr": "", 
                                    }
                            keepalived_flag=True
                        else:
                            continue
                    elif softname=="dameng":
                        soft_default_info={
                                "db_ip": "", 
                                "system_user": "dmdba", 
                                "dba_user": "sysdba",
                                "dba_password": "", 
                                "db_port": localization_soft_port[softname], 
                                "start_command": "systemctl start DmService" , 
                                "stop_command": "systemctl stop DmService"
                                }
                    elif softname=="kingbase":
                        soft_default_info={
                                "db_ip": "", 
                                "system_user": "dmdba", 
                                "dba_user": "kingbase",
                                "dba_password": "", 
                                "db_port": localization_soft_port[softname], 
                                "start_command": "su -l kingbase ''" , 
                                "stop_command": "su -l kingbase ''"
                                }
                    elif softname=="shentong":
                        soft_default_info={
                                "db_ip": "", 
                                "system_user": "root", 
                                "dba_user": "sysdba",
                                "dba_password": "szoscar55", 
                                "db_port": localization_soft_port[softname], 
                                "start_command": "/etc/init.d/oscardb_OSRDBd start" , 
                                "stop_command": "/etc/init.d/oscardb_OSRDBd stop"
                                }

                    if node not in localization_dict:
                        localization_dict[node]={}
                        localization_dict[node]["software"]=[]
                    localization_dict[node]["software"].append(softname)

                    if localization_source_dict.get(node) is None or localization_source_dict[node].get(f"{softname}_info") is None:
                        localization_dict[node][f"{softname}_info"]=soft_default_info
                    else:
                        localization_dict[node][f"{softname}_info"]=localization_source_dict[node][f"{softname}_info"]

        num=0         # 国产化软件数量序号
        temp_dict={}
        for node in localization_dict:
            for softname in localization_dict[node]["software"]:
                num+=1
                temp_dict[num]=[node, softname]

        N=len(temp_dict)        # 国产化软件个数
        while True:
            for num in temp_dict:
                node=temp_dict[num][0]
                softname=temp_dict[num][1]
                result, soft_manaul_dict=self.edit_localization_config(title, f"{num}/{N}", node, softname, localization_dict[node][f"{softname}_info"])
                self.log.logger.debug(f"{node}: {softname}: {soft_manaul_dict}")
                if result:
                    localization_dict[node][f"{softname}_info"]=soft_manaul_dict
                    if soft_manaul_dict.get("db_ip") is not None:           # 数据库ip赋值
                        localization_dict[node]["ip"]=soft_manaul_dict["db_ip"]
                    # 写入文件, 用于重新开始获取历史输入
                    self.log.logger.debug(f"写入{localization_file}")
                    result, msg=self.write_config(localization_dict, localization_file)
                    if result:
                        continue
                    else:
                        self.showmsg(msg, "Error")
                        return False, {}
                else:                       # 取消
                    return False, {}
            else:
                if len(localization_dict)==0:
                    return True, localization_dict
                else:
                    result=self.show_localization_config(title, localization_dict)
                    if result:
                        return result, localization_dict
                    else:   # 修改
                        continue

    def update_management(self, title):
        """图形: 更新管理: 更新 回滚
        """
        while True:
            menu={
                    "1": "更新", 
                    "2": "回滚", 
                    }

            code,tag=self.d.menu(f"", 
                    choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"])
                        ], 
                    title=title, 
                    width=48, 
                    height=6
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.update(menu[tag])
                if tag=="2":
                    self.rollback(menu[tag])
            else:
                break

    def update_init(self, title):
        """将in update_arch.json and not in arch.josn中的node添加到init.json
        """
        result, config_list=self.read_config(["init", "arch", "ext", "update_arch", "project", "check_dict"])
        if result:
            init_dict, arch_dict, ext_dict, update_arch_dict, project_dict, check_dict=config_list
            not_init_node=[]
            for node in update_arch_dict:
                if node not in arch_dict:
                    not_init_node.append(node)
            self.log.logger.debug(f"{not_init_node=}")

            not_init_node_num=len(not_init_node)
            add_init_dict={}
            if not_init_node_num != 0:
                result, add_init_dict=self.config_update_init(title, init_dict, not_init_node_num)
                if result:
                    result, not_pass_init_dict=self.account_verifi(add_init_dict)
                    if not result:
                        self._show_not_pass_init(not_pass_init_dict)
                        return False
                    else:
                        check_dict=self.config_check(title)
                else:
                    return False

                result, msg=self.write_config(check_dict, check_file)
                if not result:
                    self.log.logger.error(msg)
                    self.d.msgbox(msg)
                    return False

                result, exit_code=self.init_stream_show(title, add_init_dict, ext_dict)
                if not result:
                    return False
                else:
                    if exit_code==normal_code:
                        _, config_list=self.read_config(["host"])
                        host_info_dict=config_list[0]
                        code=self.show_hosts_info(host_info_dict)
                        if code==self.d.OK:             # 开始部署按钮
                            pass
                        else:                           # 终止部署按钮
                            return False
                    else:
                        return False

            update_add_arch_dict={}
            for node in update_arch_dict:
                if node not in arch_dict:
                    update_add_arch_dict[node]=update_arch_dict[node]
                else:
                    update_arch_dict[node]["ip"]=arch_dict[node]["ip"]
                    update_arch_dict[node]["located"]=arch_dict[node]["located"]

            if len(update_add_arch_dict) != 0:
                result, update_add_arch_dict, project_dict=self.adaptation_config(check_dict, update_add_arch_dict, project_dict, host_info_dict)
                if result:
                    update_arch_dict.update(update_add_arch_dict)
                else:
                    self._show_non_resource(update_arch_dict)

            for config in [(update_arch_dict, update_arch_file), (project_dict, project_file), (add_init_dict, update_init_file)]:
                result, msg=self.write_config(config[0], config[1])
                if not result:
                    self.log.logger.error(msg)
                    self.d.msgbox(msg)
                    return False
        else:
            self.log.logger.error(config_list)
            self.d.msgbox(config_list)
            return False
        return True

    def program_stop(self):
        """图形: 项目关闭
        """
        self.log.logger.info(self.str_to_title("项目关闭", 1))
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            result, dict_=super(graphics_deploy, self).program_stop(init_dict, arch_dict, ext_dict)
            if result:
                self.log.logger.info("项目关闭完成")
            else:
                self.log.logger.error("项目关闭失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def program_backup(self):
        """图形: 项目备份
        """
        self.log.logger.info(self.str_to_title("项目备份", 1))
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            result, dict_=super(graphics_deploy, self).program_backup(init_dict, arch_dict, ext_dict, global_backup_version)
            if result:
                self.log.logger.info("项目备份完成")
            else:
                self.log.logger.error("项目备份失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def config_merge(self):
        """图形: 配置文件合并
        """
        self.log.logger.info(self.str_to_title("配置文件合并", 1))
        result, config_list=self.read_config(["update_init"])
        if result:
            update_init_dict=config_list[0]
        else:
            update_init_dict={}
        result, config_list=self.read_config(["init", "arch", "update_arch"])
        if result:
            init_dict, arch_dict, update_arch_dict=config_list
            result, dict_=super(graphics_deploy, self).config_merge(init_dict, arch_dict, update_init_dict, update_arch_dict)
            if result:
                self.log.logger.info("配置文件合并完成")
            else:
                self.log.logger.error("配置文件合并失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def program_update(self):
        """图形: 项目更新
        """
        self.log.logger.info(self.str_to_title("项目更新", 1))
        result, config_list=self.read_config(["init", "arch", "ext", "update_init", "update_arch"])
        if result:
            init_dict, arch_dict, ext_dict, update_init_dict, update_arch_dict=config_list
            set_hosts_flag=True
            if len(update_init_dict) == 0:
                set_hosts_flag=False
            result, dict_=super(graphics_deploy, self).program_update(init_dict, arch_dict, ext_dict, update_arch_dict, set_hosts_flag)
            if result:
                self.log.logger.info("项目更新完成")
            else:
                self.log.logger.error("项目更新失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def updated_soft_run(self):
        """图形: 项目运行
        """
        self.log.logger.info(self.str_to_title("项目运行", 1))
        result, config_list=self.read_config(["init", "ext", "update_arch"])
        if result:
            init_dict, ext_dict, update_arch_dict=config_list
            result, dict_=super(graphics_deploy, self).updated_soft_run(init_dict, update_arch_dict, ext_dict)
            if result:
                self.log.logger.info("项目运行完成")
            else:
                self.log.logger.error("项目运行失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def program_start(self):
        """图形: 项目启动
        """
        self.log.logger.info(self.str_to_title("项目启动", 1))
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            result, dict_=super(graphics_deploy, self).program_start(init_dict, arch_dict, ext_dict)
            if result:
                self.log.logger.info("项目启动完成")
            else:
                self.log.logger.error("项目启动失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def update(self, title, rollback_flag=False):
        """图形: update_init, program_stop, program_backup, program_update, program_run, 
        """
        global global_backup_version
        global_backup_version=self.create_backup_version()
        rollback_version=self.trans_backup_version_to_date([global_backup_version])[0]
        code=self.d.yesno(f"此过程将会重启项目服务并备份数据.\n备份版本号: '{rollback_version}'.\n是否确认继续?", title="提醒") 
        if code != self.d.OK:
            return

        if rollback_flag:
            fun_name="回滚"
            self.log.logger.info(f"回滚更新配置")
            result, msg=self.rollback_update_file()
            if not result:
                error_msg=f"更新配置回滚失败: {msg}"
                self.log.logger.error(msg)
                self.d.msgbox(msg)
                return
        else:
            fun_name="更新"

        if not self.update_init(title):
            return

        # 显示更新架构
        result, config_list=self.read_config(["update_arch"])
        if result:
            update_arch_dict=config_list[0]
            code=self.show_arch_summary(title, update_arch_dict)
            if code != self.d.OK:
                return
        else:
            msg=config_list
            self.log.logger.error(msg)
            self.d.msgbox(msg)
            return

        if rollback_flag:
            stage_method={
                    "program_stop": self.program_stop, 
                    "program_backup": self.program_backup, 
                    "rollback_arch": self.rollback_arch_file, 
                    "program_merge": self.config_merge, 
                    "program_update": self.program_update, 
                    "updated_soft_run": self.updated_soft_run, 
                    "program_start": self.program_start
                    }
        else:
            stage_method={
                    "program_stop": self.program_stop, 
                    "program_backup": self.program_backup, 
                    "program_merge": self.config_merge, 
                    "program_update": self.program_update, 
                    "updated_soft_run": self.updated_soft_run, 
                    "program_start": self.program_start
                    }

        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            try:
                os.close(read_fd)
                with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                    self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)
                    for stage in stage_method:
                        result, dict_=stage_method[stage]()
                        self.log.logger.debug(f"{stage}: {result}, {dict_}")
                        if result:
                            continue
                        else:
                            self.log.logger.error(f"'{stage}'阶段执行失败: {dict_}")
                            os._exit(error_code)
                    else:
                        backup_version_list=self.get_backup_version_list()
                        backup_version_list.append(global_backup_version)
                        result, msg=self.write_config(backup_version_list, backup_version_file)
                        if result:
                            self.log.logger.debug(f"记录备份版本: {global_backup_version}")
                            self.log.logger.info(f"项目{fun_name}完成")
                        else:
                            self.log.logger.error(msg)
                            os._exit(error_code)
                os._exit(normal_code)
            except Exception as e:
                self.log.logger.error(str(e))
                os._exit(error_code)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=25, width=170)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单", width=40, height=5)
            self.show_menu()
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试", width=40, height=5)
            self.show_menu()

    def rollback(self, title):
        """图形: 回滚
        """
        rollback_version_list=self.get_rollback_version_list()
        if len(rollback_version_list)==0:
            self.d.msgbox("尚未有回滚备份", title="提示")
            return
        else:
            choices=[]
            for rollback_version in reversed(rollback_version_list):
                choices.append((rollback_version, ""))

            code,tag=self.d.menu(f"请选择回滚版本(备份时间)", 
                    choices=choices, 
                    title=title, 
                    width=48, 
                    height=8
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, 写入{tag=}")
                result, msg=self.write_config(tag, rollback_version_file)
                if result:
                    self.update(title, rollback_flag=True)
                else:
                    self.log.logger.error(msg)
                    self.d.msgbox(msg)
                    return
            else:
                return

    def install(self):
        """图形: 安装
        """
        self.log.logger.info(self.str_to_title("集群安装", 1))
        result, config_list=self.read_config(["init", "arch", "ext", "hosts"])
        if result:
            init_dict, arch_dict, ext_dict, hosts_dict=config_list
            result, dict_=super(graphics_deploy, self).install(init_dict, arch_dict, ext_dict, hosts_dict["hosts_list"])
            if result:
                self.log.logger.info("集群安装完成")
            else:
                self.log.logger.error("集群安装失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def run(self):
        """图形: 运行
        """
        self.log.logger.info(self.str_to_title("集群启动", 1))
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            result, dict_=super(graphics_deploy, self).run(init_dict, arch_dict, ext_dict)
            if result:
                self.log.logger.info("集群启动完成")
            else:
                self.log.logger.error("集群启动失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def generate_deploy_file(self):
        """生成部署信息文件
        """
        result, config_list=self.read_config(["init", "arch", "host", "project"])
        if not result:
            return False, config_list

        init_dict, arch_dict, host_info_dict, project_dict=config_list
        deploy_dict={
                "project_id": project_dict.get("project_id"), 
                "project_name": project_dict.get("project_name"), 
                "mode": "deploy", 
                "stats": {
                    "init": init_dict, 
                    "arch": arch_dict, 
                    "host": host_info_dict
                    }
                }
        result, msg=self.write_config(deploy_dict, deploy_file)
        if result:
            self.log.logger.info(f"请将文件'{os.path.abspath(deploy_file)}'上传至Dreamone平台!")
            return True, {"Sucessful": True}
        else:
            return False, msg

    def edit_arch_ip_and_located(self, title, arch_dict, located_is_show=True, readonly=False, msg="", ok_label="确认", cancel_label="返回"):
        """编辑arch_dict
        return: 
            bool            # True: 确认, False: 取消/修改
            arch_dict       
        """
        SHOW=0x0
        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi=15
        field_length=45
        ip_field_length=15
        separator="*"
        if readonly:
            ATTRIBUTE=READ_ONLY
        else:
            ATTRIBUTE=SHOW
        while True:
            n=0
            elements=[]
            node_list=[]
            for node in arch_dict:
                node_list.append(node)
                n=n+1
                ip=arch_dict[node].get("ip")
                if ip is None:
                    ip=""
                    
                info=[
                        ("主机名: ", n, 1, node, n, xi, field_length, 0, READ_ONLY), 
                        (f"IP: ", n+1, tab, ip, n+1, xi, ip_field_length, 0, ATTRIBUTE)
                        ]
                n=n+2

                if located_is_show:  # 显示located
                    located=arch_dict[node].get("located")
                    if located is None:
                        located=""
                    info.append(("安装目录: ", n, tab, located, n, xi, field_length, 0, ATTRIBUTE))
                    n=n+1

                # 显示softname
                softname_str=",".join(arch_dict[node]["software"])
                row_chars=40
                rows=math.ceil(len(softname_str)/row_chars)
                for i in range(rows):
                    if i == 0:
                        element_name="安装软件: "
                    else:
                        element_name=""
                    info.append(
                            (element_name, n+i, tab, softname_str[i*row_chars:(i+1)*row_chars], n+i, xi, field_length, 0, READ_ONLY), 
                            )
                else:
                    n=n+i
                    info.append(("", n+1, 1, separator, n+1, xi, field_length, 0, HIDDEN))
                    n=n+1
                elements.extend(info)
            code, data_list = self.d.mixedform(msg, elements=elements, title=title, ok_label=ok_label, cancel_label=cancel_label, width=70)
            if code==self.d.OK:
                self.log.logger.debug(f"{ok_label}: {data_list=}")
                if not readonly:
                    blank_flag=False
                    separator_index_list=[]
                    data_list.insert(0, separator)
                    for i in range(data_list.count(separator)):
                        separator_index_list.append(data_list.index(separator))
                    for n in range(len(data_list)):
                        if n in separator_index_list:
                            node=data_list[n+1]
                            ip=data_list[n+2].strip()
                            arch_dict[node]["ip"]=ip
                            if located_is_show:
                                located=data_list[n+3].strip()
                                arch_dict[node]["located"]=located
                                if located == "":
                                    blank_flag=True
                            if ip == "":
                                blank_flag=True
                    if blank_flag:
                        msg=f"{msg}\n警告: 有未填写信息!"
                        self.log.logger.warning("有未填写信息")
                        continue
                return True, arch_dict
            else:
                self.log.logger.debug(f"{cancel_label}: {data_list=}")
                return False, arch_dict

    @stream_show
    def g_deploy(self, title):
        """
        """
        stage_all=["install", "run", "generate_deploy_file"]
        stage_method={
                "install": self.install, 
                "run": self.run, 
                "generate_deploy_file": self.generate_deploy_file
                }
        for stage in stage_all:
            result, dict_ = stage_method[stage]()
            self.log.logger.debug(f"'{stage}': {result}, {dict_}")
            if result:
                continue
            else:
                self.log.logger.error(f"'{stage}'阶段执行失败: {dict_}")
                break
        return result, dict_

    def deploy(self, title, deploy_type):
        """图形: init, install, run, generate_deploy_file
        """
        # get ext, arch config
        result, config_list=self.read_config(["ext", "arch", "project"])
        if result:
            ext_dict, arch_dict, project_dict=config_list
            result, config_list=self.read_config(["init"])
            if result:
                init_dict=config_list[0]
            else:
                init_dict={}
        else:
            self.log.logger.error(config_list)
            self.showmsg(config_list, "Error")
            return

        # init
        hosts_list=[]               # hosts list
        local_node = ""             
        if deploy_type=="remote":
            while True:
                result, init_dict=self.config_init(title, init_dict, local_flag=False)
                self.log.logger.debug(f"{init_dict=}")
                if result:
                    result, localization_dict=self.manual_config(title, arch_dict)
                    self.log.logger.debug(f"{localization_dict=}")
                    if result:
                        result, code=self.init("集群初始化", init_dict=init_dict, localization_dict=localization_dict, ext_dict=ext_dict, local_flag=False)
                        if result and code==normal_code:
                            break
                        elif result and code!=normal_code:
                            continue
                return
        elif deploy_type=="local":
            while True:
                result, arch_dict=self.edit_arch_ip_and_located(title, arch_dict, located_is_show=False, msg="请填写集群IP", ok_label="确认", cancel_label="返回")
                self.log.logger.debug(f"{arch_dict=}")
                if result:
                    hosts_list=self.get_hosts_list(arch_dict)
                    self.log.logger.debug(f"{hosts_list=}")

                    result, init_dict=self.config_init(title, init_dict, local_flag=True)
                    self.log.logger.debug(f"{init_dict=}")
                    if result:
                        local_ip=list(init_dict.keys())[0]
                        local_node=self.check_local_node(local_ip, arch_dict)
                        if local_node == "":
                            self.showmsg("当前主机IP不在集群IP中", "ERROR")
                            continue

                        arch_dict=self._get_local_arch_dict(arch_dict, local_node)
                        self.log.logger.debug(f"{arch_dict=}")

                        result, localization_dict=self.manual_config(title, arch_dict)
                        self.log.logger.debug(f"{localization_dict=}")
                        if result:
                            result, code=self.init("本机初始化", init_dict=init_dict, localization_dict=localization_dict, ext_dict=ext_dict, local_flag=True)
                            if result and code==normal_code:
                                break
                            elif result and code!=normal_code:
                                continue
                return
        elif deploy_type=="soft_install":
            result, config_list=self.read_config(["stand_alone"])
            if result:
                arch_dict=config_list[0]
            else:
                self.log.logger.error(config_list)
                self.showmsg(config_list, "Error")
                return

            soft_list=[]
            msg="选择软件:"
            for softname in ext_dict:
                if ext_dict[softname].get("file") is not None and softname not in ("python3", "keepalived", "tomcat", "redis6", "glusterfs-server", "glusterfs-client", "autocheck", "nacos_mysql_sql"):
                    soft_list.append((softname, "", 0))
            while True:
                code, choices_soft_list=self.d.checklist(msg, choices=soft_list, title=title, ok_label="确认", cancel_label="返回")
                self.log.logger.debug(f"{code=}, {choices_soft_list=}")
                if code==self.d.OK:
                    if len(choices_soft_list) != 0:
                        arch_dict["node"]["software"]=choices_soft_list
                        result, init_dict=self.config_init(title, init_dict, local_flag=True)
                        self.log.logger.debug(f"{init_dict=}")
                        if result:
                            result, localization_dict=self.manual_config(title, arch_dict)
                            self.log.logger.debug(f"{localization_dict=}")
                            if result:
                                result, code=self.init("本机初始化", init_dict=init_dict, localization_dict=localization_dict, ext_dict=ext_dict, local_flag=True)
                                if result and code==normal_code:
                                    break
                                elif result and code!=normal_code:
                                    continue
                    else:
                        msg=f"{msg}\n未选择软件!"
                        continue
                elif code==self.d.CANCEL:
                    return

        # get config
        result, config_list=self.read_config(["host"])
        if result:
            host_info_dict=config_list[0]
        else:
            self.log.logger.error(config_list)
            self.showmsg(config_list, "Error")
            return

        code=self.show_hosts_info(host_info_dict)
        if code==self.d.OK:
            self.log.logger.debug(f"配置适配前: {arch_dict=}, {init_dict=}")
            result, arch_dict=self.adaptation_config(arch_dict, host_info_dict, localization_dict, init_dict)
            if result:
                self.log.logger.info(f"适配配置文件后的{arch_dict=}")
                while True:
                    result, _=self.show_arch_summary(title, arch_dict, msg="请确认安装架构", ok_label="开始部署", cancel_label="修改")
                    if result:
                        break
                    else:
                        _, arch_dict=self.edit_arch_ip_and_located(title, arch_dict, msg="集群修改", ok_label="确认", cancel_label="返回")
                        continue
            else:
                self._show_non_resource(arch_dict)
                return
        else:
            return

        if len(hosts_list) ==0:   # remote deploy
            hosts_list=self.get_hosts_list(arch_dict)
            self.log.logger.debug(f"{hosts_list=}")

        self.log.logger.info("配置写入文件:")
        hosts_dict={"hosts_list": hosts_list}
        local_dict={"local_node": local_node}
        for config in [(arch_dict, arch_file), (init_dict, init_file), (hosts_dict, hosts_file), (local_dict, local_file)]:
            self.log.logger.debug(f"写入{config[1]}")
            result, msg=self.write_config(config[0], config[1])
            if not result:
                self.log.logger.error(msg)
                self.showmsg(msg, "Error")
                return False

        result, returncode=self.g_deploy(title)
        if result and returncode==normal_code:
            if deploy_type!="soft_install":
                self.show_project_url(project_dict)
                self.show_menu()
        else:
            self.d.msgbox("集群部署失败, 将返回菜单", width=35, height=5)
            self.show_menu()

    def cancel(self):
        """退出安装
        """
        self.d.msgbox(f"取消安装", title="提示")
        self.log.logger.info(f"退出安装")
        sys.exit(error_code)

    def show_menu(self):
        """主菜单
        """
        while True:
            menu={
                    "1": "部署", 
                    "2": "管理", 
                    "3": "查看", 
                    #"4": "更新" 
                    }
            code,tag=self.d.menu(f"若是首次进行部署, 请从\'{menu['1']}\'依次开始:", 
                    choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ("3", menu["3"]), 
                        #("4", menu["4"])
                        ], 
                    title="主菜单", 
                    width=48
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.deploy_menu(menu[tag])
                if tag=="2":
                    self.management(menu[tag])
                if tag=="3":
                    self.query(menu[tag])
                if tag=="5":
                    self.info_query(menu[tag])
                if tag=="4":
                    self.update_management(menu[tag])
                self.d.infobox(f"{menu[tag]}结束, 将返回主菜单...", title="提示", width=40, height=4)
                time.sleep(1)
            else:
                self.cancel()

    def deploy_menu(self, title):
        """部署菜单
        """
        while True:
            menu={
                    "1": "典型部署", 
                    "2": "自定义部署", 
                    "3": "软件安装", 
                    }
            code,tag=self.d.menu(f"", 
                    choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]), 
                        ("3", menu["3"])
                        ], 
                    title=title, 
                    height=6, 
                    width=48
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.deploy(menu[tag], "remote")
                if tag=="2":
                    self.deploy(menu[tag], "local")
                if tag=="3":
                    self.deploy(menu[tag], "soft_install")
            return

    def _get_check_info(self, arch_dict):
        """获取check_dict
        return: 
            check_dict={
                "project_name": "", 
                "timing": "18:30", 
                "sender": "", 
                "mail_list": [], 
                "sms_list": []
            }
        """
        check_softname="autocheck"      # 巡检软件名
        for node in arch_dict:
            if check_softname in arch_dict[node]["software"]:
                if arch_dict[node]["autocheck_info"].get("warning_info"):
                    check_dict={
                            "project_name": arch_dict[node]["autocheck_info"]["project_name"], 
                            "timing": arch_dict[node]["autocheck_info"]["inspection_info"].get("inspection_time"), 
                            "sender": arch_dict[node]["autocheck_info"]["warning_info"]["mail_info"]["mail_sender"], 
                            "mail_list": arch_dict[node]["autocheck_info"]["warning_info"]["mail_info"]["mail_receive"], 
                            "sms_list": arch_dict[node]["autocheck_info"]["warning_info"]["sms_info"]["sms_receive"]
                            }
                else:
                    check_dict={
                            "project_name": "", 
                            "timing": "18:30", 
                            "sender": "", 
                            "mail_list": [], 
                            "sms_list": []
                            }
        else:
            check_dict={}
        return check_dict

    def _get_localization_info(self):
        """获取国产化软件信息
        return:
            localization_dict={}    # {}表示无信息
        """
        result, config_list=self.read_config(["localization"])
        if result:
            localization_dict=config_list[0]
        else:
            localization_dict={}
        return localization_dict

    def _set_check_info(self, arch_dict, localization_dict):
        """ 根据check信息补充arch_dict
        check_dict={
            "project_name": "", 
            "timing": "18:30", 
            "sender": "", 
            "mail_list": [], 
            "sms_list": []
        }
        return: arch_dict
        """
        for node in localization_dict:
            if "autocheck" in localization_dict[node]["software"]:
                check_flag=True
                check_dict=localization_dict[node]["autocheck_info"]
                break
        else:
            check_flag=False

        self.log.logger.debug(f"{check_flag=}")
        if check_flag: # 补充arch_dict
            project_name=check_dict["project_name"]
            timing=check_dict["timing"]
            sender=check_dict["sender"]
            mail_list=check_dict["mail_list"]
            sms_list=check_dict["sms_list"] 
            for node in arch_dict:
                if "autocheck" not in arch_dict[node]["software"]:
                    arch_dict[node]["software"].append("autocheck")
                if len(mail_list)!=0:
                    if arch_dict[node].get("autocheck_info") is None:
                        arch_dict[node]["autocheck_info"]={}
                    arch_dict[node]["autocheck_info"]["inspection_info"]={}
                    arch_dict[node]["autocheck_info"]["inspection_info"]={
                            "inspection_time": timing, 
                            "inspection_sender": sender, 
                            "inspection_receive": mail_list, 
                            "inspection_subject": f"{project_name}巡检"
                            }
                    arch_dict[node]["autocheck_info"]["warning_info"]={}
                    arch_dict[node]["autocheck_info"]["warning_info"]["mail_info"]={
                            "mail_sender": sender, 
                            "mail_receive": mail_list, 
                            "mail_subject": f"{project_name}预警"
                            }
                if len(sms_list)!=0:
                    if arch_dict[node].get("autocheck_info") is None:
                        arch_dict[node]["autocheck_info"]={}
                    if arch_dict[node]["autocheck_info"].get("warning_info") is None:
                        arch_dict[node]["autocheck_info"]["warning_info"]={}
                    arch_dict[node]["autocheck_info"]["warning_info"]["sms_info"]={
                            "sms_receive": sms_list, 
                            "sms_subject": f"{project_name}预警"
                            }
        return arch_dict

    def _set_keepalived_info(self, arch_dict, localization_dict):
        """ 根据localization_dict信息补充arch_dict
        keepalived_dict={
            "virtual_addr": "", 
        }
        return: arch_dict
        """
        for node in localization_dict:
            if "keepalived" in localization_dict[node]["software"]:
                keepalived_flag=True
                keepalived_dict=localization_dict[node]["keepalived_info"]
                break
        else:
            keepalived_flag=False

        self.log.logger.debug(f"{keepalived_flag=}")
        if keepalived_flag: # 补充arch_dict
            virtual_addr=keepalived_dict["virtual_addr"]
            for node in arch_dict:
                if "keepalived" in arch_dict[node]["software"]:
                    arch_dict[node]["keepalived_info"]["virtual_addr"]=virtual_addr
                    continue
        return arch_dict

    def _set_backup_tool_remote_info(self, arch_dict, init_dict):
        """若有备份且有远程备份, 则为远程备份中的node添加相应的user, password, port
        """
        backup_tool_name="backup_tool"
        for node in arch_dict:
            if backup_tool_name in arch_dict[node]["software"]:
                for type_backup in arch_dict[node][f"{backup_tool_name}_info"]:
                    backup_type=arch_dict[node][f"{backup_tool_name}_info"][type_backup]["type"]
                    if backup_type == "mysql":
                        keyname_info={
                                "root_password": arch_dict[node][f"{backup_type}_info"]["db_info"]["root_password"]
                                }
                    elif backup_type=="dm" or backup_type=="kingbase" or backup_type=="shentong":
                        if backup_type=="dm":
                            backup_type="dameng"
                        keyname_info={
                                "system_user": arch_dict[node][f"{backup_type}_info"]["system_user"], 
                                "dba_password": arch_dict[node][f"{backup_type}_info"]["dba_password"], 
                                "dba_user": arch_dict[node][f"{backup_type}_info"]["dba_user"], 
                                }
                    else:
                        keyname_info={}

                    for keyname in arch_dict[node][f"{backup_tool_name}_info"][type_backup]:
                        if keyname != "type":
                            self.log.logger.debug(f"添加{keyname}的信息: {keyname_info}")
                            arch_dict[node][f"{backup_tool_name}_info"][type_backup][keyname].update(keyname_info)
                            if arch_dict[node][f"{backup_tool_name}_info"][type_backup][keyname].get("remote_backup") is not None:
                                self.log.logger.debug(f"为{node}添加{type_backup}的远程备份信息")
                                remote_backup_host=arch_dict[node][f"{backup_tool_name}_info"][type_backup][keyname]["remote_backup"]["remote_backup_host"]
                                arch_dict[node][f"{backup_tool_name}_info"][type_backup][keyname]["remote_backup"]["user"]="root"
                                arch_dict[node][f"{backup_tool_name}_info"][type_backup][keyname]["remote_backup"]["password"]=init_dict[arch_dict[node]["ip"]]["root_password"]
                                arch_dict[node][f"{backup_tool_name}_info"][type_backup][keyname]["remote_backup"]["port"]=init_dict[arch_dict[node]["ip"]]["port"]
        return arch_dict

    def info_query(self, title):
        """主机, 软件, 备份信息查看
        """
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
        else:
            self.log.logger.error(config_list)
            self.d.msgbox(config_list)
            return

        while True:
            menu={
                    "1": "主机", 
                    "2": "软件", 
                    "3": "备份"
                    }

            code,tag=self.d.menu("", choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ("3", menu["3"])
                        ], 
                    title=title, 
                    width=40, 
                    height=6
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.nodes_query(menu[tag], init_dict, arch_dict)
                if tag=="2":
                    self.soft_choice(menu[tag], "start")
                if tag=="3":
                    self.backup_choice(menu[tag], arch_dict)
            else:
                break

    def query(self, title):
        """
        """
        result, config_list=self.read_config(["arch", "project"])
        if result:
            arch_dict, project_dict=config_list
        else:
            self.log.logger.error(config_list)
            self.d.msgbox(config_list)
            return

        while True:
            menu={
                    "1": "项目地址", 
                    "2": "部署架构", 
                    }

            code,tag=self.d.menu("", choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ], 
                    title=title, 
                    width=40, 
                    height=6
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.show_project_url(project_dict)
                if tag=="2":
                    self.show_arch_summary(menu[tag], arch_dict, msg="", ok_label="确认", cancel_label="返回")
            else:
                break

    def backup_choice(self, title, arch_dict):
        """选择常规备份和更新备份
        """
        while True:
            menu={
                    "1": "日常备份", 
                    "2": "更新备份", 
                    }

            code,tag=self.d.menu("", choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ], 
                    title=title, 
                    width=40, 
                    height=6
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.show_crontab_backup(menu[tag], arch_dict)
                if tag=="2":
                    self.show_update_backup(menu[tag], arch_dict)
            else:
                break

    def show_crontab_backup(self, title, arch_dict):
        """显示定时备份
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi_1=20
        xi_2=30
        field_length=80

        backup_info_dict=self.get_backup_info(arch_dict, "crontab")
        self.log.logger.debug(f"{backup_info_dict=}")
        if len(backup_info_dict)==0:
            self.showmsg("未设置备份", "提示", width=20)
        else:
            n=0
            elements=[]
            for node in backup_info_dict:
                n=n+1
                elements.append((f"{node}: ", n, 1, "", n, xi_2, field_length, 0, HIDDEN))
                for backup_key in backup_info_dict[node]:
                    elements.append((f"{backup_key}: ", n+1, tab, "", n+1, xi_2, field_length, 0, HIDDEN))
                    elements.append(("本地备份地址: ", n+2, tab*2, backup_info_dict[node][backup_key]["local_backup_dir"], n+2, xi_1, field_length, 0, READ_ONLY))
                    elements.append(("远程备份地址: ", n+3, tab*2, backup_info_dict[node][backup_key]["remote_backup_dir"], n+3, xi_1, field_length, 0, READ_ONLY))
                    n=n+3
            elements.append(("", n+1, 1, "", n+1, xi_1, field_length, 0, HIDDEN))
            self.log.logger.debug(f"backup summary: {elements=}")
            code, _ = self.d.mixedform(f"日常备份信息:", title=title, elements=elements, ok_label="确认", no_cancel=True)
            return code

    def show_update_backup(self, title, arch_dict):
        """显示更新备份
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi_1=20
        xi_2=30
        field_length=80

        backup_info_dict=self.get_backup_info(arch_dict, "update")
        self.log.logger.debug(f"{backup_info_dict=}")
        if len(backup_info_dict)==0:
            self.showmsg("尚未有更新备份", "提示", width=20)
        else:
            n=1
            elements=[]
            elements.append(("localhost: ", n, 1, "", n, xi_2, field_length, 0, HIDDEN))
            elements.append(("更新备份地址: ", n+1, tab*2, backup_info_dict["backup_dir"], n+1, xi_1, field_length, 0, READ_ONLY))
            elements.append(("", n+2, 1, "", n+2, xi_1, field_length, 0, HIDDEN))
            self.log.logger.debug(f"backup summary: {elements=}")
            code, _ = self.d.mixedform(f"更新备份信息:", title=title, elements=elements, ok_label="确认", no_cancel=True)
            return code

    def nodes_query(self, title, init_dict, arch_dict):
        """主机查询
        """
        node_list=[]
        for node in arch_dict:
            node_list.append((node, ""))

        while True:
            code,tag=self.d.menu(f"选择节点", 
                    choices=node_list, 
                    title=title, 
                    width=48, 
                    cancel_label="返回", 
                    ok_label="选择" 
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                node_info_dict=self.node_query(tag, init_dict, arch_dict)
                self.node_info_show(node_info_dict)
            else:
                break

    def node_query(self, title, init_dict, arch_dict):
        """主机信息查询
        """
        return {}

    def node_info_show(self, node_info_dict):
        """主机信息显示
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi_1=17
        xi_2=25
        xi_3=38
        xi_4=50
        xi_5=62
        field_length=60
        elements=[]

        n=0
        all_host_info_dict=node_info_dict
        for ip in all_host_info_dict:
            n=n+1
            node_info_dict=all_host_info_dict[ip]
            if node_info_dict.get("error_info") is None:
                info=[
                        (f"{ip}: ", n, 1, "", n, xi_1, field_length, 0, HIDDEN), 
                        ("内核版本: ", n+1, tab, node_info_dict["kernel_version"], n+1, xi_1-3, field_length, 0, READ_ONLY), 
                        ("发行版本: ", n+2, tab, node_info_dict["os_name"], n+2, xi_1-3, field_length, 0, READ_ONLY), 
                        ("CPU架构: ", n+3, tab, f"{node_info_dict['cpu_arch']}", n+3, xi_1-2, field_length, 0, READ_ONLY), 
                        ("CPU个数: ", n+3, xi_2, f"{node_info_dict['CPU'][0]}", n+3, xi_3, field_length, 0, READ_ONLY), 
                        ("CPU使用率: ", n+3, xi_4, f"{node_info_dict['CPU'][1]}%", n+3, xi_5, field_length, 0, READ_ONLY), 
                        ("内存大小: ", n+4, tab, format_size(node_info_dict['Mem'][0]), n+4, xi_1-2, field_length, 0, READ_ONLY), 
                        ("内存使用率: ", n+4, xi_2, f"{node_info_dict['Mem'][1]}%", n+4, xi_3, field_length, 0, READ_ONLY)
                        ]
                elements.extend(info)

                n=n+5
                elements.append(("磁盘: ", n, tab, "", n, xi_1, field_length, 0, HIDDEN))
                for disk in node_info_dict["Disk"]:
                    n=n+1
                    disk_info=[
                            ("挂载目录: ", n, tab*2, disk, n, xi_1-1, field_length, 0, READ_ONLY),
                            ("磁盘大小: ", n, xi_2+3, format_size(node_info_dict['Disk'][disk][0]), n, xi_3, field_length, 0, READ_ONLY), 
                            ("磁盘使用率: ", n, xi_4, f"{node_info_dict['Disk'][disk][1]}%", n, xi_5, field_length, 0, READ_ONLY)
                            ]
                    elements.extend(disk_info)
            else:
                error_msg=node_info_dict["error_info"]
                elements.append((ip, n, 1, error_msg, n, xi_1, field_length, 0, READ_ONLY))
        elements.append(("", n+1, 1, "", n+1, xi_1, field_length, 0, HIDDEN))
        self.log.logger.debug(f"host info summary: {elements=}")
        code, _ = self.d.mixedform(f"主机信息:", elements=elements, ok_label="确认")
        return code

    def management(self, title):
        """集群管理: 监控, 启动, 停止, 巡检, license注册
        """
        while True:
            menu={
                    "1": "状态", 
                    "2": "启动", 
                    "3": "停止", 
                    "4": "巡检", 
                    #"5": "license注册"
                    }

            code,tag=self.d.menu("", choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ("3", menu["3"]), 
                        ("4", menu["4"]), 
                        #("5", menu["5"])
                        ], 
                    title=title, 
                    width=40, 
                    height=6
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.monitor(menu[tag])
                if tag=="2":
                    self.status_management(menu[tag], "start")
                if tag=="3":
                    self.status_management(menu[tag], "stop")
                if tag=="4":
                    self.check(menu[tag])
                if tag=="5":
                    self.program_license_register_management(menu[tag])
            else:
                break

    def monitor(self, title):
        """图形: 显示软件状态
        """
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
        else:
            self.log.logger.error(config_list)
            self.d.msgbox(config_list)
            return

        soft_stats_dict=self.get_soft_status(init_dict, arch_dict, ext_dict)
        self.log.logger.debug(f"软件状态值: {soft_stats_dict}")

        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi=30
        field_length=10
        elements=[]

        status_value_msg_dict={
                activated_code: "正常", 
                stopped_code: "未启动", 
                abnormal_code:  "异常", 
                error_code:  "错误"
                }
        n=0
        for node in soft_stats_dict:
            n=n+1
            info=[
                    (f"{node}: ", n, 1, "", n, xi, field_length, 0, HIDDEN), 
                    ]
            for softname in soft_stats_dict[node]:
                status_value=soft_stats_dict[node][softname]
                info.extend(
                        [
                            (f"{softname}: ", n+1, tab, status_value_msg_dict[status_value], n+1, xi, field_length, 0, READ_ONLY), 
                        ]
                        )
                n=n+1
            elements.extend(info)

        elements.append(("", n+1, 1, "", n+1, xi, field_length, 0, HIDDEN))
        self.log.logger.debug(f"软件状态显示: {elements=}")
        code, _=self.d.mixedform(f"服务状态:", elements=elements, no_cancel=True, width=55)
        return code

    def show_choices_soft(self, title,  action, choices_soft_dict):
        """显示已选择的软件
        """
        if action=="start":
            action_msg="启动"
        elif action=="stop":
            action_msg="停止"
        msg=f"已选择准备{action_msg}的软件, 是否{action_msg} ?"

        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi=40
        field_length=10
        elements=[]

        n=0
        for node in choices_soft_dict:
            n=n+1
            info=[
                    (f"* {node}: ", n, 1, "", n, xi, field_length, 0, HIDDEN), 
                    ]
            for softname in choices_soft_dict[node]:
                info.extend(
                        [
                            (f"- {softname}", n+1, tab, "", n+1, xi, field_length, 0, READ_ONLY), 
                        ]
                        )
                n=n+1
            elements.extend(info)

        elements.append(("", n+1, 1, "", n+1, xi, field_length, 0, HIDDEN))
        self.log.logger.debug(f"{elements=}")
        code, _=self.d.mixedform(msg, title=title, elements=elements, width=40)
        return code

    def status_management(self, title, action):
        """图形: 管理界面start|stop
        """
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
        else:
            self.log.logger.error(f"{config_list}")
            self.d.msgbox(f"{config_list}")
            return

        control_dict={}         # start/stop dict

        if action=="start":
            help_msg="启动"
        elif action=="stop":
            help_msg="停止"

        node_list=[]            # 节点列表: [(node, ""), (node, "")]
        service_soft_dict={}    # 可以启停的服务列表(排除工具类软件): {node:[soft1, soft2], }
        for node in arch_dict:
            node_list.append((node, ""))
            service_soft_dict[node]=[]
            for softname in arch_dict[node]["software"]:
                port_list=self._get_soft_port_list(arch_dict, node, softname)
                if port_list[0] != tool_service_code:
                    service_soft_dict[node].append(softname)

        while True:
            code, node=self.d.menu(f"选择节点", 
                    choices=node_list, 
                    title=title, 
                    width=48, 
                    cancel_label="返回", 
                    ok_label="选择", 
                    help_button=True, 
                    help_label=help_msg
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {node=}")
                self.log.logger.info(f"选择{node}")

                node_soft_list=[]       # 选择软件列表
                for softname in service_soft_dict[node]:
                    if control_dict.get(node) is not None:      # 已操作的软件依旧显示
                        if softname in control_dict[node]:
                            node_soft_list.append((softname, "", 1))
                        else:
                            node_soft_list.append((softname, "", 0))
                    else:
                        node_soft_list.append((softname, "", 1))
                code, choices_soft_list=self.d.checklist(f"选择软件", choices=node_soft_list, title=title, ok_label="确认", cancel_label="放弃")

                self.log.logger.debug(f"{code=}, {choices_soft_list=}")
                if code==self.d.OK:
                    if len(choices_soft_list) != 0:
                        control_dict[node]=choices_soft_list
                elif code==self.d.CANCEL:
                    continue
            elif code==self.d.HELP:         # start|stop按钮
                if len(control_dict)==0:            # 默认全选
                    for node in service_soft_dict:
                        control_dict[node]=service_soft_dict[node]

                self.log.logger.debug("显示已选择的主机和软件:")
                code=self.show_choices_soft(title, action, control_dict)
                if code==self.d.OK:
                    self.status_management_exec(title, action=action, control_dict=control_dict, init_dict=init_dict, arch_dict=arch_dict, ext_dict=ext_dict)
                    return
            else:
                return

    @stream_show
    def status_management_exec(self, title, **kwargs):
        """图形: start|stop
        """
        action=kwargs["action"]
        control_dict=kwargs["control_dict"]
        init_dict=kwargs["init_dict"]
        arch_dict=kwargs["arch_dict"]
        ext_dict=kwargs["ext_dict"]
        if action=="start":
            result, dict_=self.start(control_dict, init_dict, arch_dict, ext_dict)
        elif action=="stop":
            result, dict_=self.stop(control_dict, init_dict, arch_dict, ext_dict)
        self.log.logger.debug(f"{action}: {result}, {dict_}")
        return result, dict_

    @stream_show
    def g_check(self, title, **kwargs):
        """
        """
        self.log.logger.info("开始巡检...")
        check_node_dict=kwargs["check_node_dict"]
        init_dict=kwargs["init_dict"]
        arch_dict=kwargs["arch_dict"]
        ext_dict=kwargs["ext_dict"]
        result, dict_, tarfile_=super(graphics_deploy, self).check(check_node_dict, init_dict, arch_dict, ext_dict)
        if result:
            self.log.logger.info("巡检完成")
            if tarfile_:
                self.log.logger.info(f"请获取巡检报告文件: '{os.path.abspath(tarfile_)}'")
        else:
            self.log.logger.error("巡检失败")
        return result, dict_

    def check(self, title):
        """图形: 巡检
        """
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
        else:
            self.log.logger.error(f"{config_list}")
            self.d.msgbox(f"{config_list}")
            return

        check_flag=True
        for node in arch_dict:
            if "autocheck" not in arch_dict[node]["software"]:
                check_flag=False
            break
        if not check_flag:
            self.showmsg("未配置巡检", title="提示", width=30)
            return

        node_list=[]
        for node in arch_dict:
            node_list.append((node, "", 1))

        while True:
            code, tag=self.d.checklist(f"选择节点", choices=node_list, title=title, ok_label="巡检", cancel_label="返回")
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                if len(tag)==0:
                    self.d.msgbox("未选择节点")
                    continue
                else:
                    check_node_dict={
                            "nodes": tag
                            }
                    break
            else:
                return
        self.g_check(title, check_node_dict=check_node_dict, arch_dict=arch_dict, ext_dict=ext_dict, init_dict=init_dict)

    @stream_show
    def g_program_license_register_management(self, title):
        """
        """
        stage_method={
                "program_stop": self.program_stop, 
                "program_license_register": self.program_license_register, 
                "program_start": self.program_start
                }
        for stage in stage_method:
            result, dict_=stage_method[stage]()
            self.log.logger.debug(f"{stage}: {result}, {dict_}")
            if result:
                continue
            else:
                self.log.logger.error(f"'{stage}'阶段执行失败: {dict_}")
                break
        else:
            self.log.logger.debug("删除上传license文件")
            os.remove(local_license_path)
        return result, dict_

    def program_license_register_management(self, title):
        """program注册license
        """
        if not os.path.exists(local_license_path):
            self.showmsg(f"'{local_license_path}'文件不存在", title="Error", height=5)
            return

        code=self.d.yesno(f"此过程将会重启项目服务.\n是否确认继续?", title="提醒", height=8) 
        if code == self.d.OK:
            self.g_program_license_register_management(title)
        else:
            return

    def program_license_register(self):
        """图形: licens注册
        """
        self.log.logger.info(self.str_to_title("节点注册", 1))
        result, config_list=self.read_config(["init", "arch"])
        if result:
            init_dict, arch_dict=config_list
            result, dict_=super(graphics_deploy, self).program_license_register(local_license_path, node_license_path, init_dict, arch_dict)
            if result:
                self.log.logger.info("节点注册完成")
            else:
                self.log.logger.error("节点注册失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_

    def _install_dialog(self):
        """安装dialog
        """
        msg="检测并配置dialog环境, 请稍等..."
        print(msg)
        self.log.logger.info(msg)
        dialog_dir=f"{ext_dir}/dialog"
        result, msg=pkg_install(dialog_dir, self.log)
        if result:
            return True
        else:
            self.log.logger.error(msg)
            return False

    def show(self):
        """说明
        """
        introduction=dedent("""
            本程序主要用来自动部署项目集群. 
            部署过程将使用方向键或Tab键进行选择, 【enter】键用来确认.

            在使用过程中严禁放大或缩小当前窗口 ! ! !
            也不要使用数字小键盘 !


            是否开始 ?
        """)

        self.log.logger.info("开始文本图形化部署")

        code=self.d.yesno(introduction, height=14, width=self.term_cols, title="说明")

        if code==self.d.OK:
            self.show_menu()
        else:
            self.cancel()

    def showmsg(self, msg, title, width=80, height=6):
        """msgbox显示
        """
        self.d.msgbox(msg, title=title, width=width, height=height)

    def show_project_url(self, project_dict):
        """显示首页地址
        """
        project_url_list=project_dict.get("project_url")
        project_name=project_dict.get("project_name")
        if project_url_list is None or project_name is None:
            self.showmsg(f"未配置项目地址", f"警告", height=5)
        else:
            project_url_str=""
            for project_url in project_url_list:
                try:
                    node=project_url.split(":")[1][2:]
                    ip=socket.gethostbyname(node)
                except Exception as e:
                    self.log.logger.error(f"{node}: {str(e)}")
                    node=""
                    ip=""
                project_url_str=f"{project_url_str}\n{project_url.replace(node, ip)}"
            self.showmsg(f"{project_url_str}", f"{project_name}项目地址", height=8)

class platform_deploy(Deploy):
    '''平台安装'''

    def __init__(self, project_id):
        super(platform_deploy, self).__init__()
        self.project_id=project_id
        self.log=Logger(
                {"platform": log_platform_level, "file": log_file_level}, 
                log_file=log_file, 
                logger_name="platform", 
                project_id=self.project_id
                )

    def init(self):
        """
        平台: 初始化
        """
        init_stats_dict={
                "project_id": self.project_id, 
                "mode": "init", 
                "result": None, 
                "stats": None, 
                "host_info": None
                }
        init_result=True
        self.log.logger.info("监测主机配置, 请稍后...\n")
        code, config_list=self.read_config(["init", "ext"])
        if code:
            init_dict, ext_dict=config_list
            result, connect_test_result=self.connect_test(init_dict)
            if not result:
                self.log.logger.error("主机信息配置有误, 请根据下方显示信息修改:")
                for node in connect_test_result:
                    if connect_test_result[node]["result"] != 0:
                        self.log.logger.error(f"{node}:\t{connect_test_result[node]['err_msg']}")
                init_result=False
            else:
                #local_python3_file=local_pkg_name_dict.get("python3")
                status, dict_=super(platform_deploy, self).init(init_dict, ext_dict)
                if status:
                    self.log.logger.info("初始化完成\n")
                    self.log.logger.info("获取主机信息中, 请稍后...")
                    all_host_info=self.get_host_msg(init_dict)
                    init_stats_dict["host_info"]=self.json_to_init_dict(all_host_info)
                else:
                    init_result=False
                    self.log.logger.error(f"初始化失败: {status}")
                init_stats_dict["stats"]=dict_
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            init_result=False
            
        init_stats_dict["result"]=init_result
        return init_stats_dict

    def install(self):
        """
        平台: 安装
        """
        install_stats_dict={
                "project_id": self.project_id, 
                "mode": "install", 
                "result": None, 
                "stats": None, 
                }
        install_result=True
        #result=self.update_extract(program_pkg, program_unzip_dir, ["project.json", "arch.json", "update.json", "start.json"])
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            self.log.logger.info("集群安装...")
            result, dict_=super(platform_deploy, self).install(init_dict, arch_dict, ext_dict)
            if result:
                self.log.logger.info("集群安装完成")
            else:
                self.log.logger.error("集群安装失败")
                install_result=False
            install_stats_dict["stats"]=dict_
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            install_result=False
        install_stats_dict["result"]=install_result
        return install_stats_dict

    def run(self):
        """
        平台: 运行
        """
        run_stats_dict={
                "project_id": self.project_id, 
                "mode": "run", 
                "result": None, 
                "stats": None, 
                }
        run_result=True
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            self.log.logger.info("集群启动...")
            result, dict_=super(platform_deploy, self).run(init_dict, arch_dict, ext_dict)
            if result:
                self.log.logger.info("集群启动完成")
            else:
                self.log.logger.error("集群启动失败")
                run_result=False
            run_stats_dict["stats"]=dict_
        else:
            self.log.logger.error(f"配置文件读取失败: {result}")
            run_result=False
        run_stats_dict["result"]=run_result
        return run_stats_dict

    def start(self):
        """
        平台: 启动
        """
        start_stats_dict={
                "project_id": self.project_id, 
                "mode": "start", 
                "result": None, 
                "stats": None, 
                }
        start_result=True
        result, config_list=self.read_config(["init", "arch", "ext", "start"])
        if result:
            init_dict, arch_dict, ext_dict, start_dict=config_list
            result, dict_=super(platform_deploy, self).start(start_dict, init_dict, arch_dict, ext_dict)
            if result:
                self.log.logger.info("启动完成")
            else:
                self.log.logger.error("启动失败")
            start_stats_dict["stats"]=dict_
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            start_result=False
        start_stats_dict["result"]=start_result
        return start_stats_dict

    def stop(self):
        """
        平台: 启动
        """
        stop_stats_dict={
                "project_id": self.project_id, 
                "mode": "stop", 
                "result": None, 
                "stats": None, 
                }
        stop_result=True
        result, config_list=self.read_config(["init", "arch", "ext", "stop"])
        if result:
            init_dict, arch_dict, ext_dict, stop_dict=result
            result, dict_=super(platform_deploy, self).stop(stop_dict, init_dict, arch_dict, ext_dict)
            if result:
                self.log.logger.info("停止完成")
            else:
                self.log.logger.error("停止失败")
            stop_stats_dict["stats"]=dict_
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            stop_result=False
        stop_stats_dict["result"]=stop_result
        return stop_stats_dict

    def update(self):
        """
        平台: 更新
        """
        update_stats_dict={
                "project_id": self.project_id, 
                "mode": "update", 
                "result": None, 
                "stats": None, 
                }
        update_result=True

        deploy_flag=True                   # 单独更新: 解压更新包, 放入update.json
        if update_pkg is not None:      
            deploy_flag=False
            if not self.update_extract(update_pkg, program_unzip_dir, ["update.json"]):
                sys.exit(error_code)

        code, result=self.read_config(["update"])
        if code:
            update_dict=result[0]
            if deploy_flag:
                msg="部署"
            else:
                msg="更新"

            self.log.logger.info(f"开始项目{msg}...")
            result, dict_=super(platform_deploy, self).update(update_dict)
            if result:
                self.log.logger.info(f"{msg}完成")
            else:
                self.log.logger.error(f"{msg}失败")
                update_result=False
            update_stats_dict["stats"]=dict_
        else:
            self.log.logger.error(f"配置文件读取失败: {result}")
            update_result=False
        update_stats_dict["result"]=update_result
        return update_stats_dict

    def deploy(self):
        """
        平台: install, run 
        """
        deploy_stats_dict={
                "project_id": self.project_id,
                "mode": "deploy",
                "result": None,
                "stats": {}
                }

        deploy_result=True
        stage_all=["install", "run"]
        stage_method={
                "install": self.install, 
                "run": self.run, 
                }
        for stage in stage_all:
            result_dict=stage_method[stage]()
            deploy_stats_dict["stats"][stage]=result_dict
            if result_dict["result"]:
                continue
            else:
                self.log.logger.error(f"'{stage}'阶段执行失败")
                deploy_result=False
                break
        deploy_stats_dict["result"]=deploy_result
        return deploy_stats_dict

    def monitor(self):
        """
        平台: 软件状态
        """
        monitor_stats_dict={
                "project_id": self.project_id, 
                "mode": "monitor", 
                "result": None, 
                "stats": None, 
                }
        monitor_result=True

        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            soft_status_dict=self.get_soft_status(init_dict, arch_dict, ext_dict)
            monitor_stats_dict["stats"]=soft_status_dict
            self.log.logger.debug(f"软件状态值: {soft_status_dict}")
        else:
            error_msg=f"配置文件读取失败: {config_list}"
            monitor_result=False
            self.log.logger.error(error_msg)
        monitor_stats_dict["result"]=monitor_result
        return monitor_stats_dict

    def check(self):
        """
        平台: 巡检
        """
        check_stats_dict={
                "project_id": self.project_id, 
                "mode": "check", 
                "result": None, 
                "stats": None, 
                }
        check_result=True
        result, config_list=self.read_config(["check", "init", "arch"])
        if result:
            check_dict, init_dict, arch_dict=config_list
            self.log.logger.info("开始巡检...\n")
            result, dict_, tarfile_=super(platform_deploy, self).check(check_dict, init_dict, arch_dict)
            if result:
                self.log.logger.info("巡检完成")
                if tarfile_:
                    data_dict={
                            "project_id": self.project_id, 
                            "file_": tarfile_
                            }
                    self.generate_info("platform_check", data_dict)
            else:
                self.log.logger.error("巡检失败")
                check_result=False
            check_stats_dict["stats"]=dict_
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            check_result=False
        check_stats_dict["result"]=check_result
        return check_stats_dict

