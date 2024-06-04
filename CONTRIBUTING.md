# Contribution Guidelines

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) first, any changes that do not follow the Code of Conduct will not be considered for inclusion in Data Concierge!

## GitHub Issues

We welcome the use of GitHub Issues to report bugs and request features. Please search for existing Issues relating to your request. If the Issue already adequately describes your request, you can simply use an emoji reaction to the top comment, if you have additional information or questions please add to the existing Issue rather than creating a new one.

## Commit messages

Please make sure your commit messages convey which files or features have been modified while remaining concise. The user can view commit details to see exactly which changes were made, so it only needs to be a short overview to provide at-a-glance identification.

Additionally, the imperative style should be used. Rather than `added X, modified Y`, say `add X, modify Y`. A good way to remember this is "If applied, my commit will…"

### Don't do this

- `changes`
- `stuff`
- `added Contributions file`
- `add CONTRIBUTIONS.md which contains the Contribution Guidelines for Data Concierge. The file contains a link to the Code of Conduct, guidelines about commit messages with examples of what not to do and what to do. Furthermore it explains that members of the public wishing to contribute changes to the project should submit a Pull Request`

### Do this

- `add Contribution Guidelines file`

## Coding style

Please follow the [PEP 8](https://peps.python.org/pep-0008/) style guide.

### Linting

We have the ruff linter configured to catch common errors and formatting issues. Please make sure you installed the development version of Concierge so the linter script will run when committing.

**Don't panic if you see a Failed status while committing!**

Ruff will attempt to fix any errors, if the checks fail but all errors are fixed, you can just add the changes and make your commit again. If there are errors ruff is unable to fix, you will have to manually resolve them and then commit.

## Pull Requests

Once you're happy with your changes, please submit a Pull Request and we will review your contribution and accept it if it matches our guidelines and the goals of the project.
