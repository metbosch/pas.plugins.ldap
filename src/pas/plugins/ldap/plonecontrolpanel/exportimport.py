import types
import os.path
from zope.interface import implements
from zope.component import queryMultiAdapter
from BTrees.OOBTree import OOBTree
from Acquisition import Implicit
from Products.CMFCore.utils import getToolByName
from Products.GenericSetup.utils import XMLAdapterBase
from Products.GenericSetup.interfaces import IBody
from Products.GenericSetup.interfaces import IFilesystemExporter
from Products.GenericSetup.interfaces import IFilesystemImporter

def _get_import_export_handler(context):
    aclu = context.getSite().acl_users
    logger = context.getLogger('pas.plugins.ldap')    
    if 'pasldap' not in aclu.objectIds():
        logger.warn("Can't handle ldap settings, no ldap plugin named "\
                    "'pasldap' found.")
        return
    pasldap = aclu.pasldap
    handler = queryMultiAdapter((pasldap, context), IBody)
    if handler is not None:
        handler.filename = '%s%s' % (handler.name, handler.suffix)
        return handler
    logger.warn("Can't find handler for ldap settings")
    

def import_settings(context):
    handler = _get_import_export_handler(context)
    if not handler: 
        return
    body = context.readDataFile(handler.filename)
    if body is None:
        logger = context.getLogger('pas.plugins.ldap')    
        logger.info("No settings file found: %s" % handler.filename)
        return
    handler.body = body
    
def export_settings(context):
    handler = _get_import_export_handler(context)
    if not handler: 
        return
    body = handler.body
    if body is None:
        logger = context.getLogger('pas.plugins.ldap')    
        logger.warn("Problem to get ldap settings.")
        return
    context.writeDataFile(handler.filename, body, handler.mime_type)    
        

class LDAPPluginXMLAdapter(XMLAdapterBase):
    """import pas groups from ldap config"""
    
    implements(IBody)
    
    name = 'ldapsettings'

    def _exportNode(self):
        node = self._getObjectNode('object')
        self._setDataAndType(self.context.settings, node)
        return node
                
    def _importNode(self, node):
        node = self._getObjectNode('object')        
        data = self._getDataFromNode(node)
        for key in data:
            self.context.settings[key] = data[key]
            
    def _setDataAndType(self, data, node):
        if isinstance(data, (tuple, list)):
            node.setAttribute('type', 'list')                
            for value in data:                    
                element = self._doc.createElement('element')
                self._setDataAndType(value, element)
                node.appendChild(element)
            return 
        if isinstance(data, (dict, OOBTree)):
            node.setAttribute('type', 'dict')        
            for key in sorted(data.keys()):                    
                element = self._doc.createElement('element')
                element.setAttribute('key', key)                
                self._setDataAndType(data[key], element)
                node.appendChild(element)
            return
        if type(data) is types.BooleanType:
            node.setAttribute('type', 'bool')                
            data = str(data)
        elif type(data) is types.IntType:
            node.setAttribute('type', 'int')                                    
            data = str(data)
        elif type(data) is types.FloatType:
            node.setAttribute('type', 'float')                                    
            data = str(data)
        elif type(data) in types.StringTypes:
            node.setAttribute('type', 'string')
        else:
            self._logger.warning('Invalid type %s found for key %s on export, '\
                                 'skipped.' % (type(data), data))
            return
        child = self._doc.createTextNode(data)
        node.appendChild(child)
        
    def _getDataByType(self, node):
        vtype = node.getAttribute('type', None)
        if vtype is None:
            return None
        if vtype == 'list':
            data = list()
            for element in node.childNodes:
                if child.nodeName != 'element':
                    continue    
                data.append(self._getDataByType(element))
            return data
        if vtype == 'dict':
            data = dict()
            for element in node.childNodes:
                if child.nodeName != 'element':
                    continue 
                key =  element.getAttribute('key', None)  
                if key is None:
                    self._logger.warning('No key found for dict on import, '\
                                         'skipped.')
                    return None
                data.update({key: self._getDataByType(element)})
                return data
        data = self._getNodeText(node)
        if vtype == 'bool':
            data = boolean(data)
        elif vtype == 'int':
            data = int(data)
        elif vtype == 'float':
            data = float(data)
        elif vtype == 'string':
            data = str(data)
        else:
            self._logger.warning('Invalid type %s found on import, skipped.' %\
                                 vtype)
            return None