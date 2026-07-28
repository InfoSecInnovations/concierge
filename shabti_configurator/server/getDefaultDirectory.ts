export default () => {
	if (process.platform == "win32") return process.env.PROGRAMDATA;
	return "/var/log/";
};
