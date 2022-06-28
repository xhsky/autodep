#!/usr/bin/env python
# coding:utf8
# sky

class dict_to_md(object):
    def  __init__(self, project_name):
        self.out_md_file=f"{project_name}.md"
        self.project_name_md=f"# {project_name}"
        self.md_dict={
                self.project_name_md: {
                    "priority": 1
                    }
                }
        self.md_content=""

    def to_table(self, key_name, headers_list, dict_text):
        """
            header_list=[
                {header1: value1}, 
                {header2: value2}
            ]
        """
        md_table_text=f"{key_name}"
        for i in headers_list:
            md_table_text=f"{md_table_text}|{list(i.keys())[0]}"
        else:
            md_table_text=f"{md_table_text}\n"
            for i in range(0, len(headers_list)+1):
                md_table_text=f"{md_table_text}--|"

        for i in dict_text:
            md_table_text=f"{md_table_text}\n{i}"
            for j in headers_list:
                key=j[list(j.keys())[0]]
                md_table_text=f"{md_table_text}|{dict_text[i][key]}"

        return md_table_text

    @staticmethod
    def add_dict_value(dic, level_header_dict, value):
        """
            args={
                "level":["header1", priority], 
                "level":["header2", priority], 
            }
        """
        for level in sorted(level_header_dict):
            prefix="#" * int(level)
            header=level_header_dict[level][0]
            priority=level_header_dict[level][1]
            prefix_header=f"{prefix} {header}"
            dic=dic.setdefault(prefix_header, {
                    "priority": priority
                })
        else:
            if value is not None:
                dic["value"]=value

    @staticmethod
    def attach_content(content_list, list_type):
        content="\n"
        if list_type==1:
            for index, item in enumerate(content_list):
                index=index+1
                content=f"{content}{index}. {item}\n"
        elif list_type==-1:
            for item in content_list:
                content=f"{content}- {item}\n"
        return content
        
    def add_content(self, level_header_dict, content=None):
        self.add_dict_value(self.md_dict[self.project_name_md], level_header_dict, content)
    
    @staticmethod
    def sort_json(dict_text):
        sort_list=[]
        for i in dict_text:
            if i != "value" and i != "priority":
                sort_list.append([dict_text[i]["priority"], i])
        sort_list.sort(key=lambda x:x[0])
        return sort_list

    def generate_md(self, md_dict):
        for i in self.sort_json(md_dict):
            header_dict=md_dict[i[1]]
            self.md_content=f"{self.md_content}\n{i[1]}\n"
            value=header_dict.get("value")
            if value is not None:
                self.md_content=f"{self.md_content}\n{value}\n\n---\n"
            self.generate_md(header_dict)
    
    def write_to_file(self):
        self.generate_md(self.md_dict)
        with open(self.out_md_file, "w") as f:
            f.write(self.md_content)

if __name__ == "__main__":
    json_content={
            "# a":{
                "priority": 0, 
                "header1":{
                    "priority": 2, 
                    "content1":{
                        "priority": 2, 
                        "content1":{
                            "value": "信息: `aaaa`", 
                            "priority": 1
                        }
                    }, 
                    "content2":{
                        "value": "### bb1", 
                        "priority": 1, 
                    }, 
                }, 
                "header2":{
                    "priority": 1, 
                    "content1":{
                        "priority": 2, 
                        "content1":{
                            "value": "信息: `abbaaa`", 
                            "priority": 1
                        }
                    }, 
                    "content2":{
                        "value": "### bb1", 
                        "priority": 1, 
                    }, 
                }
            }
    }



