# marketquotes


## provisioning

```
ansible-playbook -i hosts provisioning.yml -u dperezrada --sudo --extra-vars="hosts=antarctic-data1"
```

## deploy

```
ansible-playbook -i hosts deploy.yml -u dperezrada --sudo --extra-vars="hosts=antarctic-data1"
```

## Execute

### Development
```
DEV=1 python crypto_market_quotes/main.py bitfinex
```