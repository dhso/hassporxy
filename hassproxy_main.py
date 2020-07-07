from .hassproxy_app import HASS_PROXY_APP

def run_proxy(hass, cfg):
    # Start reverse proxy.
    HASS_PROXY_APP.run_reverse_proxy(hass, cfg)


def stop_proxy():
    # Stop reverse proxy.
    HASS_PROXY_APP.stop_reverse_proxy()