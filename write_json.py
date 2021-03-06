#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import random
import string
import uuid
import read_json
from base_util import tool_box

#打开配置文件
with open('/etc/v2ray/config.json', 'r') as json_file:
    config = json.load(json_file)

#写入配置文件
def write():
    my_json_dump=json.dumps(config,indent=1)
    with open('/etc/v2ray/config.json', 'w') as write_json_file:
        write_json_file.writelines(my_json_dump)

#inbound级别定位json
def locate_json(index_dict):
    if index_dict['inboundOrDetour'] == 0:
        part_json = config["inbound"]
    else:
        detour_index= index_dict['detourIndex']
        part_json = config["inboundDetour"][detour_index]
    return part_json

#设置inbound级别定位json
def set_locate_json(index_dict, json):
    if index_dict['inboundOrDetour'] == 0:
        config["inbound"] = json
    else:
        detour_index= index_dict['detourIndex']
        config["inboundDetour"][detour_index] = json

#减少mtproto int和out的路由绑定
def del_mtproto_routing(part_json):
    rules = config["routing"]["settings"]["rules"]
    for index, rule in enumerate(rules):
        if rule["outboundTag"] == "tg-out":
            if len(rule["inboundTag"]) == 1:
                del rules[index]
                for out_index, oubound_mtproto in enumerate(config["outboundDetour"]):
                    if oubound_mtproto["protocol"] == "mtproto":
                        del config["outboundDetour"][out_index]
                        break
            else:
                for tag_index, rule_tag in enumerate(rule["inboundTag"]):
                    if rule_tag == part_json["tag"]:
                        del rule["inboundTag"][tag_index]
                        break
            break

#更改动态端口
def en_dyn_port(en, index_dict, d_alterid=32):
    part_json = locate_json(index_dict)
    if en == 1:
        short_uuid = str(uuid.uuid1())[0:7]
        dynamic_port_tag = "dynamicPort" + short_uuid
        part_json["settings"].update({"detour":{"to":dynamic_port_tag}})
        with open('/usr/local/multi-v2ray/json_template/dyn_port.json', 'r') as dyn_port_file:
            dyn_json=json.load(dyn_port_file)
        dyn_json["settings"]["default"]["alterId"]=int(d_alterid)
        dyn_json["tag"]=dynamic_port_tag
        if config["inboundDetour"] == None:
            config["inboundDetour"]=[]
        config["inboundDetour"].append(dyn_json)
    else:
        dynamic_port_tag = part_json["settings"]["detour"]["to"]
        for index, detour_list in enumerate(config["inboundDetour"]):
            if "tag" in detour_list and detour_list["tag"] == dynamic_port_tag:
                del config["inboundDetour"][index]
                break
        if "detour" in part_json["settings"]:
            del part_json["settings"]["detour"]
    write()

#更改alterId
def write_alterid(alterid, index_dict):
    client_index = index_dict['clientIndex']
    part_json = locate_json(index_dict)
    part_json["settings"]["clients"][client_index]["alterId"]=int(alterid)
    write()

#更改端口
def write_port(my_port, index_dict):
    part_json = locate_json(index_dict)
    part_json["port"]=int(my_port)
    write()

#更改UUID
def write_uuid(my_uuid, index_dict):
    client_index = index_dict['clientIndex']
    part_json = locate_json(index_dict)
    part_json["settings"]["clients"][client_index]["id"]=str(my_uuid)
    write()

#更改email
def write_email(email, index_dict, protocol):
    client_index = index_dict['clientIndex']
    client_str = "clients" if protocol == "vmess" else "users"
    part_json = locate_json(index_dict)
    if not "email" in part_json["settings"][client_str][client_index]:
        part_json["settings"][client_str][client_index].update({"email": email})
    else:
        part_json["settings"][client_str][client_index]["email"]=email
    write()

#更改底层传输设置
def write_stream_network(network, index_dict, **kw):
    part_json = locate_json(index_dict)
    origin_protocol = part_json["protocol"]
    if part_json["protocol"] != "mtproto":
        security_backup = part_json["streamSettings"]["security"]
        tls_settings_backup = part_json["streamSettings"]["tlsSettings"]

    #减少mtproto int和out的路由绑定
    if part_json["protocol"] == "mtproto" and network != "mtproto":
        del_mtproto_routing(part_json)

    #原来是socks/mtproto 改成其他协议的
    if (part_json["protocol"] == "socks" and network != "socks" and network != "mtproto") or (part_json["protocol"] == "mtproto" and network != "mtproto" and network != "socks"):
        with open('/usr/local/multi-v2ray/json_template/server.json', 'r') as stream_file:
            vmess = json.load(stream_file)
        vmess["inbound"]["port"] = part_json["port"]
        set_locate_json(index_dict, vmess["inbound"])
        part_json = locate_json(index_dict)

    if (network == "tcp" and not kw):
        with open('/usr/local/multi-v2ray/json_template/tcp.json', 'r') as stream_file:
            tcp = json.load(stream_file)
        part_json["streamSettings"]=tcp

    elif (network == "tcp" and "para" in kw):
        with open('/usr/local/multi-v2ray/json_template/http.json', 'r') as stream_file:
            http = json.load(stream_file)
        http["tcpSettings"]["header"]["request"]["headers"]["Host"]=kw["para"]
        part_json["streamSettings"]=http

    elif (network == "socks" and "user" in kw and "pass" in kw):
        with open('/usr/local/multi-v2ray/json_template/socks.json', 'r') as stream_file:
            socks = json.load(stream_file)
        with open('/usr/local/multi-v2ray/json_template/tcp.json', 'r') as stream_file:
            tcp = json.load(stream_file)
        socks["accounts"][0]["user"]=kw["user"]
        socks["accounts"][0]["pass"]=kw["pass"]
        part_json["settings"]=socks
        part_json["protocol"]="socks"
        part_json["streamSettings"]=tcp

    elif (network == "mtproto"):
        with open('/usr/local/multi-v2ray/json_template/mtproto.json', 'r') as stream_file:
            mtproto = json.load(stream_file)
        mtproto_in = mtproto["mtproto-in"]
        mtproto_in["port"] = part_json["port"]
        mtproto_in["tag"] = index_dict["group"]
        salt = "abcdef" + string.digits
        secret = ''.join([random.choice(salt) for _ in range(32)])
        mtproto_in["settings"]["users"][0]["secret"] = secret
        set_locate_json(index_dict, mtproto_in)

        has_outbound = False
        for outbound in config["outboundDetour"]:
            if "protocol" in outbound and outbound["protocol"] == "mtproto":
                has_outbound = True
                break
        if not has_outbound:
            mtproto_out = mtproto["mtproto-out"]
            config["outboundDetour"].append(mtproto_out)
        
        rules = config["routing"]["settings"]["rules"]
        has_bind = False
        for rule in rules:
            if rule["outboundTag"] == "tg-out":
                has_bind = True
                inbound_tag_set = set(rule["inboundTag"])
                inbound_tag_set.add(index_dict["group"])
                rule["inboundTag"] = list(inbound_tag_set)
                break
        if not has_bind:
            routing_bind = mtproto["routing-bind"]
            routing_bind["inboundTag"][0] = index_dict["group"]
            rules.append(routing_bind)

    elif (network == "h2"):
        with open('/usr/local/multi-v2ray/json_template/http2.json', 'r') as stream_file:
            http2 = json.load(stream_file)
        part_json["streamSettings"]=http2
        #随机生成8位的伪装path
        salt = '/' + ''.join(random.sample(string.ascii_letters + string.digits, 8)) + '/'
        part_json["streamSettings"]["httpSettings"]["path"]=salt
        if (security_backup != "tls" or not "certificates" in tls_settings_backup):
            from base_util import v2ray_util
            v2ray_util.change_tls("on", index_dict)
            return

    elif (network == "ws" and "para" in kw):
        with open('/usr/local/multi-v2ray/json_template/ws.json', 'r') as stream_file:
            ws = json.load(stream_file)
        part_json["streamSettings"]=ws
        part_json["streamSettings"]["wsSettings"]["headers"]["Host"] = kw["para"]

        #随机生成8位的伪装path
        salt = '/' + ''.join(random.sample(string.ascii_letters + string.digits, 8)) + '/'
        part_json["streamSettings"]["wsSettings"]["path"]=salt

    elif (network == "mkcp" and not kw):
        with open('/usr/local/multi-v2ray/json_template/kcp.json', 'r') as stream_file:
            kcp = json.load(stream_file)
        part_json["streamSettings"]=kcp
        
    elif (network == "mkcp" and kw["para"]=="kcp utp"):
        with open('/usr/local/multi-v2ray/json_template/kcp_utp.json', 'r') as stream_file:
            utp = json.load(stream_file)
        part_json["streamSettings"]=utp
        
    elif (network == "mkcp" and kw["para"]=="kcp srtp"):
        with open('/usr/local/multi-v2ray/json_template/kcp_srtp.json', 'r') as stream_file:
            srtp = json.load(stream_file)
        part_json["streamSettings"]=srtp
        
    elif (network == "mkcp" and kw["para"]=="kcp wechat-video"):
        with open('/usr/local/multi-v2ray/json_template/kcp_wechat.json', 'r') as stream_file:
            wechat = json.load(stream_file)
        part_json["streamSettings"]=wechat
    
    elif (network == "mkcp" and "para" in kw and kw["para"]=="kcp dtls"):
        with open('/usr/local/multi-v2ray/json_template/kcp_dtls.json', 'r') as stream_file:
            dtls = json.load(stream_file)
        part_json["streamSettings"]=dtls
    
    if part_json["protocol"] != "mtproto" and origin_protocol != "mtproto":
        part_json["streamSettings"]["security"] = security_backup
        part_json["streamSettings"]["tlsSettings"] = tls_settings_backup

    write()

#更改TLS设置
def write_tls(action, domain, index_dict):
    part_json = locate_json(index_dict)
    if action == "on":
        part_json["streamSettings"]["security"] = "tls"
        crt_file = "/root/.acme.sh/" + domain +"_ecc"+ "/fullchain.cer"
        key_file = "/root/.acme.sh/" + domain +"_ecc"+ "/"+ domain +".key"
        with open('/usr/local/multi-v2ray/json_template/tls_settings.json', 'r') as tls_file:
            tls_settings=json.load(tls_file)
        tls_settings["certificates"][0]["certificateFile"] = crt_file
        tls_settings["certificates"][0]["keyFile"] = key_file
        part_json["streamSettings"]["tlsSettings"] = tls_settings

        with open('/usr/local/multi-v2ray/my_domain', 'w') as domain_file:
            domain_file.writelines(str(domain))
    elif action == "off":
        if part_json["streamSettings"]["network"] == "h2":
            print("关闭tls同时也会关闭HTTP/2！\n")
            print("已重置为kcp utp传输方式, 若要其他方式请自行切换")
            with open('/usr/local/multi-v2ray/json_template/kcp_utp.json', 'r') as stream_file:
                utp = json.load(stream_file)
            part_json["streamSettings"] = utp
        else:
            part_json["streamSettings"]["security"] = ""
            part_json["streamSettings"]["tlsSettings"] = {}
    write()

#更改广告拦截功能
def write_ad(action):
    if action == "on":
        config["routing"]["settings"]["rules"][0]["outboundTag"] = "blocked"
    else:
        config["routing"]["settings"]["rules"][0]["outboundTag"] = "direct"
    write()

#创建新的端口(组)
def create_new_port(newPort, protocol, **kw):
    origin_protocol=protocol
    # 如果源协议是mtproto和socks,则先新增utp的组，再修改
    if origin_protocol == "mtproto" or origin_protocol == "socks":
        protocol = "utp"
    with open('/usr/local/multi-v2ray/json_template/vmess.json', 'r') as vmess_file:
        vmess = json.load(vmess_file)
    with open('/usr/local/multi-v2ray/json_template/kcp_%s.json' % protocol, 'r') as stream_file:
        stream = json.load(stream_file)
    
    vmess["streamSettings"]=stream
    vmess["port"]=newPort
    vmess["settings"]["clients"][0]["id"]=str(uuid.uuid1())
    if config["inboundDetour"] == None:
        config["inboundDetour"]=[]
    config["inboundDetour"].append(vmess)
    print("新增端口组成功!")
    write()

    # 真正修改为mtproto或socks协议
    if origin_protocol == "mtproto" or origin_protocol == "socks":
        #重新读过配置文件
        from importlib import reload
        reload(read_json)
        write_stream_network(origin_protocol, read_json.multiUserConf[-1]["indexDict"], **kw)

#为某组新建用户
def create_new_user(group, **kw):
    multi_user_conf = read_json.multiUserConf
    user_index=0
    for index, sin_user_conf in enumerate(multi_user_conf):
        if sin_user_conf['indexDict']['group'] == group:
            user_index = index
            break

    part_json = locate_json(multi_user_conf[user_index]["indexDict"])

    if multi_user_conf[user_index]["protocol"] == "vmess":
        new_uuid = uuid.uuid1()
        email_info = ""
        with open('/usr/local/multi-v2ray/json_template/user.json', 'r') as userFile:
            user = json.load(userFile)
        if "email" in kw and kw["email"] != "":
            user.update({"email":kw["email"]})
            email_info = ", email: " + kw["email"]
        user["id"]=str(new_uuid)

        part_json["settings"]["clients"].append(user)
    
        print("新建用户成功! uuid: %s, alterId: 32%s" % (str(new_uuid), email_info))

    elif multi_user_conf[user_index]["protocol"] == "socks" and "user" in kw and "pass" in kw:
        user = {"user": kw["user"], "pass": kw["pass"]}
        part_json["settings"]["accounts"].append(user)
        print("新建Socks5用户成功! user: %s, pass: %s" % (kw["user"], kw["pass"]))
    write()

#删除用户
def del_user(index):
    multi_user_conf = read_json.multiUserConf
    index_dict = multi_user_conf[index]['indexDict']
    part_json = locate_json(index_dict)
    protocol = multi_user_conf[index]['protocol']

    #统计当前操作记录所在组的user数量
    count=0
    for sin_user_conf in multi_user_conf:
        if sin_user_conf['indexDict']['group'] == index_dict['group']:
            count += 1

    if count == 1:
        if index_dict['group'] == 'A':
            print("inbound组只有一个用户，无法删除")
            return    
        else:
            if protocol == "mtproto":
                del_mtproto_routing(part_json)
            print("当前inboundDetour组只有一个用户，整个节点组删除")
            del config["inboundDetour"][index_dict["detourIndex"]]
            if len(config["inboundDetour"]) == 0:
                config["inboundDetour"] == None
    elif protocol == "vmess":
        del part_json["settings"]["clients"][index_dict['clientIndex']]
    elif protocol == "socks":
        del part_json["settings"]["accounts"][index_dict['clientIndex']]

    print("删除用户成功!")
    write()

#删除组(端口)
def del_port(group):
    if group == 'A':
        print("A组为inbound, 无法删除")
        return
    else:
        multi_user_conf = read_json.multiUserConf
        detour_index = 0
        for sin_user_conf in multi_user_conf:
            if sin_user_conf['indexDict']['group'] == group:
                detour_index=sin_user_conf['indexDict']['detourIndex']
                if sin_user_conf["protocol"] == "mtproto":
                    index_dict=sin_user_conf['indexDict']
                    part_json = locate_json(index_dict)
                    del_mtproto_routing(part_json)
                break

        del config["inboundDetour"][detour_index]

        if len(config["inboundDetour"]) == 0:
            config["inboundDetour"] == None
        print("删除端口成功!")
        write()

#更改流量统计设置
def write_stats(action, multi_user_conf):
    conf_rules = config["routing"]["settings"]["rules"]
    if action == "on":
        with open('/usr/local/multi-v2ray/json_template/stats_settings.json', 'r') as stats_file:
            stats_json=json.load(stats_file)
        routing_rules = stats_json["routingRules"]
        del stats_json["routingRules"]

        for index_x, one_rule in enumerate(conf_rules):
            if "ip" in one_rule:
                for index_y, one_ip in enumerate(one_rule["ip"]):
                    if one_ip == "127.0.0.0/8":
                        del conf_rules[index_x]["ip"][index_y]
                        break
                break

        conf_rules.append(routing_rules)

        dokodemo_door = stats_json["dokodemoDoor"]
        del stats_json["dokodemoDoor"]
        #产生随机dokodemo_door的连接端口
        while True:
            random_port = random.randint(1000, 65535)
            if tool_box.port_is_open(random_port):
                break
        dokodemo_door["port"] = random_port
        if config["inboundDetour"] == None:
            config["inboundDetour"]=[]
        config["inboundDetour"].append(dokodemo_door)

        config.update(stats_json)

        last_group = "Z"
        for sin_user_conf in multi_user_conf:
            index_dict = sin_user_conf["indexDict"]
            group = index_dict["group"]
            if last_group == group or sin_user_conf["protocol"] == "mtproto":
                continue
            if group == 'A':
                config["inbound"].update({"tag":group})
            else:
                config["inboundDetour"][index_dict["detourIndex"]].update({"tag":group})
            last_group = group

    elif action == "off":
        if "stats" in config:
            del config["stats"]
        if "api" in config:
            del config["api"]
        if "policy" in config:
            del config["policy"]
        if config["inboundDetour"]:
            for index, detour_list in enumerate(config["inboundDetour"]):
                if detour_list["protocol"] == "dokodemo-door" and detour_list["tag"] == "api":
                    del config["inboundDetour"][index]
                    break

        for index,rules_list in enumerate(conf_rules):
            if rules_list["outboundTag"] == "api":
                del conf_rules[index]
                break
        
        if "tag" in config["inbound"] and config["inbound"]["tag"] == "A":
            last_group = "Z"
            for sin_user_conf in multi_user_conf:
                index_dict = sin_user_conf["indexDict"]
                group = index_dict["group"]
                if last_group == group or sin_user_conf["protocol"] == "mtproto":
                    continue
                if group == 'A':
                    del config["inbound"]["tag"]
                else:
                    del config["inboundDetour"][index_dict["detourIndex"]]["tag"]
                last_group = group
    write()