import logging
import time
import configparser
import socket
import subprocess
import os
import sys

_config = configparser.ConfigParser()
_config.read('config.ini')
DEFAULT_DELAY_MS = _config.getint('settings', 'message_delay_ms', fallback=50)
DEFAULT_SPLIT_LEN = _config.getint('settings', 'message_split_len', fallback=60)

user_states = {}


def update_user_state(user_id, state):
    user_states[user_id] = state


def get_user_state(user_id):
    return user_states.get(user_id, None)


def send_message(message, destination, interface):
    # The radio hardware truncates messages longer than 63 characters. To
    # ensure complete delivery we send messages in chunks slightly below
    # that limit.
    max_payload_size = getattr(interface, 'message_split_len', DEFAULT_SPLIT_LEN)
    for i in range(0, len(message), max_payload_size):
        chunk = message[i:i + max_payload_size]
        try:
            d = interface.sendText(
                text=chunk,
                destinationId=destination,
                wantAck=True,
                wantResponse=False
            )
            destid = get_node_id_from_num(destination, interface)
            chunk = chunk.replace('\n', '\\n')
            logging.info(f"Sending message to user '{get_node_short_name(destid, interface)}' ({destid}) with sendID {d.id}: \"{chunk}\"")
        except Exception as e:
            logging.info(f"REPLY SEND ERROR {e.message}")

        
        delay_sec = getattr(interface, 'message_delay', DEFAULT_DELAY_MS / 1000.0)
        time.sleep(delay_sec)


def get_node_info(interface, short_name):
    nodes = [{'num': node_id, 'shortName': node['user']['shortName'], 'longName': node['user']['longName']}
             for node_id, node in interface.nodes.items()
             if node['user']['shortName'].lower() == short_name]
    return nodes


def get_node_id_from_num(node_num, interface):
    for node_id, node in interface.nodes.items():
        if node['num'] == node_num:
            return node_id
    return None


def get_node_short_name(node_id, interface):
    node_info = interface.nodes.get(node_id)
    if node_info:
        return node_info['user']['shortName']
    return None


def send_bulletin_to_bbs_nodes(board, sender_short_name, subject, content, unique_id, bbs_nodes, interface):
    message = f"BULLETIN|{board}|{sender_short_name}|{subject}|{content}|{unique_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_mail_to_bbs_nodes(sender_id, sender_short_name, recipient_id, subject, content, unique_id, bbs_nodes,
                           interface):
    message = f"MAIL|{sender_id}|{sender_short_name}|{recipient_id}|{subject}|{content}|{unique_id}"
    logging.info(f"SERVER SYNC: Syncing new mail message {subject} sent from {sender_short_name} to other BBS systems.")
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface):
    message = f"DELETE_BULLETIN|{bulletin_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface):
    message = f"DELETE_MAIL|{unique_id}"
    logging.info(f"SERVER SYNC: Sending delete mail sync message with unique_id: {unique_id}")
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_channel_to_bbs_nodes(name, url, bbs_nodes, interface):
    message = f"CHANNEL|{name}|{url}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def tradewars_server_alive(port=4242, host="127.0.0.1", timeout=1):
    """Check if the Tradewars server is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_tradewars_server(port=4242, host="127.0.0.1"):
    """Start Tradewars server if it's not already running."""
    if tradewars_server_alive(port=port, host=host):
        return True

    server_path = os.path.join(os.path.dirname(__file__), "tradewars_server.py")
    try:
        subprocess.Popen([sys.executable, server_path])
        time.sleep(1)
    except Exception as e:
        logging.error(f"Unable to start Tradewars server: {e}")
        return False

    return tradewars_server_alive(port=port, host=host)
