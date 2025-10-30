import { $ } from "bun";
import * as dotenv from "dotenv";
import nukeExisting from "./nukeExisting";
import runSecurityTests from "./runSecurityTests";
import { mergeFiles, mergeToString } from "junit-report-merger";
import { rm, mkdir } from "node:fs/promises";
import { XMLBuilder, XMLParser } from "fast-xml-parser";
import path from "node:path";
import xunitViewer from "xunit-viewer";

await rm("./test_results", { recursive: true, force: true });

try {
	console.log(`
	-----------------------------------------------------
		RUNNING TESTS FOR SECURITY DISABLED INSTANCE...
	-----------------------------------------------------
	`);

	dotenv.config({ path: "security-disabled-env", override: true, quiet: true });
	await nukeExisting();
	console.log(
		"building Docker Compose... (can take some time if there are updates to the dependencies)",
	);
	await $`docker compose --env-file security-disabled-env -f ./docker-compose-pytest.yml build`.quiet();
	console.log(`
	____________RUNNING PYTHON TESTS______________
	`);
	await $`docker compose --env-file security-disabled-env -f ./docker-compose-pytest.yml up --attach shabti`;
	console.log(
		"building Docker Compose... (can take some time if there are updates to the dependencies)",
	);
	await $`docker compose --env-file security-disabled-env -f ./docker-compose-client-test.yml build`.quiet();
	await $`docker compose --env-file security-disabled-env -f ./docker-compose-client-test.yml up --attach shabti-client`;
	// launch API
	await $`docker compose --env-file security-disabled-env build`.quiet();
	await $`docker compose --env-file security-disabled-env up -d`;
	console.log(`
	__________RUNNING NODE TESTS___________
	`);
	console.log("waiting for API service to launch...");
	while (true) {
		try {
			await fetch("http://localhost:15131");
			break;
		} catch {
			continue;
		}
	}
	await $`bun test --reporter=junit --reporter-outfile=./tests_docker_compose/test_results/bun_security_disabled.xml`
		.cwd("..")
		.env({ ...process.env, FORCE_COLOR: "1" });

	await runSecurityTests();
} catch {}

await mkdir("./processed_test_runs", { recursive: true });
const filename = `shabti_test_run_${new Date().toISOString().replace(/:/g, "_")}`;
await mergeFiles("./test_results/merged.xml", ["./test_results/*.xml"]);
const merged = await Bun.file("./test_results/merged.xml").text();
const parser = new XMLParser({ ignoreAttributes: false });
const parsedObj = parser.parse(merged);
const processNode = (node: any) => {
	// valid test cases are either not skipped or don't match any non skipped tests (i.e. they were only skipped and not also executed in another run)
	if (node.testcase)
		node.testcase = node.testcase.filter(
			(testCase: any) =>
				typeof testCase.skipped == "undefined" ||
				!node.testcase.some(
					(otherCase: any) =>
						otherCase["@_name"] == testCase["@_name"] &&
						typeof otherCase.skipped == "undefined",
				),
		);
	if (node.testsuite) {
		if (Array.isArray(node.testsuite)) {
			for (const childNode of node.testsuite) {
				processNode(childNode);
			}
		} else {
			processNode(node.testsuite);
		}
	}
};
processNode(parsedObj.testsuites);
const builder = new XMLBuilder({ ignoreAttributes: false, format: true });
const finalXml = builder.build(parsedObj);
await Bun.write(path.join("processed_test_runs", `${filename}.xml`), finalXml);
await xunitViewer({
	server: false,
	results: path.join("processed_test_runs", `${filename}.xml`),
	title: "Shabti Aggregated Test Results",
	console: true,
	output: false,
	script: true,
});
