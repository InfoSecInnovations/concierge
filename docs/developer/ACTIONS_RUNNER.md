Action runner requirements:

- curl
- docker
- zip
- jq
- bun
- uv
- JRE
- libicu-dev
- wget

all of the above must run for the user which runs the runner

prior to setting the IP to static, install resolvconf

`sudo apt install resolvconf`

on WSL fix npm calling through to the Windows path:

- edit /etc/wsl.conf
	
	```
	[interop]
	appendWindowsPath=false
	```

npm trusted publishing doesn't work on self-hosted so we have a GitHub hosted runner to publish the npm package for the node client.