# From extension folder run the following command to build and load temporarily the extension into Pi:

```bash
pi -e ./sampler-pi-extension.ts
```


# Permanent installation of the extension into Pi:

```bash
mkdir -p ~/.pi/agent/extensions
cp sampler-pi-extension.ts ~/.pi/agent/extensions/sampler.ts
```

# Combine Skill + Extension
You can use both at the same time:
Place the Skill (Markdown) in:
`~/.pi/agent/skills/sampler/SKILL.md` (global)

Or in `.agents/skills/sampler/SKILL.md` (inside the project)

Load the TypeScript extension with -e or by installing it in `~/.pi/agent/extensions/`.

The Skill gives instructions to the agent, while the extension provides higher-level tools/commands.

# How to test it step by step

Make sure you have an indexed project:
```bash
sampler project add current . --language auto
sampler index current
sampler embed current     # optional, for semantic search
```
Start Pi with the extension:
```bash
pi -e ./sampler-pi-extension.ts
```
Test the registered commands (inside Pi):
Type in the chat: `/sampler:callers processPayment`
Or directly: Use sampler to find all callers of AuthService
Test the high-level tool:
Ask the agent something like:
> "Use sampler_explore_codebase with action=callers and query=processPayment"
Observe the hook:
Try editing a file and see if it suggests reviewing callers/usages first.   
