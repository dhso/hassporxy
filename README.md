# hassporxy

A reverse proxy plugin for home assistant with ngrokd server.

## Useage

```
# configuration.yaml

hassproxy:
    client_openid: 'xxxxxx' # Your id
    client_lport: 8123 # Optional, your home-assistant port
    client_lhost: '127.0.0.1' # Optional, your home-assistant ip
    server_host: 'xxx.com' # Optional, if `SERVER_HOST` is not config in `__init__.py`
```

## Notice

-   Download and place this components in your `custom_components` folder

-   Restart home-assistant
