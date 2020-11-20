#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-11-20 16:33:57
# sky

logs_dir="./logs"
log_file=f"{logs_dir}/autodep.log"

remote_python_transfer_dir="/tmp"
remote_python_install_dir="/opt"
remote_python_dir=f"{remote_python_install_dir}/python3"
remote_python_exec=f"{remote_python_dir}/bin/python3"

remote_code_dir=f"{remote_python_dir}/code"
remote_pkgs_dir=f"{remote_python_dir}/pkgs"

interface={
        "mail": ["smtp.dreamdt.cn", 25],        # 邮件接口
        "sms": ["smartone.10690007.com", 80],   # 短信接口
        "platform": ["", 80]                    # 公司平台接口
        }

