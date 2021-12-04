#!/bin/sh

ufw allow 6866
ufw allow 6868

cd mkdir -p /home
cd /home
git clone https://gitee.com/lingyongji/FreedomNet2.git
cd FreedomNet2/server

bash run