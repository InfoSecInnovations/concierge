import * as commander from "commander";
const program = new commander.Command();

program.configureOutput({
	// Visibly override write routines as example!
	writeOut: (str: any) => process.stdout.write(`[OUT] ${str}`),
	writeErr: (str: any) => process.stdout.write(`[ERR] ${str}`),
});

const logObject = {
	uwot: "m8",
	uavin: "a giggle",
};

program.version("1.2.3").option("-c, --compress").command("sub-command");
program.command("uwot").action((options, command) => {
	console.log(logObject);
});

program.parse();
