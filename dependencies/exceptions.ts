/**
 * The dependencies that are deliberately not pinned exactly.
 *
 * Without this every run would warn about the same handful of intentional decisions, and a warning list
 * that is never empty is a warning list nobody reads. Each entry carries a reason, so the next person
 * can tell a decision from an oversight - which is the whole difference this file exists to record.
 */

import path from "node:path";
import { ECOSYSTEMS, type Ecosystem, type Pin } from "./types";

export type Exception = {
	ecosystem: Ecosystem;
	/** as `Pin.id` spells it: PEP 503 for python, byte exact for node, registry/repository for docker */
	name: string;
	/** why it floats. Required, because an entry without one is indistinguishable from a mistake */
	reason: string;
	/** when given, only these files are exempt, so a library can float what an app must pin */
	files?: string[];
};

export const EXCEPTIONS_FILE = "dependencies/exceptions.json";

/** the committed list, or none at all when the file is absent, which is a valid state for a fixture */
export const readExceptions = async (repoDir: string): Promise<Exception[]> => {
	const file = Bun.file(path.join(repoDir, EXCEPTIONS_FILE));
	if (!(await file.exists())) return [];
	let parsed: unknown;
	try {
		parsed = JSON.parse(await file.text());
	} catch (error) {
		throw new Error(`could not parse ${EXCEPTIONS_FILE}: ${error}`);
	}
	const listed = (parsed as { exceptions?: unknown }).exceptions;
	if (!Array.isArray(listed))
		throw new Error(`${EXCEPTIONS_FILE} has no exceptions array`);
	return listed.map((entry, index): Exception => {
		const { ecosystem, name, reason, files } = entry as {
			ecosystem?: string;
			name?: string;
			reason?: string;
			files?: string[];
		};
		if (!ecosystem || !name || !reason)
			throw new Error(
				`${EXCEPTIONS_FILE} entry ${index} needs an ecosystem, a name and a reason`,
			);
		// checked rather than trusted: an ecosystem this tool does not know would match no pin and so
		// exempt nothing, which from the outside looks exactly like the entry working
		if (!ECOSYSTEMS.includes(ecosystem as Ecosystem))
			throw new Error(
				`${EXCEPTIONS_FILE} entry ${index} names ecosystem "${ecosystem}", expected ${ECOSYSTEMS.join(", ")}`,
			);
		return { ecosystem: ecosystem as Ecosystem, name, reason, files };
	});
};

/** the exception covering a pin, when one does */
export const exemption = (exceptions: Exception[], pin: Pin) =>
	exceptions.find(
		(exception) =>
			exception.ecosystem === pin.ecosystem &&
			exception.name === pin.id &&
			(!exception.files || exception.files.includes(pin.file)),
	);
