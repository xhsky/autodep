import os
import jinja2, json
from collections.abc import Iterable


# Generate a file from a template
def render(tpl_path, **kwargs):
    '''
    tpl_path: The path of conf template
    '''
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(loader=jinja2.FileSystemLoader(path or './')).get_template(filename).render(**kwargs)


# judge whether there is a single quotation mark in dict's values
def json_judge_single(a_dict):
    the_json = json.dumps(a_dict)
    if "'" in the_json:
        list_value = list(the_json)
        i = 0
        list_len = len(list_value)
        while i < list_len:
            if list_value[i] == "'":
                list_value.insert(i, "\\")
                i += 2
                list_len += 1
            else:
                i += 1
        a_json = "".join(list_value)
        return a_json
    else:
        return the_json



