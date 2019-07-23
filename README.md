# 6pm-checker

A service that tracks changes in the price of goods on [6pm.com](https://www.6pm.com/) and sends email notifications if the price has decreased or a new product has appeared on this request.

## Usage

```sh
export CONFIG_6PM='[ {"url": "https://www.6pm.com/...", "mail": "shopaholic@gmail.com"} ]'
# Optional Mailjet API key
export MJ_API_KEY = "..."
export MJ_API_SECRET = "..."

python 6pm-checker.py
```
