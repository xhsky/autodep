#!/usr/bin/env python
# *-* coding:utf8 *-*
# sky

import json

def main():
    with open("./config/init.json") as load_file:
        try:
            load_dict=json.load(load_file)
            print(load_dict)
        except json.decoder.JSONDecodeError:
            print("Error: json格式不正确")
    
if __name__ == "__main__":
    main()
