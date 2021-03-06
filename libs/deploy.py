#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 17:37:47
# sky

import locale, json, os, time, sys, tarfile, math, shutil, copy
from libs.env import logs_dir, log_file, log_file_level, log_console_level, log_platform_level, log_graphics_level, \
        remote_python_transfer_dir, remote_python_install_dir,  remote_python_exec, \
        remote_code_dir, remote_pkgs_dir, ext_dir, autodep_dir, backup_dir, \
        interface, test_mode, resource_verify_mode, backup_abs_file_format, rollback_abs_file_format, backup_soft_type, \
        host_info_file, init_stats_file, install_stats_file, start_stats_file, update_stats_file, run_stats_file, \
        rollback_dir, rollback_version_file, \
        g_term_rows, g_term_cols, \
        tool_service_code, portless_service_code, \
        located_dir_name, located_dir_link, autocheck_dst, report_dir, report_file_list, \
        init_file, arch_file, update_init_file, update_arch_file, start_file, stop_file, check_file, project_file, deploy_file, ext_file, backup_version_file, \
        normal_code, error_code, activated_code, stopped_code, abnormal_code

for dir_ in autodep_dir:
    if not os.path.exists(dir_):
        os.makedirs(dir_, exist_ok=1)

from textwrap import dedent
from libs.common import Logger, post_info, format_size, port_connect, exec_command
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
            elif config=="check":
                config_file=check_file
            elif config=="project":
                config_file=project_file
            elif config=="backup_version":
                config_file=backup_version_file
            elif config=="rollback_version":
                config_file=rollback_version_file
            elif config=="ext":
                config_file=ext_file
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
                json.dump(dict_, f, ensure_ascii=False)
            return True, ""
        except Exception as e:
            return False, str(e)

    def json_to_init_dict(self, all_host_info):
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

    def get_host_msg(self, init_dict):
        """获取主机信息
        """
        all_host_info={}
        get_msg_py="./bin/get_host_info.py"
        for node in init_dict:
            port=init_dict[node].get("port")
            remote_file=f"{remote_code_dir}/{get_msg_py.split('/')[-1]}"
            self.ssh_client.scp(node, port, "root", get_msg_py, remote_file)
            get_msg_command=f"{remote_python_exec} {remote_file}"
            self.log.logger.debug(f"获取{node}主机信息: {get_msg_command=}")
            status=self.ssh_client.exec(node, port, get_msg_command, get_pty=0)

            stdout_msg=status[1].read().strip().decode("utf8")
            stderr_msg=status[2].read().strip().decode("utf8")
            stats_value=status[1].channel.recv_exit_status()
            if  stats_value != normal_code:
                msg=stdout_msg
            else:
                msg=stderr_msg
            all_host_info[node]=[stats_value, msg]
        return all_host_info

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

    '''
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

    def _get_control_stats_dict_bak(self, env_control_stats_dict, program_control_stats_dict):
        """合并env和program的stats_dict
        """
        control_stats_dict={}
        if len(env_control_stats_dict) != 0:
            for node in env_control_stats_dict:
                control_stats_dict[node]=env_control_stats_dict[node]
                if program_control_stats_dict.get(node):
                    control_stats_dict[node].update(program_control_stats_dict[node])
        if len(program_control_stats_dict) != 0:
            program_control_stats_dict.update(control_stats_dict)
            control_stats_dict=program_control_stats_dict
        return control_stats_dict
    def program_control(self, init_dict, arch_dict, ext_dict, control_dict,  action):
        """项目start|stop
        return:
            program_stats_dict={
                "node1":{
                    "soft1": True|False
                }
            }
        """
        # 构造需要启动的节点及软件结构
        control_dict={}
        for node in arch_dict:
            control_dict[node]=arch_dict[node]["software"]
        soft_type_dict=self._divide_service(control_dict, ext_dict)

        if action=="start":
            msg="启动"
        elif action=="stop":
            msg="停止"

        program_result=True
        program_stats_dict={}
        for soft_type in reversed(soft_type_dict):
            if len(soft_type_dict[soft_type]) != 0:
                self.log.logger.info(self.str_to_title(f"{soft_type}服务{msg}", 2))
                program_result, type_stats_dict=self.nodes_control(soft_type_dict[soft_type], action, msg, init_dict, arch_dict, ext_dict)
                program_stats_dict[soft_type]=type_stats_dict
                if program_result:
                    if soft_type=="program":
                        break
                    else:
                        continue
                else:
                    break
        return program_result, program_stats_dict
    def update_bak(self, update_dict, program_dir, delete_flag, init_dict, arch_dict):
        """项目部署/更新
        return:
            update_stats_dict={
                "file": {
                    "node": True|False
                }
            }
        """
        update_result=True
        update_stats_dict={}
        for file_ in update_dict:
            file_abs=f"{program_dir}/{file_}"
            stats_value=True
            self.log.logger.info(f"{file_}部署")
            update_stats_dict[file_]={}
            if os.path.exists(file_abs):
                mode=update_dict[file_]["mode"]
                status, hosts_update_dict=update.update(mode, file_abs, program_dir, update_dict[file_]["update_info"], delete_flag, init_dict, arch_dict, self.log)
                if not status:
                    update_result=False
                update_stats_dict[file_]=hosts_update_dict
            else:
                self.log.logger.error(f"该文件{file_abs}不存在")
                update_result=False
                hosts_update_dict={}
            update_stats_dict[file_]=hosts_update_dict
        return update_result, update_stats_dict
    '''

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
        """
        if softname=="elasticsearch":
            mem=arch_dict[node]["elasticsearch_info"]["jvm_mem"]
        elif softname=="mysql":
            mem=arch_dict[node]["mysql_info"]["db_info"]["innodb_mem"]
        elif softname=="nginx":
            mem="1G"
            #self.arch_dict[node]["nginx_info"]["worker_processes"]=softname_cpu
        elif softname=="rabbitmq":
            mem=arch_dict[node]["rabbitmq_info"]["erlang_mem"]
        elif softname=="redis":
            mem=arch_dict[node]["redis_info"]["db_info"]["redis_mem"]
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

    def _get_max_disk_name(self, host_info_dict):
        """获取每个ip剩余空间最大的磁盘目录名称
        return { 
            ip: max_disk_name, 
            ip: max_disk_name, 
        }
        """
        max_disk_dict={}
        for ip in host_info_dict:
            disk_sorted=sorted(host_info_dict[ip]["Disk"].items(), key=lambda item:item[1][0]*(100-item[1][1]))
            max_disk_dict[ip]=disk_sorted[-1][0]
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

    def resource_verifi(self, arch_dict, host_info_dict):
        """根据模板中各节点安装软件的权重和 对应 集群中各节点权重和(排序对应), 并将将ip/located赋值给node配置
        return:
            True|False, arch_dict|non_resouce_dict
        """
        node_weights_dict={}
        ip_weights_dict={}

        # 获取节点权重
        for node in arch_dict:
            node_mem_weights=0
            node_cpu_weights=0
            for softname in arch_dict[node]["software"]:
                mem, cpu=self._get_soft_weights(arch_dict, node, softname)
                node_mem_weights=node_mem_weights+mem
                node_cpu_weights=node_cpu_weights+cpu
            node_weights_dict[node]=[node_mem_weights, node_cpu_weights]
        self.log.logger.debug(f"{node_weights_dict=}")

        # 获取ip权重
        for ip in host_info_dict:
            ip_weights_dict[ip]=[host_info_dict[ip]["Mem"][0], host_info_dict[ip]["CPU"][0]]
        self.log.logger.debug(f"{ip_weights_dict=}")

        # 节点与ip权重排序
        ip_weights_sort=[ x for x, y in sorted(ip_weights_dict.items(), key=lambda item:item[1][0])]
        node_weights_sort=[ x for x, y in sorted(node_weights_dict.items(), key=lambda item:item[1][0])]

        # 根据排序对应, 赋值
        for node, ip in zip(node_weights_sort, ip_weights_sort):
            arch_dict[node]["ip"]=ip
            self.log.logger.debug(f"{ip} <--> {node}")

        # 选择最大磁盘赋值
        max_disk_dict=self._get_max_disk_name(host_info_dict)
        for _ in arch_dict:
            max_disk_dir=f"{max_disk_dict[arch_dict[_]['ip']]}"
            if max_disk_dir.endswith("/"):
                located_dir=f"{max_disk_dir}{located_dir_name}"
            else:
                located_dir=f"{max_disk_dir}/{located_dir_name}"
            arch_dict[_]["located"]=located_dir
            self.log.logger.debug(f"{_} <--> {located_dir}")

        ## 资源大小验证
        non_resouce_dict={}
        if resource_verify_mode:
            for node in arch_dict:
                ip=arch_dict[node]["ip"]
                non_resouce_dict[ip]={}
                mem=ip_weights_dict[ip][0]-node_weights_dict[node][0]
                cpu=ip_weights_dict[ip][1]-node_weights_dict[node][1]
                if mem < 0:
                    non_resouce_flag=True
                    non_resouce_dict[ip]["Mem"]=node_weights_dict[node][0]
                if cpu < 0:
                    non_resouce_flag=True
                    non_resouce_dict[ip]["CPU"]=node_weights_dict[node][1]
        else:
            non_resouce_flag=False

        if not non_resouce_flag:
            return True, arch_dict
        else:
            return False, non_resouce_dict

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
        """
        for trans_file in trans_files_dict:
            src, dst=trans_files_dict[trans_file]
            self.log.logger.debug(f"传输文件: {trans_file}, {src=}, {dst=}")
            self.ssh_client.scp(ip, port, "root", src, dst)

        soft_control=soft(ip, port, self.ssh_client)
        if action=="init":
            status=soft_control.init(remote_py_file)
        elif action=="install":
            if trans_files_dict.get("pkg_file"):
                args_dict["pkg_file"]=trans_files_dict["pkg_file"][1]
            status=soft_control.install(remote_py_file, softname, args_dict)
        elif action=="run":
            status=soft_control.run(remote_py_file, softname, args_dict)
        elif action=="start":
            status=soft_control.start(remote_py_file, softname, args_dict)
        elif action=="stop":
            status=soft_control.stop(remote_py_file, softname, args_dict)
        elif action=="sendmail":
            status=soft_control.sendmail(remote_py_file, args_dict)
        elif action=="monitor":
            status=soft_control.monitor(remote_py_file, softname, args_dict)
        elif action=="backup":
            status=soft_control.backup(remote_py_file, softname, args_dict)
        return status

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
                #control_trans_files_dict=trans_files_dict.copy()
                control_trans_files_dict=copy.deepcopy(trans_files_dict)
                py_file=self.get_soft_info(softname, ext_dict, "py")
                remote_py_file=f"{remote_code_dir}/{py_file.split('/')[-1]}"
                if test_mode or action=="install":
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
                status=self.remote_exec(ip, port, softname, remote_py_file, action, control_trans_files_dict, arch_dict[node])
                for line in status[1]:
                    self.log.logger.info(line.strip())
                result_code=status[1].channel.recv_exit_status()
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

    def init(self, init_dict, ext_dict):
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
                self.log.logger.info(f"免密码登录设置完成")
                
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

    def install(self, init_dict, arch_dict, ext_dict):
        """软件安装
        return:
            install_stats_dict={
                "node1":{
                    "soft1": True|False
                }
            }
        """
        # 获取所有hosts
        hosts_list=[]
        for node in arch_dict:
            hosts_list.append(f"{arch_dict[node].get('ip')} {node}")

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
        """启动软件并初始化

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
        """软件start
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
        """软件stop
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
                    softname_info_dict=arch_dict[node].get(f"{softname}_info")
                    if  softname_info_dict is not None:
                        arch_dict[node][f"{softname}_info"]=update_arch_dict[node].get(f"{softname}_info")
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

    def program_run(self, init_dict, arch_dict, ext_dict, update_arch_dict):
        """项目运行
        """
        arch_program_above_type_dict=self._get_program_above_type_dict(arch_dict, ext_dict)
        control_dict={}
        for node in update_arch_dict:
            control_dict[node]=update_arch_dict[node]["software"]
        update_type_dict=self._divide_service(control_dict, ext_dict)

        # 将arch中软件类型:项目 以上的服务加入到update_arch_dict分类服务中以运行
        for soft_type in arch_program_above_type_dict:
            if soft_type in update_type_dict:
                for node in arch_program_above_type_dict[soft_type]:
                    if node in update_type_dict[soft_type]:
                        for softname in arch_program_above_type_dict[soft_type][node]:
                            if softname not in update_type_dict[soft_type][node]:
                                update_type_dict[soft_type][node].append(softname)
                    else:
                        update_type_dict[soft_type][node]=arch_program_above_type_dict[soft_type][node]
            else:
                update_type_dict[soft_type]=arch_program_above_type_dict[soft_type]
        self.log.logger.debug(f"{update_type_dict=}")

        run_result=True
        run_stats_dict={}
        for soft_type in update_type_dict:
            if len(update_type_dict[soft_type]) != 0:
                self.log.logger.info(f"***{soft_type}服务运行***")
                run_result, run_stats_dict=self.nodes_control(update_type_dict[soft_type], "run", "运行", init_dict, arch_dict, ext_dict)
                run_stats_dict[soft_type]=run_stats_dict
                if run_result:
                    continue
                else:
                    break
        return run_result, run_stats_dict

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
        elif softname=="rabbitmq":
            for port_name in arch_dict[node]["rabbitmq_info"]["port"]:
                port_list.append(arch_dict[node]["rabbitmq_info"]["port"][port_name])
        elif softname=="redis":
            port_list.append(arch_dict[node]["redis_info"]["db_info"]["redis_port"])
            if arch_dict[node]["redis_info"].get("sentinel_info"):
                port_list.append(arch_dict[node]["redis_info"]["sentinel_info"]["sentinel_port"])
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
        elif softname=="autocheck" or softname=="glusterfs-client":
            port_list.append(portless_service_code)
        else:
            port_list.append(tool_service_code)
        return port_list

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
            sys.exit(1)
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
    def program_start_bak(self):
        """图形: 项目启动
        """
        result, config_list=self.read_config(["init", "arch"])
        if result:
            init_dict, arch_dict=config_list
            result, dict_=super(graphics_deploy, self).program_control(init_dict, arch_dict, "start")
            #result, dict_=self.start(init_dict, arch_dict, start_dict)
            if result:
                self.log.logger.info("启动完成")
            else:
                self.log.logger.error("启动失败")
        else:
            self.log.logger.error(f"配置文件读取失败: {config_list}")
            dict_={}
        return result, dict_
    def configuration(self, title):
        """已丢弃
        集群配置: 
        """
        while True:
            menu={
                    "1": "主机检测", 
                    "2": "巡检配置"
                    }

            code,tag=self.d.menu("", choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"])
                        ], 
                    title=title, 
                    width=40, 
                    height=6, 
                    cancel_label="返回"
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.init(menu[tag])
                if tag=="2":
                    self.config_check(menu[tag])
            else:
                break
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

    def edit_host_account_info(self, title, init_list):
        """编辑主机账号信息
        """
        first_node_xi_length=20
        ip_field_length=15
        password_field_length=15
        port_field_length=5
        if init_list == []:
            elements=[
                    ("IP:", 1, 1, "192.168.0.1", 1, first_node_xi_length, ip_field_length, 0), 
                    ("root用户密码:", 2, 1, "", 2, first_node_xi_length, password_field_length, 0), 
                    ("ssh端口:", 3, 1, "22", 3, first_node_xi_length, port_field_length, 0), 
                    ]
            code, fields=self.d.form(f"请根据示例填写集群中主机信息\n\n第1台主机:", elements=elements, title=title, extra_button=True, extra_label="继续添加", ok_label="初始化", cancel_label="取消")
        else:
            elements=[]
            n=0
            for account_info in init_list:
                n=n+1
                elements.append(("IP:", n, 1, account_info[0], n, 5, ip_field_length, 0))
                elements.append(("root用户密码:", n, 22, account_info[1], n, 36, password_field_length, 0))
                elements.append(("ssh端口: ", n, 52, str(account_info[2]), n, 61, port_field_length, 0))
            code, fields=self.d.form(f"填写主机信息:", elements=elements, title=title, extra_button=True, extra_label="继续添加", ok_label="初始化", cancel_label="取消")
        self.log.logger.debug(f"主机信息: {code=}, {fields=}")
        return code, fields

    def edit_check_config(self, title, check_dict):
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

    def show_host_account_info(self, title, init_dict):
        """显示并确认主机账号信息
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

    def show_check_config(self, title, check_info_list):
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
        field_length=45
        elements=[]

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
        self.log.logger.debug(f"host info summary: {elements=}")
        code, _ = self.d.mixedform(f"请确认集群主机信息:", elements=elements, ok_label="开始部署", cancel_label="终止部署")
        return code

    def show_arch_summary(self, title, arch_dict):
        """显示arch_dict
        """
        HIDDEN = 0x1
        READ_ONLY = 0x2
        tab=3           # 
        xi=15
        field_length=45
        n=0
        elements=[]
        for node in arch_dict:
            n=n+1
            info=[
                    (f"{node}: ", n, 1, "", n, xi, field_length, 0, HIDDEN), 
                    (f"IP: ", n+1, tab, arch_dict[node]["ip"], n+1, xi, field_length, 0, READ_ONLY), 
                    ("安装目录: ", n+2, tab, arch_dict[node]["located"], n+2, xi, field_length, 0, READ_ONLY)
                    ]
            n=n+3
            m=0
            soft_nums=len(arch_dict[node]["software"])
            soft_nums_rows=1
            rows=math.ceil(soft_nums/soft_nums_rows)
            for i in range(rows):
                if i == 0:
                    element_name="安装软件: "
                else:
                    element_name=""
                info.append(
                        (element_name, n+i, tab, ", ".join(arch_dict[node]["software"][m:m+soft_nums_rows]), n+i, xi, field_length, 0, READ_ONLY), 
                        )
                m=m+soft_nums_rows
            n=n+i
            elements.extend(info)
        elements.append(("", n+1, 1, "", n+1, xi, field_length, 0, HIDDEN))
        self.log.logger.debug(f"arch summary: {elements=}")
        code, _ = self.d.mixedform(f"架构摘要:", elements=elements, title=title, ok_label="确认", cancel_label="终止部署")
        return code

    def _show_non_resource(self, non_resouce_dict):
        """显示资源不足的信息
        """
        msg=""
        for ip in non_resouce_dict:
            msg=f"{msg}\n* 主机({ip})至少需要:"
            mem=non_resouce_dict[ip].get("Mem")
            cpu=non_resouce_dict[ip].get("CPU")
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

    def _trans_init_dict_to_init_list(self, init_dict):
        """将init_dict转为有序的list显示
        """
        init_list=[]
        for ip in init_dict:
            init_list.append((ip, init_dict[ip]["root_password"], init_dict[ip]["port"]))
        return init_list

    def _trans_init_fields_to_init_list(self, init_fields):
        """ 将fields list: [ip, pwd, port, ip, pwd, port]
            转为init list: [(ip, pwd, port), (ip, pwd, port)]
        """
        init_list=[]
        for index, item in enumerate(init_fields):
            if index % 3 == 0:
                account_info=(init_fields[index], init_fields[index+1], int(init_fields[index+2]))
                init_list.append(account_info)
        return init_list

    def _trans_init_list_to_init_dict(self, init_list):
        """将init_list: [(ip, pwd, port), (ip, pwd, port)] 转为
             init_dict: {
                "ip": {
                    "root_password": pwd, 
                    "port": port
                }
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

    def _trans_init_fields_to_init_dict(self, init_fields):
        """将init_fields: [ip, pwd, port, ip, pwd, port] 转为
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

    def config_init(self, title, init_dict):
        """配置init_dict
        return:
            bool, init_dict
        """
        init_list=self._trans_init_dict_to_init_list(init_dict)
        while True:                     # 添加node信息
            code, init_fields=self.edit_host_account_info(title, init_list)
            if code==self.d.OK:
                init_dict=self._trans_init_fields_to_init_dict(init_fields)
                code=self.show_host_account_info(title, init_dict)
                if code==self.d.OK:
                    return True, init_dict
                else:
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

    def config_check(self, title):
        """配置check_dict
        return:
            check_dict          # {}代表不配置
        """
        check_dict=self._get_check_info()
        self.log.logger.debug(f"{check_dict=}")
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

    def init_stream_show(self, title, init_dict, ext_dict):
        """初始化过程显示
        """
        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            try:
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
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单", width=40, height=5)
            return False, error_code
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试", width=40, height=5)
            return False, error_code

    def adaptation_config(self, check_dict, arch_dict, project_dict, host_info_dict):
        """适应配置文件, 并校验资源
        """
        # 将check_dict信息写入arch_dict和project_dict
        if len(check_dict) != 0:
            arch_dict, project_dict=self._set_check_info(arch_dict, project_dict, check_dict)

        # 资源校验适配
        result, arch_dict=self.resource_verifi(arch_dict, host_info_dict)
        return result, arch_dict, project_dict

    def init(self, title, init_dict):
        """图形: 初始化
        """
        # 填写init.json并校验, 选填check.json
        result, init_dict=self.config_init(title, init_dict)
        if result:
            result, dict_=self.account_verifi(init_dict)
            if not result:
                self._show_not_pass_init(not_pass_init_dict)
                return False
            else:
                check_dict=self.config_check(title)
        else:
            return False

        for config in [(init_dict, init_file), (check_dict, check_file)]:
            result, msg=self.write_config(config[0], config[1])
            if not result:
                self.msgbox(msg)
                return False

        result, config_list=self.read_config(["init", "ext", "arch", "project", "check"])
        if result:
            init_dict, ext_dict, arch_dict, project_dict, check_dict=config_list
        else:
            self.log.logger.error(config_list)
            self.d.msgbox(config_list, title="警告", width=80, height=6)
            return False

        result, exit_code=self.init_stream_show(title, init_dict, ext_dict)
        if not result:
            return False
        else:
            if exit_code==normal_code:
                time.tzset()    # 主机信息获取过程中会重置时区, 程序内重新获取时区信息
                _, config_list=self.read_config(["host"])
                host_info_dict=config_list[0]
                code=self.show_hosts_info(host_info_dict)
                if code==self.d.OK:             # 开始部署按钮
                    result, arch_dict, project_dict=self.adaptation_config(check_dict, arch_dict, project_dict, host_info_dict)
                    if result:
                        for config in [(arch_dict, arch_file), (project_dict, project_file)]:
                            result, msg=self.write_config(config[0], config[1])
                            if not result:
                                self.log.logger.error(msg)
                                self.d.msgbox(msg)
                                return False
                    else:
                        self._show_non_resource(arch_dict)
                else:                           # 终止部署按钮
                    return False
                return True
            else:
                self.log.logger.error(f"{exit_code=}")
                return False

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

    def program_run(self):
        """图形: 项目运行
        """
        self.log.logger.info(self.str_to_title("项目运行", 1))
        result, config_list=self.read_config(["init", "arch", "ext", "update_arch"])
        if result:
            init_dict, arch_dict, ext_dict, update_arch_dict=config_list
            result, dict_=super(graphics_deploy, self).program_run(init_dict, arch_dict, ext_dict, update_arch_dict)
            if result:
                self.log.logger.info("项目运行完成")
            else:
                self.log.logger.error("项目运行失败")
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
                    "program_run": self.program_run
                    }
        else:
            stage_method={
                    "program_stop": self.program_stop, 
                    "program_backup": self.program_backup, 
                    "program_merge": self.config_merge, 
                    "program_update": self.program_update, 
                    "program_run": self.program_run
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
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
            result, dict_=super(graphics_deploy, self).install(init_dict, arch_dict, ext_dict)
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
            self.log.logger.info(f"请将文件'{os.path.abspath(deploy_file)}'上传至平台 !")
            return True, {"Sucessful": True}
        else:
            return False, msg

    def deploy(self, title):
        """图形: init, install, run, start, generate_deploy_file
        图形: init, install, run, program_update, program_start, generate_deploy_file
        """

        result, config_list=self.read_config(["init"])
        if result:
            init_dict=config_list[0]
        else:
            init_dict={}
        if not self.init(title, init_dict):
            return

        result, config_list=self.read_config(["arch"])
        if not result:
            self.d.msgbox(config_list)
            return
        else:
            arch_dict=config_list[0]

        code=self.show_arch_summary(title, arch_dict)
        if code != self.d.OK:
            return

        stage_all=["install", "run", "generate_deploy_file"]
        stage_method={
                "install": self.install, 
                "run": self.run, 
                "generate_deploy_file": self.generate_deploy_file
                }
        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            try:
                os.close(read_fd)
                with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                    self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)   
                    for stage in stage_all:
                        result, dict_ = stage_method[stage]()
                        self.log.logger.debug(f"'{stage}': {result}, {dict_}")
                        if result:
                            continue
                        else:
                            self.log.logger.error(f"'{stage}'阶段执行失败: {dict_}")
                            os._exit(error_code)
                    #else:   # 生成program.json文件
                    #    _, config_list=self.read_config(["update"])
                    #    result, msg=self.write_config(config_list[0], program_file)
                    #    if not result:
                    #        self.log.logger.error(msg)
                    #        os._exit(error_code)
                os._exit(normal_code)
            except Exception as e:
                self.log.logger.error(str(e))
                os._exit(error_code)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=30, width=180)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单", width=40, height=5)
            self.show_menu()
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试", width=40, height=5)
            self.show_menu()

        if exit_code==0:
            self.d.msgbox("集群部署完成, 将返回菜单", width=35, height=5)
            self.show_menu()
        else:
            self.d.msgbox("集群部署失败, 将返回菜单", width=35, height=5)
            self.show_menu()

    def cancel(self):
        """退出安装
        """
        self.d.msgbox(f"取消安装", title="提示")
        self.log.logger.info(f"退出安装")
        sys.exit(0)

    def show_menu(self):
        """主菜单
        """
        while True:
            menu={
                    "1": "部署", 
                    "2": "管理", 
                    "3": "更新"
                    }
            code,tag=self.d.menu(f"若是首次进行部署, 请从\'{menu['1']}\'依次开始:", 
                    choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ("3", menu["3"])
                        ], 
                    title="主菜单", 
                    width=48
                    )
            if code==self.d.OK:
                self.log.logger.debug(f"{code=}, {tag=}")
                self.log.logger.info(f"选择{menu[tag]}")
                if tag=="1":
                    self.deploy(menu[tag])
                if tag=="2":
                    self.management(menu[tag])
                if tag=="3":
                    self.update_management(menu[tag])
                self.d.infobox(f"{menu[tag]}结束, 将返回主菜单...", title="提示", width=40, height=4)
                time.sleep(1)
            else:
                self.cancel()

    def _get_check_info(self):
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
        check_dict_default={
                "project_name": "", 
                "timing": "18:30", 
                "sender": "", 
                "mail_list": [], 
                "sms_list": []
                }
        result, config_list=self.read_config(["check"])
        if result:
            check_dict=config_list[0]
            if len(check_dict)==0:
                check_dict=check_dict_default
        else:
            check_dict=check_dict_default
        return check_dict

    def _set_check_info(self, arch_dict, project_dict, check_dict):
        """ 根据check_dict补充arch_dict, project_dict
        check_dict={
            "project_name": "", 
            "timing": "18:30", 
            "sender": "", 
            "mail_list": [], 
            "sms_list": []
        }
        return: True, msg
        """
        project_name=check_dict["project_name"]
        timing=check_dict["timing"]
        sender=check_dict["sender"]
        mail_list=check_dict["mail_list"]
        sms_list=check_dict["sms_list"] 

        # 补充project.json
        project_dict["project_name"]=project_name

        # 补充arch_dict
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
        return arch_dict, project_dict

    def management(self, title):
        """集群管理: 监控, 启动, 停止, 巡检
        """
        while True:
            menu={
                    "1": "状态", 
                    "2": "启动", 
                    "3": "停止", 
                    "4": "巡检"
                    }

            code,tag=self.d.menu("", choices=[
                        ("1", menu["1"]), 
                        ("2", menu["2"]),
                        ("3", menu["3"]), 
                        ("4", menu["4"])
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

        node_list=[]            # 节点列表
        service_soft_dict={}    # 可以启停的服务列表(排除工具类软件)
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
                #for softname in arch_dict[node]["software"]:
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
                    #for node in arch_dict:
                    for node in service_soft_dict:
                        control_dict[node]=service_soft_dict[node]

                code=self.show_choices_soft(title, action, control_dict)
                if code==self.d.OK:
                    self.status_management_exec(title, action, control_dict, init_dict, arch_dict, ext_dict)
                    return
            else:
                return

    def status_management_exec(self, title, action, control_dict, init_dict, arch_dict, ext_dict):
        """图形: start|stop
        """
        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            try:
                os.close(read_fd)
                with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                    self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)   

                    #_, config_list=self.read_config(["init", "arch"])
                    #init_dict, arch_dict=config_list
                    if action=="start":
                        result, dict_=self.start(control_dict, init_dict, arch_dict, ext_dict)
                    elif action=="stop":
                        result, dict_=self.stop(control_dict, init_dict, arch_dict, ext_dict)
                    self.log.logger.debug(f"{action}: {result}, {dict_}")
                    if not result:
                        self.log.logger.error(f"'{action}'执行失败: {dict_}")
                        os._exit(error_code)
                os._exit(normal_code)
            except Exception as e:
                self.log.logger.error(str(e))
                os._exit(error_code)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=18, width=80)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单", width=40, height=5)
            self.show_menu()
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试", width=40, height=5)
            self.show_menu()

    def check(self, title):
        """图形: 巡检
        """
        result, config_list=self.read_config(["init", "arch", "ext"])
        if result:
            init_dict, arch_dict, ext_dict=config_list
        else:
            self.log.logger.error(f"{result}")
            self.d.msgbox(f"{result}")
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

        read_fd, write_fd = os.pipe()
        child_pid = os.fork()

        if child_pid == 0:          # 进入子进程
            try:
                os.close(read_fd)
                with os.fdopen(write_fd, mode="a", buffering=1) as wfile:
                    self.log=Logger({"graphical": log_graphics_level}, wfile=wfile)   
                    self.log.logger.info("开始巡检...")
                    status, dict_, tarfile_=super(graphics_deploy, self).check(check_node_dict, init_dict, arch_dict, ext_dict)
                    if result:
                        self.log.logger.info("巡检完成")
                        if tarfile_:
                            self.log.logger.info(f"请获取巡检报告文件: '{os.path.abspath(tarfile_)}'")
                    else:
                        self.log.logger.error("巡检失败")
                        os._exit(error_code)
                os._exit(normal_code)
            except Exception as e:
                self.log.logger.error(str(e))
                os._exit(error_code)
        os.close(write_fd)
        self.d.programbox(fd=read_fd, title=title, height=30, width=180)
        exit_info = os.waitpid(child_pid, 0)[1]
        if os.WIFEXITED(exit_info):
            exit_code = os.WEXITSTATUS(exit_info)
        elif os.WIFSIGNALED(exit_info):
            self.d.msgbox("子进程被被信号'{exit_code}中断', 将返回菜单", width=40, height=5)
            self.show_menu()
        else:
            self.d.msgbox("发生莫名错误, 请返回菜单重试", width=40, height=5)
            self.show_menu()

    def _install_dialog(self):
        """安装dialog
        """
        msg="检测并配置dialog环境, 请稍等..."
        self.log.logger.info(msg)
        command="rpm -qi dialog"
        result, msg=exec_command(command)
        self.log.logger.debug(command)
        if not result:
            command="rpm -Uvh ../ext/dialog/dialog-1.2-5.20130523.el7.x86_64.rpm"
            result, msg=exec_command(command)
            self.log.logger.debug(command)
            if result:
                return True
            else:
                return False
        else:
            return True

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
                sys.exit(1)

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

