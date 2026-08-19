import path from "node:path";

export const repoRoot = path.resolve(import.meta.dir, "..");

export const absolute = (file: string) => path.join(repoRoot, file);

export const run = async (
	command: string[],
	options?: { cwd?: string; allowFailure?: boolean },
) => {
	const proc = Bun.spawn(command, {
		cwd: options?.cwd ?? repoRoot,
		stdout: "pipe",
		stderr: "pipe",
	});
	const [stdout, stderr] = await Promise.all([
		new Response(proc.stdout).text(),
		new Response(proc.stderr).text(),
	]);
	const exitCode = await proc.exited;
	if (exitCode !== 0 && !options?.allowFailure)
		throw new Error(
			`${command.join(" ")} exited with ${exitCode}: ${stderr.trim() || stdout.trim()}`,
		);
	return { exitCode, stdout, stderr };
};

/** never throws on a non zero exit: git uses exit codes as answers, e.g. `diff --quiet` */
export const git = (...args: string[]) =>
	run(["git", ...args], { allowFailure: true });

export const isDirty = async () => {
	const { stdout } = await git("status", "--porcelain");
	return stdout.trim().length > 0;
};
