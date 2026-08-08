// the local development configuration is run by a watch process we spawn, which has to be
// stopped before the containers are touched or it will bring them straight back up. The
// containers can also be running from the devcontainer or a test run, in which case there's no
// process of ours to stop, hence the return value
export default async (state: { watchProcess?: Bun.Subprocess }) => {
	if (!state.watchProcess) return false;
	state.watchProcess.kill("SIGINT");
	await state.watchProcess.exited;
	delete state.watchProcess;
	return true;
};
