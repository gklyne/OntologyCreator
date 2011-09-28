# $Id: ConvertOntology.py 1024 2008-12-17 17:42:56Z graham $
#
# Process Ontology in CSV file to publishable format
#
# TODO: describe file format
#

import sys
import optparse
import logging
import csv
import StringIO
import re

# ----------
# Vocabulary
# ----------

class Vocabulary:
    """
    Represents a full vocabulary as read from a CSV file.
    """
    def __init__(self):
        self._headings = None
        self._sequence = []
        self._prefixes = []
        self._classes  = []

    def addSequenceItem(self, item):
        """
        self._sequence keeps track of the ordering of items in the input stream,
        as a sequence of object values scanned from the input, used for reconstructing
        the input for display.  Sequence items are None, indicating a blank input row,
        a VocabPrefix or VocabClass value.
        """
        self._sequence.append(item)

    def getSequence(self):
        return self._sequence

    def setHeadings(self, headings):
        h = VocabHeadings(headings)
        self._headings = h
        self.addSequenceItem(h)    

    def getHeadings(self):
        return self._headings.getHeadings()

    def addPrefix(self, prefix, namespaceUri, label, descr, comment):
        p = VocabPrefix(prefix, namespaceUri, label, descr, comment)
        self._prefixes.append(p)
        self.addSequenceItem(p)

    def getPrefixes(self):
        return self._prefixes

    def getPrefix(self, idx):
        return self._prefixes[idx]

    def addClass(self,vclass):
        self._classes.append(vclass)
        self.addSequenceItem(vclass)

    def getClasses(self):
        return self._classes

    def getClass(self, idx):
        return self._classes[idx]

# --------
# VocabUri
# --------

class VocabUri(object):
    """
    URI used by a vocabulary: preserve qname components and full URI
    """
    def __init__(self, prefixtable, uritxt):
        self._base   = None
        self._prefix = None
        self._local  = None
        self._uri    = None
        if uritxt != None:
            self.setUri(prefixtable, uritxt)
        return

    def setUri(self, prefixtable, uritxt):
        log = logging.getLogger("ConvertOntology.VocabUri")
        log.debug("setUri '%s;", uritxt)
        qname_pattern = re.compile("([-.\w]+):([-.\w]+)")
        uri_pattern   = re.compile("<([^>]*)>")
        mqname = qname_pattern.match(uritxt)
        if mqname:
            if prefixtable:
                pre = mqname.group(1)
                loc = mqname.group(2)
                for p in prefixtable:
                    log.debug("setUri prefix %s, uri %s", p.getPrefix(), p.getUri())
                    if pre == p.getPrefix():
                        self._base   = p.getUri()
                        self._prefix = pre
                        self._local  = loc
                        self._uri    = self._base+self._local
                        return
                raise ValueError, "Prefix for '%s' not defined"%(uritxt)
            else:
                raise ValueError, "Expected <uri>, got qname '%s'"%(uritxt)
        muri = uri_pattern.match(uritxt)
        if muri:
            self._uri = muri.group(1)
            return
        raise ValueError, "Expected <uri> or qname, got '%s'"%(uritxt)

    def isUri(self):
        return True

    def getUri(self):
        if self._uri == None:
            raise ValueError, "No URI defined"
        return self._uri

    def haveNamePair(self):
        return self._prefix and self._local

    def getUriXml(self):
        if self.haveNamePair():
            return "&%s;%s"%(self._prefix, self._local)
        return self.getUri()

    def getQName(self):
        if self.haveNamePair():
            return "%s:%s"%(self._prefix, self._local)
        raise ValueError, "No prefix defined to form QName: %s"(self._uri)

    def getQNameOrUri(self):
        if self.haveNamePair():
            return "%s:%s"%(self._prefix, self._local)
        return "<%s>"%(self.getUri())

    def getEscapedQNameOrUri(self):
        log = logging.getLogger("ConvertOntology.VocabUri")
        log.debug("getEscapedQNameOrUri: return node uri: %s", self._uri)
        if self.haveNamePair():
            return "%s:%s"%(self._prefix, self._local)
        return "&lt;%s&gt;"%(self.getUri())

    def getPrefix(self):
        if self.haveNamePair():
            return self._prefix
        raise ValueError, "No prefix defined : %s"(self._uri)

# ---------
# VocabNode
# ---------

class VocabNode(VocabUri):
    """
    RDF node; URI or literal
    """
    def __init__(self, prefixtable, valtxt):
        super(VocabNode,self).__init__(None, None)
        self._nodevalue = None
        self.setUri(prefixtable, valtxt)
        return

    def setUri(self, prefixtable, valtxt):
        log = logging.getLogger("ConvertOntology.VocabNode")
        log.debug("setUri: '%s'", valtxt)
        qname_pattern = re.compile("(\w+):(\w+)")
        uri_pattern   = re.compile("<([^>]*)>")
        mqname = qname_pattern.match(valtxt)
        muri   = uri_pattern.match(valtxt)
        if (not mqname) and (not muri):
            log.debug("Setting node value: '%s'", valtxt)
            self._nodevalue = valtxt
            return
        log.debug("Setting node uri: '%s'", valtxt)
        super(VocabNode,self).setUri(prefixtable, valtxt)

    def isUri(self):
        return (self._nodevalue == None)

    def isFullUri(self):
        return (self._nodevalue == None) and (not self.haveNamePair())

    def getValue(self):
        log = logging.getLogger("ConvertOntology.VocabNode")
        if self._nodevalue != None:
            log.debug("getValue: return node value '%s'", self._nodevalue)
            return self._nodevalue
        log.debug("getValue: return node uri '%s'", self._uri)
        return self.getQNameOrUri()

    def getValueXml(self):
        log = logging.getLogger("ConvertOntology.VocabNode")
        if self._nodevalue != None:
            log.debug("getValueXml: return node value '%s'", self._nodevalue)
            if self._nodevalue[0] == '"' and self._nodevalue[-1] == '"':
                return self._nodevalue[1:-1]
            return self._nodevalue
        log.debug("getValueXml: return node uri '%s'", self._uri)
        return self.getUriXml()

    def getEscapedValue(self):
        log = logging.getLogger("ConvertOntology.VocabNode")
        if self._nodevalue != None:
            log.debug("getEscapedValue: return node value '%s'", self._nodevalue)
            return self._nodevalue
        log.debug("getEscapedValue: return node uri '%s'", self._uri)
        return self.getEscapedQNameOrUri()

# -------------------
# VocabCommonElements
# -------------------

class VocabCommonElements(object):
    """
    Common elements for several vocabulary items
    """
    def __init__(self, vocab, new, uri, label=None, descr=None, comment=None):
        self._new     = new
        self._uri     = VocabUri(vocab and vocab.getPrefixes(), uri)
        self._label   = label
        self._descr   = descr
        self._comment = []
        self.addComment(comment)

    def isNew(self):
        return self._new

    def getUri(self):
        return self._uri.getUri()

    def getUriXml(self):
        return self._uri.getUriXml()

    def getQName(self):
        return self._uri.getQName()

    def getQNameOrUri(self):
        return self._uri.getQNameOrUri()

    def getEscapedQNameOrUri(self):
        return self._uri.getEscapedQNameOrUri()

    def getLabel(self):
        return self._label or ""

    def getDescription(self):
        return self._descr or ""

    def addComment(self, comment):
        if comment:
            self._comment.append(comment)

    def getComment(self):
        return self._comment

# -------------
# VocabHeadings
# -------------

class VocabHeadings(object):
    def __init__(self, headings):
        self._headings = headings

    def getHeadings(self):
        return self._headings

    def getHeading(self, idx):
        return self._headings[idx]

# -----------
# VocabPrefix
# -----------

class VocabPrefix(VocabCommonElements):

    def __init__(self, prefix, namespaceUri, label=None, descr=None, comment=None):
        super(VocabPrefix,self).__init__(None, True, namespaceUri, label, descr, comment)
        self._prefix  = prefix

    def getPrefix(self):
        return self._prefix

# ----------
# VocabClass
# ----------

class VocabClass(VocabCommonElements):
    """
    Represents a vocabulary class or frame
    """
    def __init__(self, vocab, newClass, classURI, label=None, descr=None, comment=None):
        super(VocabClass,self).__init__(vocab, newClass, classURI, label, descr, comment)
        self._attrs   = []
        self._slots   = []

    def addAttr(self, attr):
        self._attrs.append(attr)

    def getAttrs(self):
        return self._attrs

    def getAttr(self, idx):
        return self._attrs[idx]

    def addSlot(self, slot):
        self._slots.append(slot)

    def getSlots(self):
        return self._slots

    def getSlot(self, idx):
        return self._slots[idx]

# ---------
# VocabAttr
# ---------

class VocabAttr(VocabCommonElements):
    """
    Represents an attribute of a vocabulary class; i.e. a schema assertion about that class
    """
    def __init__(self, vocab, newAttr, inverseAttr, attrURI, value, label=None, descr=None, comment=None):
        super(VocabAttr,self).__init__(vocab, newAttr, attrURI, label, descr, comment)
        self._inverse = inverseAttr
        self._value   = VocabNode(vocab and vocab.getPrefixes(), value) # URI or literal
        return
    
    def isInverse(self):
        return self._inverse

    def isUriValue(self):
        return self._value.isUri()

    def isFullUriValue(self):
        return self._value.isFullUri()

    def getValue(self):
        return self._value.getValue()

    def getValueUri(self):
        return self._value.getUri()

    def getValueQName(self):
        return self._value.getQName()

    def getValueXml(self):
        return self._value.getValueXml()

    def getValueQNameOrUri(self):
        return self._value.getQNameOrUri()

    def getEscapedValueQNameOrUri(self):
        return self._value.getEscapedValue()

# ---------
# VocabSlot
# ---------

class VocabSlot(VocabCommonElements):
    """
    Represents a slot of a vocabulary class; i.e. a property that is expected to be associated with 
    an instance of the class, along with cardinality and property value type constraints.
    """
    def __init__(self, vocab, newSlot, inverseProp, propURI, mincard, maxcard, valtype, 
                 label=None, descr=None, comment=None):
        super(VocabSlot,self).__init__(vocab, newSlot, propURI, label, descr, comment)
        self._inverse = inverseProp
        self._mincard = mincard
        self._maxcard = maxcard
        self._valtype = VocabUri(vocab.getPrefixes(), valtype)
        self._asserts = []

    def isInverse(self):
        return self._inverse

    def getMinCardinality(self):
        return self._mincard

    def getMaxCardinality(self):
        return self._maxcard

    def getValTypeQName(self):
        return self._valtype.getQName()

    def getValTypeUri(self):
        return self._valtype.getUri()

    def getValTypeXml(self):
        return self._valtype.getUriXml()

    def getValTypeQNameOrUri(self):
        return self._valtype.getQNameOrUri()

    def getEscapedValTypeQNameOrUri(self):
        return self._valtype.getEscapedQNameOrUri()

    def getValTypePrefix(self):
        return self._valtype.getPrefix()

    def addAssertion(self, vocab, relation, value, label, descr, comment):
        a = SlotAssertion(vocab, relation, value, label, descr, comment)
        self._asserts.append(a)

    def getAssertions(self):
        return self._asserts

    def getAssertion(self, idx):
        return self._asserts[idx]

# -------------
# SlotAssertion
# -------------

class SlotAssertion(VocabCommonElements):
    """
    Represents an assertion about the property for a slot; 
    e.g. that it is a subproperty of some other property.
    """
    def __init__(self, vocab, relation, value, label=None, descr=None, comment=None):
        super(SlotAssertion,self).__init__(vocab, False, relation, label, descr, comment)
        self._value   = VocabNode(vocab and vocab.getPrefixes(), value) # URI or literal

    def getValueOrUri(self):
        return self._value.getValue()

    def getValueUri(self):
        return self._value.getUri()

    def getValueQName(self):
        return self._value.getQName()

    def getValueXml(self):
        return self._value.getUriXml()

    def getValueQNameOrUri(self):
        return self._value.getQNameOrUri()

    def getEscapedValueQnameOrUri(self):
        return self._value.getEscapedQNameOrUri()

# -------------------------------
# Vocabulary processing functions
# -------------------------------

def readVocabulary(csvreader):
    """
    Read vocabulary details from the CSV reader, and return a 
    VocabClass object reflecting what was there.
    """
    log = logging.getLogger("ConvertOntology.readVocabulary")
    v = Vocabulary()
    try:
        # Column headings
        v.setHeadings(csvreader.next())
        # Table body
        for row in csvreader:
            row = (row+['','','','','','',''])[:7]
            log.debug("read row '%s'", str(row))
            (r_flag,r_class,r_prop,r_value,r_label,r_descr,r_comment) = row
            if r_flag == '@' and r_class == 'prefix':
                #TODO: move re.compiles out of loop
                pref_pattern = re.compile("\s*([^:]*):?")
                mpref = pref_pattern.match(row[2])
                v.addPrefix(mpref.group(1), row[3], r_label, r_descr, r_comment)
            elif r_class == '' and r_prop == '' and r_value == '' and r_label == '' and r_descr == '' and r_comment == '':
                v.addSequenceItem(None)
            elif r_flag != '#':
                if r_class != '':
                    c = VocabClass(v, r_flag == '+', r_class, r_label, r_descr, r_comment)
                    v.addClass(c)
                    p = None
                    r_label    = ''
                    r_descr    = ''
                    r_comment  = ''
                    r_prevprop = ''
                if r_value != '':
                    if r_prop != '':
                        r_prevprop = r_prop
                    else:
                        r_prop = r_prevprop
                if r_prop != '':
                    #TODO: move re.compiles out of loop
                    prop_pattern = re.compile("\s*(\^)?\s*(.*)")
                    mprop = prop_pattern.match(r_prop)
                    pnew  = r_flag == '+'
                    pinv  = mprop.group(1) == '^'
                    puri  = mprop.group(2)
                    #TODO: move re.compiles out of loop
                    slot_pattern = re.compile("\s*(([?1*+])\s*::)?\s*(<=)?\s*(.*)")
                    mslot = slot_pattern.match(r_value)
                    prel  = mslot.group(3)
                    sval  = mslot.group(4)
                    if mslot.group(1) != None:
                        card  = mslot.group(2)
                        cmin  = 0
                        cmax  = sys.maxint
                        if card in "1+": cmin = 1
                        if card in "1?": cmax = 1
                        p = VocabSlot(v, pnew, pinv, puri, cmin, cmax, sval, r_label, r_descr, r_comment)
                        c.addSlot(p)
                    elif mslot.group(3) == '<=':
                        rel = "rdfs:subPropertyOf"
                        p.addAssertion(v, rel, sval, r_label, r_descr, r_comment)
                    else:
                        p = VocabAttr(v, pnew, pinv, puri, sval, r_label, r_descr, r_comment)
                        c.addAttr(p)
                    r_value   = None
                    r_label   = None
                    r_descr   = None
                    r_comment = None
                if r_comment != None and r_comment != '':
                    if r_class != '' or p == None:
                        c.addComment(r_comment)
                    else:
                        p.addComment(r_comment)
    except csv.Error, e:
        sys.stderr.write("input line %d: %s" % (csvreader.line_num, e))
        return None
    return v

def testReadVocabulary():
    def assertEq(val,expect):
        assert val == expect, "Found '%s', expected '%s'"%(val,expect)

    vtxt =  '''"f","c","p","v","label","descr","comment"
        ,,,,,,
        "@","prefix","rdf:","<http://www.w3.org/1999/02/22-rdf-syntax-ns#>",,,
        "@","prefix","rdfs:","<http://www.w3.org/2000/01/rdf-schema#>",,,
        "@","prefix","pre:","<prefix#>","prefix label","prefix descr","prefix comment"
        ,,,,,,
        ,"<#>","rdfs:seeAlso","<http://a.b/see-also/index.html>",,"Some comment",
        ,,"rdfs:seeAlso","<second-see-also>",,,
        ,,,,,,
        "+","pre:Class",,,"a class","class descr","class comment"
        "+",,"pre:prop","pre:val","prop val","prop val descr","prop val comment"
        "+",,"pre:slot1","1 :: pre:type1","slot1 type1","slot1 type1 descr","slot1 type1 comment"
        "+",,"pre:slot2","? :: pre:type2","slot2 type2","slot2 type2 descr","slot2 type2 comment"
        "+",,"pre:slot3","* :: pre:type3","slot3 type3","slot3 type3 descr","slot3 type3 comment"
        "+",,"pre:slot4","+ :: pre:type4","slot4 type4","slot4 type4 descr","slot4 type4 comment"
        "+",,,"<= pre:superprop",,,,
        ,,,,,,
        "+","pre:Type",,,"a type","type descr","type comment"
        "+",,"^ rdf:type","value1","type value1","type value1 descr","type value1 comment"
        "+",,,"value2","type value2","type value2 descr","type value2 comment"
        "+",,,,,,"type value2 more comment"
        "+",,"rdfs:label","""label text"""
        ,,,,,,
        "+","pre:c.c-c","pre:p.p-p","1 :: pre:s.s-s","c.c-c p.p-p s.s-s","class, property and slot with '.' and '-' in name"
        '''
    vstr = StringIO.StringIO(vtxt)
    vocab = readVocabulary(csv.reader(vstr, skipinitialspace=True ))

    seq = [VocabHeadings, None, 
           VocabPrefix, VocabPrefix, VocabPrefix, None, 
           VocabClass, None, 
           VocabClass, None, 
           VocabClass]
    for (sval,styp) in zip(vocab.getSequence(),seq):
        assert ((sval == None) and (styp == None)) or isinstance(sval,styp)

    assertEq(vocab.getHeadings(), ["f","c","p","v","label","descr","comment"])

    assertEq(len(vocab.getPrefixes()), 3)
    assertEq(vocab.getPrefix(0).getPrefix(),      "rdf")
    assertEq(vocab.getPrefix(1).getPrefix(),      "rdfs")
    assertEq(vocab.getPrefix(2).getPrefix(),      "pre")
    assertEq(vocab.getPrefix(2).getUri(),         "prefix#")
    assertEq(vocab.getPrefix(2).getLabel(),       "prefix label")
    assertEq(vocab.getPrefix(2).getDescription(), "prefix descr")
    assertEq(vocab.getPrefix(2).getComment(),     ["prefix comment"])

    assertEq(len(vocab.getClasses()), 4)

    assertEq(vocab.getClass(0).isNew(),           False)
    assertEq(vocab.getClass(0).getUri(),          "#")
    assertEq(vocab.getClass(0).getLabel(),        "")
    assertEq(vocab.getClass(0).getDescription(),  "Some comment")
    assertEq(vocab.getClass(0).getComment(),      [])
    assertEq(len(vocab.getClass(0).getAttrs()),   2)
    assertEq(len(vocab.getClass(0).getSlots()),   0)

    c0a0 = vocab.getClass(0).getAttr(0)
    assertEq(c0a0.isNew(),              False)
    assertEq(c0a0.isInverse(),          False)
    assertEq(c0a0.getQName(),           "rdfs:seeAlso")
    assertEq(c0a0.getValueQNameOrUri(), "<http://a.b/see-also/index.html>")
    assertEq(c0a0.getValue(),           "<http://a.b/see-also/index.html>")
    assertEq(c0a0.getEscapedValueQNameOrUri(), "&lt;http://a.b/see-also/index.html&gt;")
    assertEq(c0a0.getLabel(),           "")
    assertEq(c0a0.getDescription(),     "")
    assertEq(c0a0.getComment(),         [])

    c0a1 = vocab.getClass(0).getAttr(1)
    assertEq(c0a1.isNew(),              False)
    assertEq(c0a1.isInverse(),          False)
    assertEq(c0a1.getQName(),           "rdfs:seeAlso")
    assertEq(c0a1.getValueQNameOrUri(), "<second-see-also>")
    assertEq(c0a1.getValue(),           "<second-see-also>")
    assertEq(c0a1.getEscapedValueQNameOrUri(), "&lt;second-see-also&gt;")
    assertEq(c0a1.getLabel(),           "")
    assertEq(c0a1.getDescription(),     "")
    assertEq(c0a1.getComment(),         [])

    assertEq(vocab.getClass(1).isNew(),           True)
    assertEq(vocab.getClass(1).getQName(),        "pre:Class")
    assertEq(vocab.getClass(1).getUri(),          "prefix#Class")
    assertEq(vocab.getClass(1).getLabel(),        "a class")
    assertEq(vocab.getClass(1).getDescription(),  "class descr")
    assertEq(vocab.getClass(1).getComment(),      ["class comment"])
    assertEq(len(vocab.getClass(1).getAttrs()),   1)
    assertEq(len(vocab.getClass(1).getSlots()),   4)

    c1a0 = vocab.getClass(1).getAttr(0)
    assertEq(c1a0.isNew(),              True)
    assertEq(c1a0.isInverse(),          False)
    assertEq(c1a0.getQName(),           "pre:prop")
    assertEq(c1a0.getUri(),             "prefix#prop")
    assertEq(c1a0.getValueQNameOrUri(), "pre:val")
    assertEq(c1a0.getLabel(),           "prop val")
    assertEq(c1a0.getDescription(),     "prop val descr")
    assertEq(c1a0.getComment(),         ["prop val comment"])

    c1s0 = vocab.getClass(1).getSlot(0)
    assertEq(c1s0.isNew(),              True)
    assertEq(c1s0.isInverse(),          False)
    assertEq(c1s0.getQName(),           "pre:slot1")
    assertEq(c1s0.getUri(),             "prefix#slot1")
    assertEq(c1s0.getMinCardinality(),  1)
    assertEq(c1s0.getMaxCardinality(),  1)
    assertEq(c1s0.getValTypeQName(),    "pre:type1")
    assertEq(c1s0.getValTypeUri(),      "prefix#type1")
    assertEq(c1s0.getValTypeXml(),      "&pre;type1")
    assertEq(c1s0.getLabel(),           "slot1 type1")
    assertEq(c1s0.getDescription(),     "slot1 type1 descr")
    assertEq(c1s0.getComment(),         ["slot1 type1 comment"])
    assertEq(len(c1s0.getAssertions()), 0)

    c1s1 = vocab.getClass(1).getSlot(1)
    assertEq(c1s1.isNew(),              True)
    assertEq(c1s1.isInverse(),          False)
    assertEq(c1s1.getQName(),           "pre:slot2")
    assertEq(c1s1.getUri(),             "prefix#slot2")
    assertEq(c1s1.getMinCardinality(),  0)
    assertEq(c1s1.getMaxCardinality(),  1)
    assertEq(c1s1.getValTypeQName(),    "pre:type2")
    assertEq(c1s1.getValTypeUri(),      "prefix#type2")
    assertEq(c1s1.getValTypeXml(),      "&pre;type2")
    assertEq(c1s1.getLabel(),           "slot2 type2")
    assertEq(c1s1.getDescription(),     "slot2 type2 descr")
    assertEq(c1s1.getComment(),         ["slot2 type2 comment"])
    assertEq(len(c1s1.getAssertions()), 0)

    c1s2 = vocab.getClass(1).getSlot(2)
    assertEq(c1s2.isNew(),              True)
    assertEq(c1s2.isInverse(),          False)
    assertEq(c1s2.getQName(),           "pre:slot3")
    assertEq(c1s2.getUri(),             "prefix#slot3")
    assertEq(c1s2.getMinCardinality(),  0)
    assertEq(c1s2.getMaxCardinality(),  sys.maxint)
    assertEq(c1s2.getValTypeQName(),    "pre:type3")
    assertEq(c1s2.getValTypeUri(),      "prefix#type3")
    assertEq(c1s2.getValTypeXml(),      "&pre;type3")
    assertEq(c1s2.getLabel(),           "slot3 type3")
    assertEq(c1s2.getDescription(),     "slot3 type3 descr")
    assertEq(c1s2.getComment(),         ["slot3 type3 comment"])
    assertEq(len(c1s2.getAssertions()), 0)

    c1s3 = vocab.getClass(1).getSlot(3)
    assertEq(c1s3.isNew(),              True)
    assertEq(c1s3.isInverse(),          False)
    assertEq(c1s3.getQName(),           "pre:slot4")
    assertEq(c1s3.getUri(),             "prefix#slot4")
    assertEq(c1s3.getMinCardinality(),  1)
    assertEq(c1s3.getMaxCardinality(),  sys.maxint)
    assertEq(c1s3.getValTypeQName(),    "pre:type4")
    assertEq(c1s3.getValTypeUri(),      "prefix#type4")
    assertEq(c1s3.getValTypeXml(),      "&pre;type4")
    assertEq(c1s3.getLabel(),           "slot4 type4")
    assertEq(c1s3.getDescription(),     "slot4 type4 descr")
    assertEq(c1s3.getComment(),         ["slot4 type4 comment"])
    assertEq(len(c1s3.getAssertions()), 1)

    c1s3a0 = c1s3.getAssertion(0)
    assertEq(c1s3a0.getQName(),         "rdfs:subPropertyOf")
    assertEq(c1s3a0.getValueOrUri(),    "pre:superprop")
    assertEq(c1s3a0.getLabel(),         "")
    assertEq(c1s3a0.getDescription(),   "")
    assertEq(c1s3a0.getComment(),       [])

    assertEq(vocab.getClass(2).isNew(),           True)
    assertEq(vocab.getClass(2).getQName(),        "pre:Type")
    assertEq(vocab.getClass(2).getLabel(),        "a type")
    assertEq(vocab.getClass(2).getDescription(),  "type descr")
    assertEq(vocab.getClass(2).getComment(),      ["type comment"])
    assertEq(len(vocab.getClass(2).getAttrs()),   3)
    assertEq(len(vocab.getClass(2).getSlots()),   0)

    c2a0 = vocab.getClass(2).getAttr(0)
    assertEq(c2a0.isNew(),          True)
    assertEq(c2a0.isInverse(),      True)
    assertEq(c2a0.getQName(),       "rdf:type")
    assertEq(c2a0.getValue(),       "value1")
    assertEq(c2a0.getEscapedValueQNameOrUri(), "value1")
    assertEq(c2a0.getLabel(),       "type value1")
    assertEq(c2a0.getDescription(), "type value1 descr")
    assertEq(c2a0.getComment(),     ["type value1 comment"])

    c2a1 = vocab.getClass(2).getAttr(1)
    assertEq(c2a1.isNew(),          True)
    assertEq(c2a1.isInverse(),      True)
    assertEq(c2a1.isUriValue(),     False)
    assertEq(c2a1.getQName(),       "rdf:type")
    assertEq(c2a1.getValue(),       "value2")
    assertEq(c2a1.getLabel(),       "type value2")
    assertEq(c2a1.getValueXml(),    "value2")
    assertEq(c2a1.getDescription(), "type value2 descr")
    assertEq(c2a1.getComment(),     ["type value2 comment",
                                     "type value2 more comment"])

    c2a2 = vocab.getClass(2).getAttr(2)
    assertEq(c2a2.isNew(),          True)
    assertEq(c2a2.isUriValue(),     False)
    assertEq(c2a2.isInverse(),      False)
    assertEq(c2a2.getQName(),       "rdfs:label")
    assertEq(c2a2.getValue(),       '"label text"')
    assertEq(c2a2.getLabel(),       "")
    assertEq(c2a2.getValueXml(),    'label text')
    assertEq(c2a2.getDescription(), "")
    assertEq(c2a2.getComment(),     [])

    assertEq(vocab.getClass(3).isNew(),           True)
    assertEq(vocab.getClass(3).getQName(),        "pre:c.c-c")
    assertEq(vocab.getClass(3).getUri(),          "prefix#c.c-c")
    assertEq(vocab.getClass(3).getLabel(),        "c.c-c p.p-p s.s-s")
    assertEq(vocab.getClass(3).getDescription(),  "class, property and slot with '.' and '-' in name")
    assertEq(vocab.getClass(3).getComment(),      [])
    assertEq(len(vocab.getClass(3).getAttrs()),   0)
    assertEq(len(vocab.getClass(3).getSlots()),   1)

    c3s0 = vocab.getClass(3).getSlot(0)
    assertEq(c3s0.isNew(),              True)
    assertEq(c3s0.isInverse(),          False)
    assertEq(c3s0.getQName(),           "pre:p.p-p")
    assertEq(c3s0.getUri(),             "prefix#p.p-p")
    assertEq(c3s0.getMinCardinality(),  1)
    assertEq(c3s0.getMaxCardinality(),  1)
    assertEq(c3s0.getValTypeQName(),    "pre:s.s-s")
    assertEq(c3s0.getValTypeUri(),      "prefix#s.s-s")
    assertEq(c3s0.getValTypeXml(),      "&pre;s.s-s")
    assertEq(c3s0.getLabel(),           "")
    assertEq(c3s0.getDescription(),     "")
    assertEq(c3s0.getComment(),         [])
    assertEq(len(c3s0.getAssertions()), 0)


# ------------------
# Main program logic
# ------------------

def convertOntology(ipstr, opstr, options):
    """
    Convert an ontology to publishable form, using data streams and options provided.
    
    Returns:
      0 - success
      1 - error
    """
    csvreader = csv.reader(ipstr)
    if options.mediawiki:
        return convertOntologyToMediaWiki(csvreader, opstr, options)
    elif options.basecamp:
        return convertOntologyToBasecamp(csvreader, opstr, options)
    elif options.rdf:
        return convertOntologyToOwl(csvreader, opstr, options)
    else:
        assert False,"TODO - convertOntology other options"
    return 1

def convertOntologyToOwl(csvreader, opstr, options):
    """
    Convert an ontology from the supplied csv reader to OWL RDF/XML format.
    """
    #TODO: use qualified cardinality restrictions?
    #TODO: add RDF, RDFS, OWL, OWL2 namespaces to prefix list?
    #TODO: detect non-class values and output as instance data
    owl_preamble = (
        """<?xml version="1.0"?>\n\n"""
        )
    owl_postamble = (
        """<!-- End of file; written by $Id: ConvertOntology.py 1024 2008-12-17 17:42:56Z graham $ -->\n\n"""
        )
    owl_entity_start = (
        """<!DOCTYPE rdf:RDF [\n"""
        )
    owl_entity_prefix = (
        """    <!ENTITY %s "%s" >\n"""
        )
    owl_entity_end = (
        """]>\n\n"""
        )
    owl_rdfopen_start = (
        """<rdf:RDF \n"""
        )
    owl_rdfopen_prefix = (
        """      xmlns:%s="%s"\n"""
        )
    owl_rdfopen_end = (
        """    >\n\n"""
        )
    owl_rdfclose = (
        """</rdf:RDF>\n\n"""
        )
    owl_ontology_elem = (
        """    <owl:Ontology rdf:about=""/>\n\n"""
        )
    owl_class_open = (
        """    <owl:Class rdf:about="%s">\n"""
        )
    owl_class_close = (
        """    </owl:Class>\n\n"""
        )
    owl_class_label = (
        """        <rdfs:label>%s</rdfs:label>\n"""
        )
    owl_class_description = (
        """        <rdfs:comment\n"""
        """            >%s</rdfs:comment>\n"""
        )
    owl_class_attribute = (
        """        <%s rdf:resource="%s"/>\n"""
        )
    owl_class_attr_lit = (
        """        <%s>%s</%s>\n"""
        )
    owl_class_slot_type = (
        """        <rdfs:subClassOf>\n"""
        """            <owl:Restriction>\n"""
        """                <owl:onProperty rdf:resource="%s"/>\n"""
        """                <owl:allValuesFrom rdf:resource="%s"/>\n"""
        """            </owl:Restriction>\n"""
        """        </rdfs:subClassOf>\n"""
        )
    owl_class_slot_min = (
        """        <rdfs:subClassOf>\n"""
        """            <owl:Restriction>\n"""
        """                <owl:onProperty rdf:resource="%s"/>\n"""
        """                <owl:minCardinality rdf:datatype="&xsd;nonNegativeInteger">%s</owl:minCardinality>\n"""
        """            </owl:Restriction>\n"""
        """        </rdfs:subClassOf>\n"""
        )
    owl_class_slot_max = (
        """        <rdfs:subClassOf>\n"""
        """            <owl:Restriction>\n"""
        """                <owl:onProperty rdf:resource="%s"/>\n"""
        """                <owl:maxCardinality rdf:datatype="&xsd;nonNegativeInteger">%s</owl:maxCardinality>\n"""
        """            </owl:Restriction>\n"""
        """        </rdfs:subClassOf>\n"""
        )
    owl_class_slot_exactly = (
        """        <rdfs:subClassOf>\n"""
        """            <owl:Restriction>\n"""
        """                <owl:onProperty rdf:resource="%s"/>\n"""
        """                <owl:cardinality rdf:datatype="&xsd;nonNegativeInteger">%s</owl:cardinality>\n"""
        """            </owl:Restriction>\n"""
        """        </rdfs:subClassOf>\n"""
        )
    owl_class_enumeration_open = (
        """    <owl:Class rdf:about="%s">\n"""
        """        <owl:oneOf rdf:parseType="Collection">\n"""
        )
    owl_class_enumeration_value = (
        """            <rdf:Description rdf:about="%s"/>\n"""
        )
    owl_class_enumeration_close = (
        """        </owl:oneOf>\n"""
        """    </owl:Class>\n\n"""
        )
    owl_class_union_open = (
        """    <owl:Class rdf:about="%s">\n"""
        """        <owl:unionOf rdf:parseType="Collection">\n"""
        )
    owl_class_union_value = (
        """            <owl:Class rdf:about="%s"/>\n"""
        )
    owl_class_union_close = (
        """        </owl:unionOf>\n"""
        """    </owl:Class>\n\n"""
        )
    owl_assertion_open = (
        """    <rdf:Description rdf:about="%s">\n"""
        )
    owl_assertion_value = (
        """        <%s rdf:resource="%s"/>\n"""
        )
    owl_assertion_close = (
        """    </rdf:Description>\n\n"""
        )
    owl_datatype_property_open = (
        """    <owl:DatatypeProperty rdf:about="%s">\n"""
        )
    owl_object_property_open = (
        """    <owl:ObjectProperty rdf:about="%s">\n"""
        )
    owl_property_label = (
        """        <rdfs:label>%s</rdfs:label>\n"""
        )
    owl_property_description = (
        """        <rdfs:comment\n"""
        """            >%s</rdfs:comment>\n"""
        )
    owl_object_property_close = (
        """    </owl:ObjectProperty>\n\n"""
        )
    owl_datatype_property_close = (
        """    </owl:DatatypeProperty>\n\n"""
        )
    owl_zzzzzz = (
        """\n"""
        )

    # Parse vocabulary details from CSV
    try:
        vocab = readVocabulary(csvreader)
    except csv.Error, e:
        sys.stderr.write("input line %d: %s" % (csvreader.line_num, e))
        return 1
    # Process vocabulary
    #
    # Write preamble
    opstr.write(owl_preamble)
    # Write prefix entities
    opstr.write(owl_entity_start)
    for p in vocab.getPrefixes():
            opstr.write(owl_entity_prefix%(p.getPrefix(), p.getUri()))
    opstr.write(owl_entity_end)
    # Write rdf:RDF with prefix namespaces
    opstr.write(owl_rdfopen_start)
    for p in vocab.getPrefixes():
            opstr.write(owl_rdfopen_prefix%(p.getPrefix(), p.getUri()))
    opstr.write(owl_rdfopen_end)
    # Write ontology header (TODO: think about how to name ontology)
    opstr.write(owl_ontology_elem)
    # Write out slot property descriptions, labels, etc
    for c in [cc for cc in vocab.getClasses() if cc.isNew()]:
        for s in c.getSlots():
            #TODO: use URIs rather than qnames or prefix strings to isolate literal types
            if s.getValTypeQName() == "rdfs:Literal" or s.getValTypePrefix() == "xsd":
                opstr.write(owl_datatype_property_open%(s.getUriXml()))
                propclose = owl_datatype_property_close
            else:
                opstr.write(owl_object_property_open%(s.getUriXml()))
                propclose = owl_object_property_close
            if s.getLabel() != "":
                opstr.write(owl_property_label%(s.getLabel()))
            # Class description
            if s.getDescription() != "":
                opstr.write(owl_property_description%(s.getDescription()))
            opstr.write(propclose)
    # Process class descriptions
    for c in [cc for cc in vocab.getClasses() if cc.isNew()]:
        # Class open
        opstr.write(owl_class_open%(c.getUriXml()))
        # Class label
        if c.getLabel() != "":
            opstr.write(owl_class_label%(c.getLabel()))
        # Class description
        if c.getDescription() != "":
            opstr.write(owl_class_description%(c.getDescription()))
        # Non-inverse class attributes
        for a in [aa for aa in c.getAttrs() if not aa.isInverse()]:
            if a.isUriValue():
                opstr.write(owl_class_attribute%(a.getQName(), a.getValueXml()))
            else:
                opstr.write(owl_class_attr_lit%(a.getQName(), a.getValueXml(), a.getQName()))
        # Class slots
        for s in c.getSlots():
            if s.isInverse():
                raise ValueError, "Inverse slot property not supported"
            #TODO: Handle repeated slot property with different types (for now, just assume closure)
            opstr.write(owl_class_slot_type%(s.getUriXml(), s.getValTypeXml()))
            min = s.getMinCardinality()
            max = s.getMaxCardinality()
            if min == max:
                opstr.write(owl_class_slot_exactly%(s.getUriXml(), min))
            elif min != 0:
                opstr.write(owl_class_slot_min%(s.getUriXml(), min))
            elif max != sys.maxint:
                opstr.write(owl_class_slot_max%(s.getUriXml(), max))
        # Class close
        opstr.write(owl_class_close)
    # Deal with enumerated indivudual values
    for c in [cc for cc in vocab.getClasses() if cc.isNew()]:
        #TODO: create function to construct a URI with reference to prefixes; e.g. vocab.mkUri("rdf:type")
        vals = []
        for a in [aa for aa in c.getAttrs() 
                            if aa.isInverse() and 
                               aa.getQName() == "rdf:type"]:
            vals.append(a.getValueXml())
        if vals != []:
            opstr.write(owl_class_enumeration_open%(c.getUriXml()))
            for v in vals:
                opstr.write(owl_class_enumeration_value%(v))
            opstr.write(owl_class_enumeration_close)
    # Deal with enumerated subclass values
    for c in [cc for cc in vocab.getClasses() if cc.isNew()]:
        #TODO: create function to construct a URI with reference to prefixes; e.g. vocab.mkUri("rdf:type")
        vals = []
        for a in [aa for aa in c.getAttrs() 
                            if aa.isInverse() and 
                               aa.getQName() == "rdfs:subClassOf"]:
            vals.append(a.getValueXml())
        if vals != []:
            opstr.write(owl_class_union_open%(c.getUriXml()))
            for v in vals:
                opstr.write(owl_class_union_value%(v))
            opstr.write(owl_class_union_close)
    # Deal with inverse attribute assertions
    for c in [cc for cc in vocab.getClasses() if cc.isNew()]:
        #TODO: create function to construct a URI with reference to prefixes; e.g. vocab.mkUri("rdf:type")
        for a in [aa for aa in c.getAttrs() 
                            if aa.isInverse() and 
                               aa.getUri() != "rdf:type" and 
                               aa.getUri() != "rdfs:subClassOf"]:
            opstr.write(owl_assertion_open%(a.getValueXml()))
            opstr.write(owl_assertion_value%(a.getQName(), c.getUriXml()))
            opstr.write(owl_assertion_close)
    # Close <rdf:RDF> element
    opstr.write(owl_rdfclose)
    # Write file postamble
    opstr.write(owl_postamble)
    return 0

def convertOntologyToMediaWiki(csvreader, opstr, options):
    """
    Convert an ontology from the supplied csv reader to mediawiki table format.
    """
    wiki_preamble = (
        """== Vocabulary summary ==\n"""
        """\n"""
        """{| border="0" padding="1" style="background:#FFFFFF"\n"""
        )
    wiki_blank = (
        """|- style="background:#FFFFFF"\n"""
        """|||||||||\n"""
        )
    wiki_heading = (
        """|- style="background:#E8E8F0"\n"""
        """! %s !! %s !! %s !! %s !! %s\n"""
        )
    wiki_prefix = (
        """|- style="background:#F8F8FF"\n"""
        """| @prefix ||%s:||colspan="3"|<%s>\n"""
        )
    wiki_oldentry = (
        """|- style="background:#F8F8FF; color:#808080;"\n"""
        """|%s||%s||%s||%s||%s\n"""
        )
    wiki_newentry = (
        """|- style="background:#F8F8FF"\n"""
        """|%s||%s||%s||%s||%s\n"""
        )
    wiki_comment = (
        """|- style="background:#F8F8FF; color:#C00000; font-style:italic;"\n"""
        """|  ||  ||  ||  || -- %s\n"""
        )
    wiki_postamble = (
        """|}\n\n"""
        )
    wiki_class = (
        """=== Class %s ===\n"""
        """\n%s\n\n"""
        )
    wiki_property = (
        """=== Property %s ===\n"""
        """\n%s\n\n"""
        )

    # Parse vocabulary details from CSV
    try:
        vocab = readVocabulary(csvreader)
    except csv.Error, e:
        sys.stderr.write("input line %d: %s" % (csvreader.line_num, e))
        return 1
    # Process vocabulary
    opstr.write(wiki_preamble)
    for item in vocab.getSequence():
        if item == None:
            opstr.write(wiki_blank)
        elif isinstance(item, VocabHeadings):
            opstr.write(wiki_heading%tuple(item.getHeadings()[1:6]))
        elif isinstance(item, VocabPrefix):
            #TODO: include label, descr, comment?
            opstr.write(wiki_prefix%(item.getPrefix(),item.getUri()))
        elif isinstance(item, VocabClass):
            # Class
            classvals = (item.getQNameOrUri(),"","",item.getLabel(),item.getDescription())
            if item.isNew():
                opstr.write(wiki_newentry%classvals)
            else:
                opstr.write(wiki_oldentry%classvals)
            comment   = item.getComment()
            if comment:
                opstr.write(wiki_comment%("\n\n".join(comment)))
            # Attributes
            for attr in item.getAttrs():
                prop = attr.getQName()
                if attr.isInverse(): prop = "^ "+prop
                attrvals = ("", prop, attr.getValueOrUri(), attr.getLabel(), attr.getDescription())
                if attr.isNew():
                    opstr.write(wiki_newentry%attrvals)
                else:
                    opstr.write(wiki_oldentry%attrvals)
                comment   = attr.getComment()
                if comment:
                    opstr.write(wiki_comment%("\n\n".join(comment)))
            # Slots
            for slot in item.getSlots():
                prop = slot.getQName()
                if slot.isInverse(): prop = "^ "+prop
                if slot.getMinCardinality() == 0:
                    if slot.getMaxCardinality() == 1:
                        flag = '?'
                    else:
                        flag = '*'
                else:
                    if slot.getMaxCardinality() == 1:
                        flag = '1'
                    else:
                        flag = '+'
                styp = flag + " :: " + slot.getValTypeQName()
                slotvals = ("", prop, styp, slot.getLabel(), slot.getDescription())
                if slot.isNew():
                    opstr.write(wiki_newentry%slotvals)
                else:
                    opstr.write(wiki_oldentry%slotvals)
                for asrt in slot.getAssertions(): 
                    prop = asrt.getQName()
                    if prop == "rdfs:subPropertyOf":
                        prop = "<="
                    asrtvals = ("", "", prop+" "+asrt.getValueOrUri(), asrt.getLabel(), asrt.getDescription())
                    if asrt.isNew():
                        opstr.write(wiki_newentry%asrtvals)
                    else:
                        opstr.write(wiki_oldentry%asrtvals)
                comment   = slot.getComment()
                if comment:
                    opstr.write(wiki_comment%("\n\n".join(comment)))
        else:
            assert False, "Unexpected value: "+str(item)
    opstr.write(wiki_postamble)
    # Second pass to pick out class comments:
    if False:
        for item in vocab.getSequence():
            if isinstance(item, VocabClass):
                comment   = item.getComment()
                if comment:
                    opstr.write(wiki_class%(item.getUri(), "\n\n".join(comment)))
    # Third pass to pick out slot property comments:
    if False:
        for item in vocab.getSequence():
            if isinstance(item, VocabClass):
                for slot in item.getSlots():
                    comment   = slot.getComment()
                    if comment:
                        opstr.write(wiki_property%(slot.getUri(), "\n\n".join(comment)))
    return 0


def convertOntologyToBasecamp(csvreader, opstr, options):
    """
    Convert an ontology from the supplied csv reader to Basecamp table format.
    """
    basecamp_preamble = (
        """<h2>Vocabulary summary</h2>\n"""
        """\n"""
        """<table valign="top" class="tableclass" id="tableid" stype="border:0; padding:1; background:#FFEEEE;">"""
        )
    basecamp_blank = (
        """<tr>"""
        ### """<td style="background:#E8E8F0;" colspan="5"></td>"""
        """</tr>"""
        )
    basecamp_heading = (
        """<tr style="background:#E8E8F0;">"""
        """<th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th>"""
        """</tr>"""
        )
    basecamp_prefix = (
        """<tr style="background:#F8F8FF;">"""
        """<td>@prefix</td><td>%s:</td><td colspan="3">&lt;%s&gt;</td>"""
        """</tr>"""
        )
    basecamp_oldclass = (
        """<tr style="background:#F8F8FF; color:#606060;">"""
        """<td colspan="3" valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td>"""
        """</tr>"""
        )
    basecamp_newclass = (
        """<tr style="background:#F8F8FF;">"""
        """<td colspan="3" valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td>"""
        """</tr>"""
        )
    basecamp_oldentry = (
        """<tr style="background:#F8F8FF; color:#606060;">"""
        """<td valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td>"""
        """</tr>"""
        )
    basecamp_newentry = (
        """<tr style="background:#F8F8FF;">"""
        """<td valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td><td valign="top">%s</td>"""
        """</tr>"""
        )
    basecamp_oldentry_long = (
        """<tr style="background:#F8F8FF; color:#606060;">"""
        """<td rowspan="2" valign="top">%s</td><td rowspan="2" valign="top">%s</td><td colspan="3">%s</td>"""
        """</tr>"""
        """<tr style="background:#F8F8FF; color:#606060;">"""
        """<td></td><td>%s</td><td>%s</td>"""
        """</tr>"""
        )
    basecamp_newentry_long = (
        """<tr style="background:#F8F8FF;">"""
        """<td rowspan="2" valign="top">%s</td><td rowspan="2" valign="top">%s</td><td colspan="3">%s</td>"""
        """</tr>"""
        """<tr style="background:#F8F8FF;">"""
        """<td></td><td>%s</td><td>%s</td>"""
        """</tr>"""
        )
    basecamp_comment = (
        """<tr style="background:#F8F8FF; color:#C00000; font-style:italic;">"""
        """<td></td><td></td><td></td><td></td><td>--&nbsp;%s</td>"""
        """</tr>"""
        )
    basecamp_postamble = (
        """</table>\n\n"""
        )
    basecamp_class = (
        """h3. Class %s\n"""
        """\n%s\n\n"""
        )
    basecamp_property = (
        """h3. Property %s\n"""
        """\n%s\n\n"""
        )

    def writeAssertion(attr, attrvals):
        """
        Helper function to write an assertion entry, selecting an appropriate format string
        
        If the assertion value (object) is full URI then use long form format string
        """
        if attr.isFullUriValue():
            if attr.isNew():
                opstr.write(basecamp_newentry_long%tuple(attrvals))
            else:
                opstr.write(basecamp_oldentry_long%tuple(attrvals))
        else:
            if attr.isNew():
                opstr.write(basecamp_newentry%tuple(attrvals))
            else:
                opstr.write(basecamp_oldentry%tuple(attrvals))
        return

    # Parse vocabulary details from CSV
    try:
        vocab = readVocabulary(csvreader)
    except csv.Error, e:
        sys.stderr.write("input line %d: %s" % (csvreader.line_num, e))
        return 1
    # Process vocabulary
    opstr.write(basecamp_preamble)
    for item in vocab.getSequence():
        if item == None:
            opstr.write(basecamp_blank)
        elif isinstance(item, VocabHeadings):
            headings = [ h or "&nbsp;" for h in item.getHeadings()[1:6] ]
            opstr.write(basecamp_heading%tuple(headings))
        elif isinstance(item, VocabPrefix):
            #TODO: include label, descr, comment?
            opstr.write(basecamp_prefix%(item.getPrefix(),item.getUri()))
        elif isinstance(item, VocabClass):
            # Class
            classvals = (item.getEscapedQNameOrUri(),item.getLabel(),item.getDescription())
            if item.isNew():
                opstr.write(basecamp_newclass%tuple(classvals))
            else:
                opstr.write(basecamp_oldclass%tuple(classvals))
            comment   = item.getComment()
            if comment:
                opstr.write(basecamp_comment%("<br/><br/>".join(comment)))
            # Attributes
            for attr in item.getAttrs():
                prop = attr.getQName()
                if attr.isInverse(): prop = "&#94; "+prop
                attrvals = ("", prop, attr.getEscapedValueQNameOrUri(), attr.getLabel(), attr.getDescription())
                writeAssertion(attr, attrvals)
                ###if attr.isNew():
                ###    opstr.write(basecamp_newentry_long%tuple(attrvals))
                ###else:
                ###    opstr.write(basecamp_oldentry_long%tuple(attrvals))
                comment   = attr.getComment()
                if comment:
                    opstr.write(basecamp_comment%("<br/><br/>".join(comment)))
            # Slots
            for slot in item.getSlots():
                prop = slot.getQName()
                if slot.isInverse(): prop = "&#94; "+prop
                if slot.getMinCardinality() == 0:
                    if slot.getMaxCardinality() == 1:
                        flag = '?'
                    else:
                        flag = '&#42;'
                else:
                    if slot.getMaxCardinality() == 1:
                        flag = '1'
                    else:
                        flag = '+'
                styp = flag + " :: " + slot.getEscapedValTypeQNameOrUri()
                slotvals = ("", prop, styp, slot.getLabel(), slot.getDescription())
                if slot.isNew():
                    opstr.write(basecamp_newentry%tuple(slotvals))
                else:
                    opstr.write(basecamp_oldentry%tuple(slotvals))
                for asrt in slot.getAssertions(): 
                    prop = asrt.getQName()
                    if prop == "rdfs:subPropertyOf":
                        prop = "<="
                    asrtvals = ("", "", prop+" "+asrt.getEscapedValueQNameOrUri(), asrt.getLabel(), asrt.getDescription())
                    writeAssertion(asrt, asrtvals)
                    ###if asrt.isNew():
                    ###    opstr.write(basecamp_newentry%tuple(asrtvals))
                    ###else:
                    ###    opstr.write(basecamp_oldentry%tuple(asrtvals))
                comment   = slot.getComment()
                if comment:
                    opstr.write(basecamp_comment%("<br/><br/>".join(comment)))
        else:
            assert False, "Unexpected value: "+str(item)
    opstr.write(basecamp_postamble)
    # Second pass to pick out class comments:
    if False:
        for item in vocab.getSequence():
            if isinstance(item, VocabClass):
                comment   = item.getComment()
                if comment:
                    opstr.write(basecamp_class%(item.getUri(), "\n\n".join(comment)))
    # Third pass to pick out slot property comments:
    if False:
        for item in vocab.getSequence():
            if isinstance(item, VocabClass):
                for slot in item.getSlots():
                    comment   = slot.getComment()
                    if comment:
                        opstr.write(basecamp_property%(slot.getUri(), "\n\n".join(comment)))
    return 0

def getOptions(prog, argv):
    """
    Get options and open data streams; also set up logging options
    
    prog    is the name of the program
    argv    is a list of arguments from the command line
    
    Returns a triple (input_stream,output_stream,options).
    """

    # Get command line arguments
    parser = optparse.OptionParser(
                usage="%prog [options] [input]\n\n"\
                      "where 'input' is an optional input file name (defaults to stdin)",
                version="%prog $Rev: 1024 $")
    # Main program options
    parser.add_option("-m", "--mediawiki", 
                      action="store_true", dest="mediawiki", 
                      default=False,
                      help="Generate Mediawiki table output format")
    parser.add_option("-b", "--basecamp", 
                      action="store_true", dest="basecamp", 
                      default=False,
                      help="Generate Basecamp (Textile) table output format")
    parser.add_option("-r", "--rdf", 
                      action="store_true", dest="rdf", 
                      default=False,
                      help="Generate OWL/RDF schema output")
    parser.add_option("-n", "--n3", 
                      action="store_true", dest="n3", 
                      default=False,
                      help="Generate Notation3 schema output")
    parser.add_option("-v", "--verbose", 
                      action="store_true", dest="verbose", 
                      default=False,
                      help="Display information about progress of operation")

    # Input and output options
    parser.add_option("-i", "--input", 
                      dest="inp_file", 
                      default="",
                      help="Input file name (defaults to stdin)")
    parser.add_option("-o", "--output",
                      dest="out_file", 
                      default="",
                      help="Output file name (defaults to stdout)")

    # Debugging and logging options
    parser.add_option("-c", "--info",
                      action="store_true", dest="log_info", 
                      default=False,
                      help="Log informative (commentary) output")
    parser.add_option("-d", "--debug", 
                      action="store_true", dest="log_debug", 
                      default=False,
                      help="Log debug output")
    parser.add_option("-t", "--timed", 
                      action="store_true", dest="log_timed", 
                      default=False,
                      help="Add timestamps to log output")
    parser.add_option("-l", "--logfile", 
                      dest="log_filename", 
                      default="",
                      help="Log file name")

    # Parse command line now
    (options, args) = parser.parse_args(argv)
    if len(args) > 2: parser.error("Too many arguments")

    # Set up logging
    log_level = logging.WARNING
    filelog_level = logging.WARNING
    if options.log_info:
        log_level = logging.INFO
        filelog_level = logging.INFO
    if options.log_debug:   
        log_level = logging.DEBUG
        filelog_level = logging.DEBUG

    logformat = logging.Formatter('%(levelname)s %(name)s %(message)s', "%H:%M:%S")
    if options.log_timed:
        logformat = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s', "%H:%M:%S")

    rootlogger = logging.getLogger('')
    rootlogger.setLevel(logging.DEBUG)  # Then filter in handlers for less.

    strhandler = logging.StreamHandler(sys.stdout)
    strhandler.setLevel(log_level)
    strhandler.setFormatter(logformat)
    rootlogger.addHandler(strhandler)
    
    if options.log_filename:
        # Enable logging to a file
        fileloghandler = logging.FileHandler(options.logfilename,"w")
        fileloghandler.setLevel(filelog_level)
        fileloghandler.setFormatter(logformat)
        rootlogger.addHandler(fileloghandler)

    # Set up input and output streams
    ipstr = sys.stdin
    if len(args) == 2:
        options.inp_file = args[1]
    if options.inp_file:
        try:
            ipstr = open(options.inp_file,"rb")
        except IOError, e:
            sys.stderr.write("Open input file %s failed: %s"%(options.inp_file,str(e)))
            return (None, None, None)

    opstr = sys.stdout
    if options.out_file:
        try:
            opstr = open(options.out_file,"wb")
        except IOError, e:
            sys.stderr.write("Open output file %s failed: %s"%(options.inp_file,str(e)))
            return (None, None, None)
    ### opstr = EncodedFile(opstr,'...','utf-8')


    # return to process
    return (ipstr,opstr,options)

# Program run from command line

if __name__ == "__main__":
    (ipstr,opstr,options) = getOptions("ConvertOntology", sys.argv)
    status = 1
    if ipstr and opstr and options:
        status  = convertOntology(ipstr,opstr,options)
    sys.exit(status)

# $Id: ConvertOntology.py 1024 2008-12-17 17:42:56Z graham $, end.
