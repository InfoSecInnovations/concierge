import { $ } from "bun";

export default () => $`uv run pre-commit install`.cwd("..");
