"""
Define the community machanism.
Author:www.muzixing.com

Date                Work
2015/5/29           new this file
2015/7/20           define the class of oxp msg.
2015/7/21           Problem:I mix up the server and client protocol stack
                    So, all packet will have parser and serializer method.

"""

"""
Decoder/Encoder implementations of OpenExchange 1.0.
____________________________________________________
OXPT_HELLO = 0          # Symmetric message done
OXPT_ERROR = 1          # Symmetric message done
OXPT_ECHO_REQUEST = 2   # Symmetric message done
OXPT_ECHO_REPLY = 3     # Symmetric message done
OXPT_EXPERIMENTER = 4   # Symmetric message done

OXPT_FEATURES_REQUEST = 5       # Super/Domain message  done
OXPT_FEATURES_REPLY = 6         # Super/Domain message  done

OXPT_GET_CONFIG_REQUEST = 7     # Super/Domain message  done
OXPT_GET_CONFIG_REPLY = 8       # Super/Domain message  done
OXPT_SET_CONFIG = 9             # Super/Domain message  done

OXPT_TOPO_REQUEST = 10          # Super/Domain message  done
OXPT_TOPP_REPLY = 11            # Super/Domain message  done

OXPT_HOST_REQUEST = 12          # Super/Domain message  done
OXPT_HOST_REPLY = 13            # Super/Domain message  done
OXPT_HOST_UPDATE = 14           # Super/Domain message  done

OXPT_VPORT_STATUS = 15          # Asynchronous message

OXPT_SBP = 16       # Southbound Protocol message       done

OXPT_VENDOR = 17    # Vendor message                    done
____________________________________________________

Common structures

_______________

vport           done
host            done
internal_link   done
_______________
"""

import struct
import binascii

from oxproto_parser import StringifyMixin, MsgBase, msg_pack_into, msg_str_attr
from ryu.lib import addrconv
from ryu.lib import mac
from ryu.lib.ip import ipv4_to_str
from ryu.lib.ip import ipv4_to_bin
from . import oxproto_parser
from . import oxproto_v1_0 as oxproto
from ryu import utils

import logging
LOG = logging.getLogger('ryu.oxproto.oxproto_v1_0_parser')

_MSG_PARSERS = {}


def _set_msg_type(msg_type):
    '''Annotate corresponding OXP message type'''
    def _set_cls_msg_type(cls):
        cls.cls_msg_type = msg_type
        return cls
    return _set_cls_msg_type


def _register_parser(cls):
    '''class decorator to register msg parser'''
    assert cls.cls_msg_type is not None
    assert cls.cls_msg_type not in _MSG_PARSERS
    _MSG_PARSERS[cls.cls_msg_type] = cls.parser
    return cls


@oxproto_parser.register_msg_parser(oxproto.OXP_VERSION)
def msg_parser(domain, version, msg_type, msg_len, xid, buf):
    parser = _MSG_PARSERS.get(msg_type)
    return parser(domain, version, msg_type, msg_len, xid, buf)


def _set_msg_reply(msg_reply):
    '''Annotate OXP reply message class'''
    def _set_cls_msg_reply(cls):
        cls.cls_msg_reply = msg_reply
        return cls
    return _set_cls_msg_reply

#
# common structures
#


class OXPVPort(oxproto_parser.namedtuple('OXPVPort', (
        'vport_no', 'state'))):

    @classmethod
    def parser(cls, buf, offset):
        port = struct.unpack_from(oxproto.OXP_VPORT_PACK_STR,
                                  buf, offset)
        port = list(port)
        return cls(*port)


class OXPHost(oxproto_parser.namedtuple('OXPHost', (
        'ip', 'mac', 'mask', 'state'))):

    @classmethod
    def parser(cls, buf, offset):
        host = struct.unpack_from(oxproto.OXP_HOST_PACK_STR,
                                  buf, offset)
        return cls(*host)


class OXPInternallink(oxproto_parser.namedtuple('OXPInternallink', (
        'src_vport', 'dst_vport', 'capability'))):

    @classmethod
    def parser(cls, buf, offset):
        link = struct.unpack_from(oxproto.OXP_INTERNAL_LINK_PACK_STR,
                                  buf, offset)
        return cls(*link)
#
# Open eXchange Protocol messages
# parser + serializer
#


@_register_parser
@_set_msg_type(oxproto.OXPT_HELLO)
class OXPHello(MsgBase):
    def __init__(self, domain):
        super(OXPHello, self).__init__(domain)


@_register_parser
@_set_msg_type(oxproto.OXPT_ERROR)
class OXPErrorMsg(MsgBase):
    def __init__(self, domain, type_=None, code=None, data=None):
        super(OXPErrorMsg, self).__init__(domain)
        self.type = type_
        self.code = code
        self.data = data

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPErrorMsg, cls).parser(domain, version, msg_type,
                                             msg_len, xid, buf)
        msg.type, msg.code = struct.unpack_from(
            oxproto.OXP_ERROR_MSG_PACK_STR, msg.buf,
            oxproto.OXP_HEADER_SIZE)
        msg.data = msg.buf[oxproto.OXP_ERROR_MSG_SIZE:]
        return msg

    def _serialize_body(self):
        assert self.data is not None
        msg_pack_into(oxproto.OXP_ERROR_MSG_PACK_STR, self.buf,
                      oxproto.OXP_HEADER_SIZE, self.type, self.code)
        self.buf += self.data


@_register_parser
@_set_msg_type(oxproto.OXPT_ECHO_REPLY)
class OXPEchoReply(MsgBase):
    def __init__(self, domain, data=None):
        super(OXPEchoReply, self).__init__(domain)
        self.data = data

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPEchoReply, cls).parser(domain, version, msg_type,
                                              msg_len, xid, buf)
        msg.data = msg.buf[oxproto.OXP_HEADER_SIZE:]
        return msg

    def _serialize_body(self):
        assert self.data is not None
        self.buf += self.data


@_register_parser
@_set_msg_type(oxproto.OXPT_ECHO_REQUEST)
class OXPEchoRequest(MsgBase):
    def __init__(self, domain, data=None):
        super(OXPEchoRequest, self).__init__(domain)
        self.data = data

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPEchoRequest, cls).parser(domain, version, msg_type,
                                                msg_len, xid, buf)
        msg.data = msg.buf[oxproto.OXP_HEADER_SIZE:]
        return msg

    def _serialize_body(self):
        if self.data is not None:
            self.buf += self.data


@_register_parser
@_set_msg_type(oxproto.OXPT_FEATURES_REPLY)
class OXPDomainFeatures(MsgBase):
    def __init__(self, domain, domain_id=None,
                 proto_type=None, sbp_version=None, capabilities=None):
        super(OXPDomainFeatures, self).__init__(domain)
        self.domain_id = domain_id
        self.proto_type = proto_type
        self.sbp_version = sbp_version
        self.capabilities = capabilities

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPDomainFeatures, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)

        _id, _type, _version, _capabilities = struct.unpack_from(
            oxproto.OXP_DOMAIN_FEATURES_PACK_STR, msg.buf,
            oxproto.OXP_HEADER_SIZE)

        msg.domain_id = _id
        msg.proto_type = _type
        msg.sbp_version = _version
        msg.capabilities = _capabilities

        return msg

    def _serialize_body(self):
        msg_pack_into(oxproto.OXP_DOMAIN_FEATURES_PACK_STR, self.buf,
                      oxproto.OXP_HEADER_SIZE, self.domain_id,
                      self.proto_type, self.sbp_version, self.capabilities)


@_register_parser
@_set_msg_type(oxproto.OXPT_FEATURES_REQUEST)
class OXPFeaturesRequest(MsgBase):
    def __init__(self, domain):
        super(OXPFeaturesRequest, self).__init__(domain)

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPFeaturesRequest, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)
        return msg


@_register_parser
@_set_msg_type(oxproto.OXPT_GET_CONFIG_REPLY)
class OXPGetConfigReply(MsgBase):
    def __init__(self, domain, flags=24,
                 period=20, miss_send_len=128):
        super(OXPGetConfigReply, self).__init__(domain)
        self.flags = flags
        self.period = period
        self.miss_send_len = miss_send_len

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPGetConfigReply, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)

        msg.flags, msg.period, msg.miss_send_len = struct.unpack_from(
            oxproto.OXP_DOMAIN_CONFIG_PACK_STR, msg.buf,
            oxproto.OXP_HEADER_SIZE)

        return msg

    def _serialize_body(self):
        msg_pack_into(oxproto.OXP_DOMAIN_CONFIG_PACK_STR, self.buf,
                      oxproto.OXP_HEADER_SIZE, self.flags,
                      self.period, self.miss_send_len)


@_register_parser
@_set_msg_type(oxproto.OXPT_GET_CONFIG_REQUEST)
class OXPGetConfigRequest(MsgBase):
    def __init__(self, domain):
        super(OXPGetConfigRequest, self).__init__(domain)

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPGetConfigRequest, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)
        return msg


@_register_parser
@_set_msg_type(oxproto.OXPT_SET_CONFIG)
class OXPSetConfig(MsgBase):
    def __init__(self, domain, flags=24,
                 period=20, miss_send_len=128):
        super(OXPSetConfig, self).__init__(domain)
        self.flags = flags
        self.period = period
        self.miss_send_len = miss_send_len

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPSetConfig, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)

        msg.flags, msg.period, msg.miss_send_len = struct.unpack_from(
            oxproto.OXP_DOMAIN_CONFIG_PACK_STR, msg.buf,
            oxproto.OXP_HEADER_SIZE)

        return msg

    def _serialize_body(self):
        msg_pack_into(oxproto.OXP_DOMAIN_CONFIG_PACK_STR, self.buf,
                      oxproto.OXP_HEADER_SIZE, self.flags,
                      self.period, self.miss_send_len)


@_register_parser
@_set_msg_type(oxproto.OXPT_TOPO_REPLY)
class OXPTopoReply(MsgBase):
    def __init__(self, domain, links=set()):
        super(OXPTopoReply, self).__init__(domain)
        self.links = links

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPTopoReply, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)

        msg.links = set()
        n_links = ((msg_len - oxproto.OXP_HEADER_SIZE) /
                   oxproto.OXP_INTERNAL_LINK_SIZE)
        offset = oxproto.OXP_HEADER_SIZE

        for i in xrange(n_links):
            link = OXPInternallink.parser(msg.buf, offset)
            msg.links.add(link)
            offset += oxproto.OXP_INTERNAL_LINK_SIZE

        return msg

    def _serialize_body(self):
        offset = oxproto.OXP_HEADER_SIZE
        if self.links:
            for link in self.links:
                msg_pack_into(oxproto.OXP_INTERNAL_LINK_PACK_STR,
                              self.buf, offset, link.src_vport,
                              link.dst_vport, link.capability)
                offset += oxproto.OXP_INTERNAL_LINK_SIZE


@_register_parser
@_set_msg_type(oxproto.OXPT_TOPO_REQUEST)
class OXPTopoRequest(MsgBase):
    def __init__(self, domain):
        super(OXPTopoRequest, self).__init__(domain)

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPTopoRequest, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)
        return msg


@_register_parser
@_set_msg_type(oxproto.OXPT_HOST_REPLY)
class OXPHostReply(MsgBase):
    def __init__(self, domain, hosts=set()):
        super(OXPHostReply, self).__init__(domain)
        self.hosts = hosts

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPHostReply, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)

        msg.hosts = set()
        n_host = ((msg_len - oxproto.OXP_HEADER_SIZE) / oxproto.OXP_HOST_SIZE)
        offset = oxproto.OXP_HEADER_SIZE

        for i in xrange(n_host):
            host = OXPHost.parser(msg.buf, offset)
            msg.hosts.add(host)
            offset += oxproto.OXP_HOST_SIZE

        return msg

    def _serialize_body(self):
        offset = oxproto.OXP_HEADER_SIZE
        for host in self.hosts:
            msg_pack_into(oxproto.OXP_HOST_PACK_STR,
                          self.buf, offset, host.ip,
                          host.mac, host.mask, host.state)
            offset += oxproto.OXP_HOST_SIZE


@_register_parser
@_set_msg_type(oxproto.OXPT_HOST_REQUEST)
class OXPHostRequest(MsgBase):
    def __init__(self, domain):
        super(OXPHostRequest, self).__init__(domain)

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPHostRequest, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)
        return msg


@_register_parser
@_set_msg_type(oxproto.OXPT_HOST_UPDATE)
class OXPHostUpdate(MsgBase):
    def __init__(self, domain, hosts=set()):
        super(OXPHostUpdate, self).__init__(domain)
        self.hosts = hosts

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPHostUpdate, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)

        msg.hosts = set()
        n_host = ((msg_len - oxproto.OXP_HEADER_SIZE) / oxproto.OXP_HOST_SIZE)
        offset = oxproto.OXP_HEADER_SIZE

        for i in xrange(n_host):
            host = OXPHost.parser(msg.buf, offset)
            msg.hosts.add(host)
            offset += oxproto.OXP_HOST_SIZE

        return msg

    def _serialize_body(self):
        offset = oxproto.OXP_HEADER_SIZE
        for host in self.hosts:
            msg_pack_into(oxproto.OXP_HOST_PACK_STR,
                          self.buf, offset, host.ip,
                          host.mac, host.mask, host.state)
            offset += oxproto.OXP_HOST_SIZE


@_register_parser
@_set_msg_type(oxproto.OXPT_VPORT_STATUS)
class OXPVportStatus(MsgBase):
    def __init__(self, domain, reason=None, vport=None):
        super(OXPVportStatus, self).__init__(domain)
        self.reason = reason
        self.vport = vport

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPVportStatus, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)

        msg.reason, msg.vport_no, msg.state = struct.unpack_from(
            oxproto.OXP_VPORT_STATUS_PACK_STR, msg.buf,
            oxproto.OXP_HEADER_SIZE)

        return msg

    def _serialize_body(self):
        offset = oxproto.OXP_HEADER_SIZE
        msg_pack_into(
            oxproto.OXP_VPORT_STATUS_PACK_STR,
            self.buf, offset, self.reason,
            self.vport.vport_no, self.vport.state)


@_register_parser
@_set_msg_type(oxproto.OXPT_SBP)
class OXPSBP(MsgBase):
    def __init__(self, domain, data=None):
        super(OXPSBP, self).__init__(domain)
        self.data = data

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPSBP, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)
        msg.data = buf[oxproto.OXP_HEADER_SIZE:]

        return msg

    def _serialize_body(self):
        assert self.data is not None
        self.buf += self.data


class OXPSBP_Header(StringifyMixin):
    def __init__(self, type=None, flags=0, length=None, xid=0):
        super(OXPSBP_Header, self).__init__()
        self.type = type
        self.flags = flags
        self.length = length
        self.xid = xid
        self.buf = bytearray()

    @classmethod
    def parser(cls, buf, offset):
        _type, flags, length, xid = struct.unpack_from(
            oxproto.OXP_SBP_COMPRESSED_HEADER_PACK_STR,
            buffer(buf), offset)
        msg = OXPSBP_Header(type=_type, flags=flags, length=length, xid=xid)
        return msg

    def serialize(self):
        msg_pack_into(oxproto.OXP_SBP_COMPRESSED_HEADER_PACK_STR, self.buf,
                      0, self.type, self.flags, self.length, self.xid)


class OXPSBP_Forwarding_Request(StringifyMixin):
    def __init__(self, src_ip, dst_ip, in_port, mask=255,
                 eth_type=0x0800, qos=1, data=None):
        super(OXPSBP_Forwarding_Request, self).__init__()
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.in_port = in_port
        self.mask = mask
        self.eth_type = eth_type
        self.qos = qos
        self.buf = bytearray()
        self.data = data

    @classmethod
    def parser(cls, buf, offset):
        src_ip, dst_ip, in_port, mask, eth_type, qos = struct.unpack_from(
            oxproto.OXPSBP_FORWARDING_REQUEST_PACK_STR, buffer(buf), offset)

        data = buf[oxproto.OXPSBP_REQUEST_SIZE:]
        msg = OXPSBP_Forwarding_Request(src_ip=ipv4_to_str(src_ip),
                                        dst_ip=ipv4_to_str(dst_ip),
                                        in_port=in_port, mask=mask,
                                        eth_type=eth_type, qos=qos,
                                        data=data)
        return msg

    def serialize(self):
        msg_pack_into(oxproto.OXPSBP_FORWARDING_REQUEST_PACK_STR, self.buf,
                      0, ipv4_to_bin(self.src_ip), ipv4_to_bin(self.dst_ip),
                      self.in_port, self.mask,
                      self.eth_type, self.qos)
        self.buf += self.data


class OXPSBP_Forwarding_Reply(StringifyMixin):
    def __init__(self, src_ip, dst_ip, src_vport,
                 dst_vport, mask=255, eth_type=0x800, qos=1):
        super(OXPSBP_Forwarding_Reply, self).__init__()
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_vport = src_vport
        self.dst_vport = dst_vport
        self.mask = mask
        self.eth_type = eth_type
        self.qos = qos
        self.buf = bytearray()

    @classmethod
    def parser(cls, buf, offset):
        (src_ip, dst_ip, src_vport,
         dst_vport, mask, eth_type,
         qos) = struct.unpack_from(oxproto.OXPSBP_FORWARDING_REPLY_PACK_STR,
                                   buffer(buf), offset)

        msg = OXPSBP_Forwarding_Reply(src_ip=ipv4_to_str(src_ip),
                                      dst_ip=ipv4_to_str(dst_ip),
                                      src_vport=src_vport, dst_vport=dst_vport,
                                      mask=mask, eth_type=eth_type, qos=qos)
        return msg

    def serialize(self):
        msg_pack_into(oxproto.OXPSBP_FORWARDING_REPLY_PACK_STR, self.buf, 0,
                      ipv4_to_bin(self.src_ip), ipv4_to_bin(self.dst_ip),
                      self.src_vport, self.dst_vport,
                      self.mask, self.eth_type, self.qos)


class OXPSBP_Packet_Out(StringifyMixin):
    def __init__(self, out_port, data=None):
        super(OXPSBP_Packet_Out, self).__init__()
        self.out_port = out_port
        self.data = data
        self.buf = bytearray()

    @classmethod
    def parser(cls, buf, offset):
        (out_port, ) = struct.unpack_from(
            oxproto.OXPSBP_PACKET_OUT_PACK_STR, buffer(buf), offset)

        data = buf[oxproto.OXPSBP_PKT_OUT_SIZE:]
        msg = OXPSBP_Packet_Out(out_port=out_port, data=data)
        return msg

    def serialize(self):
        msg_pack_into(oxproto.OXPSBP_PACKET_OUT_PACK_STR,
                      self.buf, 0, self.out_port)
        self.buf += bytearray(self.data)


@_register_parser
@_set_msg_type(oxproto.OXPT_VENDOR)
class OXPVendor(MsgBase):
    _VENDORS = {}

    @staticmethod
    def register_vendor(id_):
        def _register_vendor(cls):
            OXPVendor._VENDORS[id_] = cls
            return cls
        return _register_vendor

    def __init__(self, domain):
        super(OXPVendor, self).__init__(domain)
        self.data = None
        self.vendor = None

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPVendor, cls).parser(domain, version, msg_type,
                                           msg_len, xid, buf)
        (msg.vendor,) = struct.unpack_from(
            oxproto.OXP_VENDOR_HEADER_PACK_STR, msg.buf,
            oxproto.OXP_HEADER_SIZE)

        cls_ = cls._VENDORS.get(msg.vendor)
        if cls_:
            msg.data = cls_.parser(domain, msg.buf, 0)
        else:
            msg.data = msg.buf[oxproto.OXP_VENDOR_HEADER_SIZE:]

        return msg

    def serialize_header(self):
        msg_pack_into(oxproto.OXP_VENDOR_HEADER_PACK_STR,
                      self.buf, oxproto.OXP_HEADER_SIZE, self.vendor)

    def _serialize_body(self):
        assert self.data is not None
        self.serialize_header()
        self.buf += self.data


@_register_parser
@_set_msg_type(oxproto.OXPT_EXPERIMENTER)
class OXPExperimenter(MsgBase):
    def __init__(self, domain, data=None):
        super(OXPExperimenter, self).__init__(domain)
        self.data = data

    @classmethod
    def parser(cls, domain, version, msg_type, msg_len, xid, buf):
        msg = super(OXPExperimenter, cls).parser(
            domain, version, msg_type, msg_len, xid, buf)
        msg.data = msg.buf[oxproto.OXP_HEADER_SIZE:]
        return msg

    def _serialize_body(self):
        if self.data is not None:
            self.buf += self.data
