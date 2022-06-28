import os
import jinja2


# Generate a file from a template
def render(tpl_path, **kwargs):
    '''
    tpl_path: The path of conf template
    '''
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(loader=jinja2.FileSystemLoader(path or './')).get_template(filename).render(**kwargs)
