# $Id: DomHelpers.py 34 2008-01-08 15:21:57Z graham $
#

import types
from os.path import exists
from os import rename, remove, linesep

from xml.dom import minidom

from StringIO  import StringIO
from string import strip

from Functions import concatMap

"""
Miscellaneous DOM helper functions.
"""

def parseXmlString(config):
    """
    Parse XML from a supplied string into a DOM structure
    """
    if type(config) == types.UnicodeType:
        s = StringIO(config.encode("utf-8") )
    else:
        s = StringIO(config)
    return parseXmlStream(s)

def parseXmlFile(name):
    """
    Read and parse XML from a file into a DOM structure
    """
    f = open(name,"r")
    dom = parseXmlStream(f)
    f.close()
    return dom

def saveXmlToFile(name, xmlDom, doBackup=True):
    """
    write bthe Xml DOM to a disk file.
    """
    if doBackup:
        if exists(name):
            if exists(name+'.bak'):
                remove(name+'.bak')
            rename( name, name+'.bak')
    f = open(name,"w")
    xmlDom.writexml(f)
    f.close()

def saveXmlToFilePretty(name, xmlDom, doBackup=True):
    """
    write bthe Xml DOM to a disk file.
    """
    if doBackup:
        if exists(name):
            if exists(name+'.bak'):
                remove(name+'.bak')
            rename( name, name+'.bak')
    f = open(name,"w")
    xmlDom.writexml(f, addindent="  ", newl="\n" )
    #xmlDom.writexml(f, addindent="  ", newl=linesep )
    f.close()

def parseXmlStream(inpstr):
    """
    Parse XML from a supplied stream into a DOM structure.
    Closes the stream when done.
    """
    dom = minidom.parse(inpstr)
    inpstr.close()
    return dom

def getElemXml(node):
    """
    Return text value of xml element (include all its children in the Xml string)
    """
    return node.toxml(encoding="utf-8")

def getElemPrettyXml(node):
    """
    Return prettyfied text value of xml element 
    (include all its children in the Xml string)
    """
    return node.toprettyxml(indent="  ", encoding="utf-8")

def getAttrText(elem,attr):
    """
    Return text value from a named attribute of the supplied element node.
    """
    return elem.getAttribute(attr)

def getElemText(elem):
    """
    Return text value from a single element node.
    This is a concatenation of text nodes contained within the element.
    """
    return getNodeListText(elem.childNodes)

def getNodeListText(nodelist):
    """
    Return concatenation of text values from a supplied list of nodes
    """
    rc = u""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def getFirstTextNodeValue(elem):
    """
    Return text value from the first named subnode of the supplied node.
    This is only the text at that node and 
    """
    return getElemText(elem)

def getNamedElem(parent, nodename):
    """
    Return first subnode of given parent with given tag name, or None
    if there is no such subnode.
    """
    nodes = parent.getElementsByTagName(nodename)
    if nodes:
        return nodes[0]
    return None

def getNamedNodeXml(parent, nodename):
    """
    Return Xml string of the first named subnode 
    (include all its children in the Xml string),
    or None.
    """
    subnode = getNamedElem(parent, nodename)
    if subnode:
        return getElemXml(subnode)
    return None
   
def getNamedNodeText(parent, nodename):
    """
    Return text value from the first named subnode of the supplied node
    This is a concatenation of text nodes contained within the first named element.
    """
    subnode = getNamedElem(parent, nodename)
    return subnode and getElemText(subnode)

def getNamedNodeAttrText(node, nodename, attr):
    """
    Return text value from a named attribute of the first named subnode of the supplied node
    """
    elem = getNamedElem(node, nodename)
    return elem and elem.getAttribute(attr)

# Node content replacement

def removeChildren(elm):
    while elm.hasChildNodes():
        elm.removeChild(elm.firstChild)
    return elm

def replaceChildren(elm,newchildren):
    removeChildren(elm)
    for n in newchildren:
        elm.appendChild(n)
    return elm

def replaceChildrenText(elm,newtext):
    replaceChildren(elm, [elm.ownerDocument.createTextNode(newtext)])
    return elm

# Node test functions

def isElement(node):
    """
    Returns True if the supplied node is an element
    """
    return node.nodeType == node.ELEMENT_NODE

def isAttribute(node):
    """
    Returns True if the supplied node is an attribute
    """
    return node.nodeType == node.ATTRIBUTE_NODE

def isText(node):
    """
    Returns True if the supplied node is free text.
    """
    return node.nodeType == node.TEXT_NODE

# Content manipulation helpers
def escapeChar(c,d={}):
    if c == '<': return "&lt;"
    if c == '>': return "&gt;"
    if c == '&': return "&amp;"
    return d.get(c,c)

def escapeCharForHtml(c):
    return escapeChar(c,d={'\n': "<br/>"})

def escapeText(s):
    return concatMap(escapeChar, s)

def escapeTextForHtml(s):
    return concatMap(escapeCharForHtml, s)

# End.
