#!/usr/bin/env python
import sys
import ast
import xml.etree.ElementTree as ET

def slurp(fname):
    with open(fname, 'r') as file:
        return file.read().encode('utf-8')

def calculate_offsets(source):
    result = [0]
    offset = 0
    for l in source.splitlines(keepends=True):
        offset += len(l)
        result.append(offset)
    return result

def to_offset(lineno, col_offset):
    return offsets[lineno - 1] + col_offset

def beg(node):
    if hasattr(node, 'beg'):
        return node.beg
    elif hasattr(node, 'lineno'):
        return to_offset(node.lineno, node.col_offset)
    else:
        return 0

def end(node):
    if hasattr(node, 'end'):
        return node.end
    elif hasattr(node, 'end_lineno'):
        return to_offset(node.end_lineno, node.end_col_offset)
    else:
        return len(source)

def text(beg, end):
    return source[beg:end].decode('utf-8')

def collect_child_nodes(node):
    result = []
    for key, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            if hasattr(value, 'beg'):
                result.append(value)
            else:
                result.extend(collect_child_nodes(value))
        elif isinstance(value, list):
            for e in value:
                if isinstance(e, ast.AST):
                    if hasattr(e, 'beg'):
                        result.append(e)
                    else:
                        result.extend(collect_child_nodes(e))
    return result

def attach_location(node):
    children = []
    for key, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            attach_location(value)
            children.append(value)
        elif isinstance(value, list):
            for e in value:
                if isinstance(e, ast.AST):
                    attach_location(e)
                    children.append(e)
    if hasattr(node, 'lineno'):
        node.beg = to_offset(node.lineno, node.col_offset)
        node.end = to_offset(node.end_lineno, node.end_col_offset)
    elif node.__class__.__name__ == 'Module':
        node.beg = 0
        node.end = len(source)
    elif len(children) > 0:
        node.beg = children[0].beg
        node.end = children[-1].end
    else:
        pass

def ast_to_xml(node):
    type = node.__class__.__name__
    e = ET.Element(type)
    #e.attrib['beg'] = str(node.beg)
    #e.attrib['end'] = str(node.end)

    cur_node = cur_xml = None
    for c in collect_child_nodes(node):
        if cur_node is None:
            e.text = text(beg(node), beg(c))
        else:
            cur_xml.tail = text(end(cur_node), beg(c))
        cur_node = c
        cur_xml = ast_to_xml(c) 
        e.append(cur_xml)

    if cur_node is None:
        e.text = text(beg(node), end(node))
    else:
        cur_xml.tail = text(end(cur_node), end(node))

    return e

source = slurp(sys.argv[1])
offsets = calculate_offsets(source)
root = ast.parse(source, filename=__file__)
attach_location(root)
xml = ast_to_xml(root)
print(ET.tostring(xml, encoding='utf-8').decode('utf-8'))
