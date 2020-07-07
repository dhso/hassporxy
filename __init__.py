# configuration.yaml 配置
#
# hassproxy:
#     client_openid: 'xxxxxx'
#     client_bufsize: 1024 # 可选 吞吐量
#     client_protocol: 'https' # 可选 不要改
#     client_lport: 8123 # 可选 ha端口号
#     client_rport: 0 # 可选 不要改
#     client_lhost: '127.0.0.1' # 可选 不要改
#     server_host: 'xxx.com' #可选
#     server_port: 4443 #可选

import os

from homeassistant.const import (EVENT_HOMEASSISTANT_START,
                                 EVENT_HOMEASSISTANT_STOP, EVENT_STATE_CHANGED)
import logging
LOGGER = logging.getLogger(__name__)

DOMAIN = 'hassproxy'
SERVER_HOST = 'xxx.com'
SERVER_PORT = 4443
CLIENT_BUFSIZE = 1024
CLIENT_PROTOCOL = 'https'
CLIENT_LPORT = 8123
CLIENT_RPORT = 0
CLIENT_HOST = '127.0.0.1'


def setup(hass, config):
    global DOMAIN
    global NOTIFYID
    global SERVER_HOST
    global SERVER_PORT
    global CLIENT_BUFSIZE
    global CLIENT_PROTOCOL
    global CLIENT_LPORT
    global CLIENT_RPORT
    global CLIENT_HOST
    """Set up hassproxy component."""
    LOGGER.info("Begin setup hassproxy!")

    def send_notify(notify_str,
                    notify_title="Hass Proxy Infomation",
                    notify_id="hassproxy_notify"):
        """Update UI."""
        LOGGER.debug("Send notify: %s", notify_str)
        hass.components.persistent_notification.async_create(
            notify_str, notify_title, notify_id)

    # Load config mode from configuration.yaml.
    cfg = config[DOMAIN]
    if 'client_openid' not in cfg:
        send_notify("No client_openid in hassproxy config!")
        LOGGER.error("No client_openid in hassproxy config!")
        return False
    if 'server_host' not in cfg:
        cfg['server_host'] = SERVER_HOST
    if 'server_port' not in cfg:
        cfg['server_port'] = SERVER_PORT
    if 'client_bufsize' not in cfg:
        cfg['client_bufsize'] = CLIENT_BUFSIZE
    if 'client_protocol' not in cfg:
        cfg['client_protocol'] = CLIENT_PROTOCOL
    if 'client_lport' not in cfg:
        cfg['client_lport'] = CLIENT_LPORT
    if 'client_rport' not in cfg:
        cfg['client_rport'] = CLIENT_RPORT
    if 'client_lhost' not in cfg:
        cfg['client_lhost'] = CLIENT_HOST

    async def stop_hassproxy(event):
        """Stop Hassproxy while closing ha."""
        LOGGER.info("Begin stop hassproxy!")
        from .hassproxy_main import stop_proxy
        stop_proxy()

    async def start_hassproxy(event):
        """Start Hassproxy while starting ha."""
        LOGGER.debug("hassproxy started!")
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hassproxy)

    async def handle_event(event):
        """Handle Hassproxy event."""

    async def on_state_changed(event):
        """Disable the dismiss button if needed."""

    from .hassproxy_main import run_proxy
    run_proxy(hass, cfg)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_hassproxy)
    hass.bus.async_listen(EVENT_STATE_CHANGED, on_state_changed)
    hass.bus.async_listen('hassproxy_event', handle_event)

    return True