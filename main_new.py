#!/usr/bin/env python3
# *-* coding:utf8 *-*
# 2020-10-21 13:55:46
# sky

import sys
import getopt
from textwrap import dedent
from libs import deploy


def print_usage_info():
    usage_info=dedent(f"""
        Usage: {sys.argv[0]} OPTIONS [COMMAND]

        Options:
            -t, --text string          以文本方式安装
            -g, --graphics             以图形方式安装

        Connands:
            init                       文本方式初始化
            install                    文本方式安装
            start                      文本方式启动
    """)
    return usage_info

def main():
    try:
        options, args=getopt.getopt(sys.argv[1:], "t:gh", ["text=", "graphics", "help"])
    except getopt.GetoptError:
        print(print_usage_info())
        sys.exit(0)

    #print(f"{options=}, {args=}")

    if len(options)==0 or len(args)!=0:
        print(print_usage_info())
        exit()

    conf_file="./config/conf.json"
    init_file="./config/init.json"
    arch_file="./config/arch.json"
    project_file="./config/project"

    for opt, arg in options:
        if opt in ("-g", "--graphics"):
            d=deploy.graphics_deploy(conf_file, init_file, arch_file, project_file)
            d.show()
        elif opt in ("-t", "--text"):
            d=deploy.text_deploy(conf_file, init_file, arch_file, project_file)
            if arg=="init":
                d.init()
            elif arg=="install":
                d.install()
            elif arg=="start":
                d.start()
            else:
                print(print_usage_info())
        elif opt in ("-h", "--help"):
            print(print_usage_info())
        else:
            print(print_usage_info())

if __name__ == "__main__":
    main()
