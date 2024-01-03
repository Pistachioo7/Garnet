# Garnet-ui

## 启动

软件要求：

python >= 3.10.12

npm >= 10.2.3

node >= v21.2.0

python 配置，建议使用虚拟环境

```shell
python -m venv .venv
```

启用虚拟环境

```shell
source .venv/bin/activate
```

安装后端依赖

```shell
pip install -r piplist
```

安装前端依赖

```shell
cd Vue3-garnet-ui
npm install pnpm
npm install
```

配置ui/settings.py下的本机相关常量

```python
# region 需要自定义设置的内容
# garnet文件夹
GARNETPATH = "../../Garnet"

# Metadata
NAME = "DELL_Windows"
IPADDRESS = "127.0.0.1"
PORT = 9000

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-3pn^b24iqv(2*ta^rq+%)ghl2--z7*qk4y7mkznai16_jx&@c8"
# endregion
```

修改前端中的后端地址 Vue3-garnet-ui/src/utils/request.js

```javascript
const baseURL = 'http://<djangoHost:djangoPort>/api/'
```

迁移数据库

```shell
ui/manage.py makemigrations Model
ui/manage.py makemigrations
ui/manage.py migrate
```

预加载数据项

```shell
ui/manage.py loaddata ui/protocol.json
ui/manage.py loaddata ui/mpc.json
```

运行服务器

```shell
ui/manage.py runserver <djangoHost:djangoPort>
```

如果使用vscode，也可以使用vscode的调试功能来一步启动，这首先需要修改.vscode\launch.json：

```json
    "args": [
        "runserver",
        "<djangoHost:djangoPort>"
    ],
```

运行任务队列 Django-q（使用另一终端）：

```shell
ui/manage.py qcluster
```

启动前端（再使用一个终端）：

```shell
cd Vue3-garnet-ui
pnpm dev --host yourHost --port yourPort
```