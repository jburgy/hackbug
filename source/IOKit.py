#!/usr/bin/env python

'''Python bindings for the `I/O Kit`_ framework

The `I/O Kit`_ is a collection of system frameworks, libraries, tools, and other resources for creating device drivers in OS X.
It is based on an object-oriented programming model implemented in a restricted form of C++ that omits features unsuitable for
use within a multithreaded kernel.  Many of its entry points are wrappers for corresponding mach_ functions.


.. _`I/O Kit`: https://developer.apple.com/library/mac/#documentation/devicedrivers/conceptual/IOKitFundamentals/Introduction/Introduction.html
.. _mach: http://en.wikipedia.org/wiki/Mach_(kernel)
'''

from CoreFoundation import *
from ctypes import *
from objc import pyobjc_id, objc_object

_iokit = CDLL('/System/Library/Frameworks/iokit.framework/iokit')

kUSBVendorID	    		= 'idVendor'
kUSBProductID	    	    	= 'idProduct'

kIOUSBDeviceClassName		= 'IOUSBDevice'
kIOUSBInterfaceClassName	= 'IOUSBInterface'

kIOPublishNotification		= 'IOServicePublish'
kIOFirstPublishNotification	= 'IOServiceFirstPublish'
kIOMatchedNotification		= 'IOServiceMatched'
kIOFirstMatchNotification	= 'IOServiceFirstMatch'
kIOTerminatedNotification	= 'IOServiceTerminate'

kIOMasterPortDefault		= c_void_p.in_dll(_iokit, 'kIOMasterPortDefault')
kIOProviderClassKey		= 'IOProviderClass'

kIOServicePlane			= 'IOService'
kIOBSDNameKey			= 'BSD Name'
kIOCalloutDeviceKey		= 'IOCalloutDevice'
kIORegistryIterateRecursively	= 0x00000001
kIORegistryIterateParents	= 0x00000002

_iokit.IONotificationPortCreate.restype = c_void_p
_iokit.IONotificationPortCreate.argtypes = [c_void_p]

_iokit.IONotificationPortDestroy.argtypes = [c_void_p]

NOTIFICATION = CFUNCTYPE(None, py_object, c_void_p)

_iokit.IOServiceAddMatchingNotification.restype = c_int32
_iokit.IOServiceAddMatchingNotification.argtypes = [c_void_p, c_char_p, c_void_p, NOTIFICATION, py_object, c_void_p]

_iokit.IOObjectRelease.argtypes = [c_void_p]

_iokit.IONotificationPortGetRunLoopSource.restype = c_void_p
_iokit.IONotificationPortGetRunLoopSource.argtypes = [c_void_p]

_iokit.IORegistryEntrySearchCFProperty.restype = c_void_p
_iokit.IORegistryEntrySearchCFProperty.argtypes = [c_void_p, c_void_p, c_void_p, c_void_p, c_uint32]

def IOServiceMatching(name = kIOUSBDeviceClassName):
    '''Create a matching dictionary that specifies an IOService class match.

    Reimplements the `simple C function`_ in pure python using pyobjc_ CoreFoundation classes
    instead of using ctypes to wrap it and having to promote its result to an `objc_object`.

    Returns a CFMutableDictionaryRef_ with a special `kIOProviderClassKey` entry.
    A CFMutableDictionaryRef_ behaves very much like a `dict`.

    .. _`simple C function`: https://developer.apple.com/library/mac/#documentation/IOKit/Reference/IOKitLib_header_reference/Reference/reference.html#//apple_ref/doc/c_ref/IOServiceMatching
    .. _pyobjc: http://pythonhosted.org/pyobjc/
    .. _CFMutableDictionaryRef: https://developer.apple.com/library/mac/#documentation/CoreFoundation/Reference/CFMutableDictionaryRef/Reference/reference.html    
    '''
    dct = CFDictionaryCreateMutable(None, 0, kCFTypeDictionaryKeyCallBacks, kCFTypeDictionaryValueCallBacks)
    dct[kIOProviderClassKey] = name
    return dct

def raw_ptr(obj):
    '''Get pyobjc CFString raw pointer

    to pass it to IOKit functions via ctypes'''
    return pyobjc_id(obj.nsstring())

def IORegistryEntrySearchCFProperty(entry, plane, key, allocator=kCFAllocatorDefault, options=kIORegistryIterateRecursively):
    '''IORegistryEntrySearchCFProperty_ wrapper

    .. _IORegistryEntrySearchCFProperty: https://developer.apple.com/library/mac/#documentation/IOKit/Reference/IOKitLib_header_reference/Reference/reference.html#//apple_ref/doc/c_ref/IORegistryEntrySearchCFProperty
    '''
    prop = _iokit.IORegistryEntrySearchCFProperty(entry, plane, raw_ptr(CFSTR(key)), kCFAllocatorDefault, kIORegistryIterateRecursively)
    return objc_object(c_void_p = prop)

class IOIterator(object):
    '''Abstraction to iterate over a collection of `I/O Kit`_ objects

    Returned by IOServiceGetMatchingServices_ and IOServiceAddMatchingNotification_

    .. _IOServiceGetMatchingServices: https://developer.apple.com/library/mac/#documentation/IOKit/Reference/IOKitLib_header_reference/Reference/reference.html#//apple_ref/doc/c_ref/IOServiceGetMatchingServices
    '''
    def __init__(self, iterator):
        self._obj = iterator
    def release(self):
        _iokit.IOObjectRelease(self._obj)
    def __iter__(self):
        return self
    def next(self):
        '''IOIteratorNext_ wrapper

        Returns the next object in an iteration.
        
        .. _IOIteratorNext: https://developer.apple.com/library/mac/#documentation/IOKit/Reference/IOKitLib_header_reference/Reference/reference.html#//apple_ref/doc/c_ref/IOIteratorNext
        '''
        service = _iokit.IOIteratorNext(self._obj)
        if not service:
            raise StopIteration
        return service

def _callback(context, iterator):
    context(IOIterator(iterator))

def _path_callback(context, iterator):
    generator = (IORegistryEntrySearchCFProperty(service, kIOServicePlane, kIOCalloutDeviceKey) for service in IOIterator(iterator))
    context(generator)

_notification      = NOTIFICATION(_callback)
_path_notification = NOTIFICATION(_path_callback)

class IONotificationPort(object):
    '''IONotificationPortCreate_ wrapper

    Creates a notification object for receiving IOKit notifications of new devices or state changes.

    .. _IONotificationPortCreate: https://developer.apple.com/library/mac/#documentation/IOKit/Reference/IOKitLib_header_reference/Reference/reference.html#//apple_ref/doc/c_ref/IONotificationPortCreate
    '''
    def __init__(self, master_port = kIOMasterPortDefault):
        self._obj = _iokit.IONotificationPortCreate(master_port)

    def __del__(self):
        _iokit.IONotificationPortDestroy(self._obj)

    def addMatchingNotifications(self, matching, receiver):
        '''Rich IOServiceAddMatchingNotification_ wrapper

        Look up registered IOService objects that match a matching dictionary, and
        hooks notification requests to specially named methods on receiver.

        +------------------+-------------------------------+
        |Method Name       |Notification Type              |
        +==================+===============================+
        |`on_publish`      |``kIOPublishNotification``     |
        +------------------+-------------------------------+
        |`on_first_publish`|``kIOFirstPublishNotification``|
        +------------------+-------------------------------+
        |`on_match`        |``kIOMatchedNotification``     |
        +------------------+-------------------------------+
        |`on_first_match`  |``kIOFirstMatchNotification``  |
        +------------------+-------------------------------+
        |`on_terminate`    |``kIOTerminateNotification``   |
        +------------------+-------------------------------+

        The method should expect a single argument, which will be an :class:`.IOIterator`.  As a
        convenience, receiver can also implement methods whose names start with `on_path_`
        instead of `on_`.  These methods will receiver a generator which yields path names for
        the relevant devices.


        Sample_ receiver implementation::

            from CoreFoundation import *
            from IOKit import *
            
            port = IONotificationPort()

            matching = IOServiceMatching()
            matching[kUSBVendorID] = 0x0451
            matching[kUSBProductID] = 0xf432

            class Receiver(object):
                def on_path_match(self, paths):
                    for path in paths:
                        print '%s matched' % path
                def on_path_terminate(self, paths):
                    for path in paths:
                        print '%s terminated' % path

            receiver = Receiver()
            iterator = port.addMatchingNotifications(matching, receiver)

            source = port.getRunLoopSource()
            CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopDefaultMode)
            CFRunLoopRun()
        
        .. _IOServiceAddMatchingNotification: https://developer.apple.com/library/mac/#documentation/IOKit/Reference/IOKitLib_header_reference/Reference/reference.html#//apple_ref/doc/c_ref/IOServiceMatchingAddNotification
        .. _Sample: https://developer.apple.com/library/mac/#documentation/DeviceDrivers/Conceptual/USBBook/USBDeviceInterfaces/USBDevInterfaces.html
        '''
        map = (
            (kIOPublishNotification,        'on_publish',               _notification),
            (kIOFirstPublishNotification,   'on_first_publish',         _notification),
            (kIOMatchedNotification,        'on_match',                 _notification),
            (kIOFirstMatchNotification,     'on_first_match',           _notification),
            (kIOTerminatedNotification,     'on_terminate',             _notification),
            (kIOPublishNotification,        'on_path_publish',          _path_notification),
            (kIOFirstPublishNotification,   'on_path_first_publish',    _path_notification),
            (kIOMatchedNotification,        'on_path_match',            _path_notification),
            (kIOFirstMatchNotification,     'on_path_first_match',      _path_notification),
            (kIOTerminatedNotification,     'on_path_terminate',        _path_notification),
        )

        obj = self._obj
        matching_id = pyobjc_id(matching)

        iterators = {}
        for k, v, n in map:
            attr = getattr(receiver, v, None)
            if not attr:
                continue
            wrap = py_object(attr)
            setattr(receiver, k + '_ctype', wrap) # keep reference
            it = c_void_p()
            ret = _iokit.IOServiceAddMatchingNotification(obj, k, matching_id, n, wrap, byref(it))
            if ret:
                raise IOException(ret)
            n(wrap, it)
            iterators[v] = it

        return iterators

    def getRunLoopSource(self):
        '''IONotificationPortGetRunLoopSource_ wrapper

        .. _IONotificationPortGetRunLoopSource: https://developer.apple.com/library/mac/#documentation/IOKit/Reference/IOKitLib_header_reference/Reference/reference.html#//apple_ref/doc/c_ref/IONotificationPortGetRunLoopSource
        '''
        source = _iokit.IONotificationPortGetRunLoopSource(self._obj)
        return CFRunLoopSourceRef(c_void_p = source)

if __name__ == '__main__':

    port = IONotificationPort()

    matching = IOServiceMatching()
    matching[kUSBVendorID] = 0x0451
    matching[kUSBProductID] = 0xf432

    class Receiver(object):
        def on_path_match(self, paths):
            for path in paths:
                print '%s matched' % path
#                self.serial = serial.serial_for_url(port, baudrate=9600, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_TWO, timeout=1)

        def on_path_terminate(self, paths):
            for path in paths:
                print '%s terminated' % path

    receiver = Receiver()
    iterator = port.addMatchingNotifications(matching, receiver)

    source = port.getRunLoopSource()
    
    assert not CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopDefaultMode)
    CFRunLoopRun()
