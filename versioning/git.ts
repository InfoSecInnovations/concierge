export const run = async (
	command: string[],
	options: { cwd: string; allowFailure?: boolean },
) => {
	const proc = Bun.spawn(command, {
		cwd: options.cwd,
		stdout: "pipe",
		stderr: "pipe",
	});
	const [stdout, stderr] = await Promise.all([
		new Response(proc.stdout).text(),
		new Response(proc.stderr).text(),
	]);
	const exitCode = await proc.exited;
	if (exitCode !== 0 && !options.allowFailure)
		throw new Error(
			`${command.join(" ")} exited with ${exitCode}: ${stderr.trim() || stdout.trim()}`,
		);
	return { exitCode, stdout, stderr };
};

/** never throws on a non zero exit: git uses exit codes as answers, e.g. `diff --quiet` */
export const git =
	(cwd: string) =>
	(...args: string[]) =>
		run(["git", ...args], { cwd, allowFailure: true });
