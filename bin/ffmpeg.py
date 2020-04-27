#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import tarfile

def install(soft_file, located):
    os.makedirs(located, exist_ok=1)

    try:
        # 解压安装包
        t=tarfile.open(soft_file)
        t.extractall(path=located)
    except Exception as e:
        return 0, e

    # 安装rpm依赖
    pkgs=" ".join(os.listdir(f"{located}/ffmpeg/deps/"))
    result=os.system(f"cd {located}/ffmpeg/deps &> /dev/null && rpm -Uvh {pkgs} &> /dev/null")
    # 768 为重新安装返回码
    if  result == 0 or result == 768:
        return 1, "ok"
    else:
        return 0, "依赖包安装失败"

def main():
    weight, soft_file, conf_json=sys.argv[1:4]
    conf_dict=json.loads(conf_json)

    # 安装
    located=conf_dict.get("located")
    value, msg=install(soft_file, located)
    if value==1:
        print("ffmpeg安装完成")
    else:
        print(f"Error: 安装失败: {msg}")

if __name__ == "__main__":
    main()
