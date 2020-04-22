#!/opt/python3/bin/python3
# *-* coding:utf8 *-*
# sky

import sys, os, json
import tarfile

def install(soft_file, located):
    os.makedirs(located, exist_ok=1)

    try:
        t=tarfile.open(soft_file)
        t.extractall(path=located)
        return 1, "ok"
    except Exception as e:
        return 0, e

def main():
    weight, soft_file, conf_json=sys.argv[1:4]
    conf_dict=json.loads(conf_json)
    #print(f"{soft_file=}, {data_dict=}")

    # 安装
    located=conf_dict.get("located")
    value, msg=install(soft_file, located)
    if value==1:
        print("jdk安装完成")
    else:
        print(f"Error: 解压安装包失败: {msg}")
        return 

    # 配置
    for i in os.listdir(located):
        if i.startswith("jdk"):
            src=f"{located}/{i}"
    try:
        dst=f"{located}/jdk"
        os.symlink(src, dst)
        path=f"export JAVA_HOME={dst}\nexport PATH=$JAVA_HOME/bin:$PATH\n"
        with open("/etc/profile.d/jdk.sh", "w") as f:
            f.write(path)
    except Exception as e:
        print(f"Error: jdk配置出错: {e}")
    else:
        print(f"jdk配置完成")

if __name__ == "__main__":
    main()
