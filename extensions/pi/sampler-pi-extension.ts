/**
 * Pi Extension: Sampler Integration
 *
 * This TypeScript extension adds high-level commands and tools
 * for working with sampler-cli directly inside Pi.
 *
 * Place it in ~/.pi/agent/extensions/sampler.ts
 * or load it temporarily with: pi -e ./sampler-pi-extension.ts
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { StringEnum } from "@earendil-works/pi-ai";

// ============================================
// Shared Helpers for Sampler Setup & Query
// ============================================

const ensuredProjects = new Set<string>();

async function getCwdRoot(pi: ExtensionAPI): Promise<string> {
  const result = await pi.exec("bash", [
    "-c",
    "git rev-parse --show-toplevel 2>/dev/null || pwd",
  ]);
  return result.stdout.trim();
}

function getProjectNameFromPath(path: string): string {
  // Simple basename logic
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || "default";
}

async function ensureProjectReady(
  pi: ExtensionAPI,
  ctx: any,
  name: string,
  path: string,
  force: boolean = false,
): Promise<boolean> {
  if (ensuredProjects.has(name) && !force) return true;

  ctx.ui.notify(`Setting up sampler for project '${name}'...`, "info");

  // 1. Try to add project (ignore "already exists" error)
  const addResult = await pi.exec("bash", [
    "-c",
    `sampler project add "${name}" "${path}" --language auto`,
  ]);
  if (addResult.code !== 0 && !addResult.stderr.includes("already exists")) {
    ctx.ui.notify(`Failed to register project: ${addResult.stderr}`, "error");
    return false;
  }

  // 2. Index project (core graph: symbols, relationships, files)
  const indexCmd = force
    ? `sampler index "${name}" --plain --force`
    : `sampler index "${name}" --plain`;
  const indexResult = await pi.exec("bash", ["-c", indexCmd]);

  // Handle missing dependencies gracefully - core indexing still works
  if (indexResult.code !== 0) {
    const stderr = indexResult.stderr || indexResult.stdout;

    // Check for known optional dependency errors (BGE, numpy, etc.)
    if (
      stderr.includes("BGE") ||
      stderr.includes("numpy") ||
      stderr.includes("embeddings")
    ) {
      ctx.ui.notify(
        "Core indexing complete (semantic search requires optional deps: pip install 'sampler-cli[semantic,embeddings]').",
        "info",
      );
    } else {
      ctx.ui.notify(`Failed to index project: ${stderr}`, "error");
      return false;
    }
  } else {
    // Index succeeded - check if embeddings were generated
    if (
      indexResult.stdout.includes("Embedded") ||
      indexResult.stdout.includes("embed")
    ) {
      ctx.ui.notify("Project indexed with embeddings.", "success");
    } else {
      ctx.ui.notify(
        "Project indexed (semantic search unavailable without numpy).",
        "info",
      );
    }
  }

  ensuredProjects.add(name);
  ctx.ui.notify(`Project '${name}' is ready.`, "success");
  return true;
}

/**
 * Injects a block of text into the agent's context window as a system message.
 * This makes sampler output visible for follow-up reasoning and manual references.
 */
async function injectAgentContext(ctx: any, title: string, content: string) {
  if (ctx.agent?.submitMessage) {
    await ctx.agent.submitMessage({
      role: "system",
      content: `### Sampler Result: ${title}\n\n${content}`,
    });
  }
}

/**
 * Cleans sampler output to be more agent-friendly.
 * Strips "projectName:" prefix from lines to prevent path duplication issues in agent reasoning.
 */
function cleanSamplerOutput(output: string, projectName: string): string {
  if (!output || !projectName) return output || "";
  const escaped = projectName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Match project name at start of line, optionally after tree-drawing chars/spaces
  const regex = new RegExp(`^(\\s*[│├└─▎]?\\s*)${escaped}:`, "gm");
  return output.replace(regex, "$1");
}

/**
 * Shared helper to run a sampler command, display it nicely, and inject the
 * result into the agent's context window so it can reason about it.
 */
async function runAndReport(
  pi: ExtensionAPI,
  ctx: any,
  title: string,
  cmd: string,
  projectName?: string,
  successType: "success" | "info" = "success",
) {
  const result = await pi.exec("bash", ["-c", cmd]);
  const isSuccess = result.code === 0;
  const rawOutput = (result.stdout || result.stderr || "").trim();

  // Clean output if project matches
  const output = isSuccess && projectName
    ? cleanSamplerOutput(rawOutput, projectName)
    : rawOutput;

  // 1. If it's a success, send the cleaned output to the agent context
  //    so the user can refer to it and the agent can reason about it.
  if (isSuccess && output) {
    await injectAgentContext(
      ctx,
      `${title}\nUser manually executed \`${cmd}\``,
      output,
    );
  }

  // 2. Keep UI notification minimal: just the command and a status hint
  ctx.ui.notify(
    `▶ ${cmd}\n${isSuccess ? "✓ Results added to context" : output || "(no output)"}`,
    isSuccess ? successType : "error",
  );

  return { ...result, stdout: output, stderr: isSuccess ? "" : result.stderr };
}

/**
 * Resolves which project to use. If explicitProject is provided, we assume it's already registered.
 * Otherwise, we auto-detect from CWD and ensure it's indexed.
 */
async function resolveProject(
  pi: ExtensionAPI,
  ctx: any,
  explicitProject?: string,
): Promise<{ name: string; path: string } | null> {
  if (explicitProject) {
    return { name: explicitProject, path: "" }; // Path not needed for registered projects
  }

  const root = await getCwdRoot(pi);
  const name = getProjectNameFromPath(root);
  const success = await ensureProjectReady(pi, ctx, name, root);
  return success ? { name, path: root } : null;
}

export default function (pi: ExtensionAPI) {
  // ============================================
  // 1. Register useful commands
  // ============================================

  pi.registerCommand("sampler:search", {
    description: "Semantic or structural search in the codebase using sampler",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      const query =
        argsArray.find((a) => !a.startsWith("-")) ||
        (await ctx.ui.input("Search query:"));
      if (!query) return;

      const useSemantic =
        argsArray.includes("--semantic") ||
        (await ctx.ui.confirm("Use semantic search?", false));

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;

      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      const runSearch = async () => {
        const cmd = useSemantic
          ? `sampler search "${query}" --semantic --project "${resolved.name}" --limit 15 --style bars`
          : `sampler search "${query}" --project "${resolved.name}" --limit 15 --style bars`;
        return runAndReport(pi, ctx, `Search: ${query}`, cmd, resolved.name);
      };

      let result = await runSearch();

      // Fallback: If semantic search fails (possibly missing embeddings), try to embed and retry once
      if (useSemantic && result.code !== 0) {
        const stderr = result.stderr || result.stdout;
        if (
          stderr.includes("numpy") ||
          stderr.includes("semantic") ||
          stderr.includes("embeddings")
        ) {
          ctx.ui.notify(
            "Missing deps (pip install 'sampler-cli[semantic,embeddings]'). Falling back to keyword search.",
            "warning",
          );
          // Fallback to non-semantic search
          const fallbackCmd = `sampler search "${query}" --project "${resolved.name}" --limit 15`;
          result = await runAndReport(
            pi,
            ctx,
            `Search (fallback): ${query}`,
            fallbackCmd,
            resolved.name,
          );
        } else if (
          stderr.includes("requires embeddings") ||
          stderr.includes("not found")
        ) {
          ctx.ui.notify("Generating embeddings for semantic search...", "info");
          await pi.exec("bash", ["-c", `sampler embed "${resolved.name}"`]);
          result = await runSearch();
        }
      }
    },
  });

  pi.registerCommand("sampler:callers", {
    description: "Find who calls a symbol using sampler",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let symbol = argsArray.find((a) => !a.startsWith("-"));
      if (!symbol) {
        symbol = await ctx.ui.input("Symbol name (or path:symbol):");
      }
      if (!symbol) return;

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Callers of ${symbol}`,
        `sampler callers "${symbol}" --project "${resolved.name}" --style bars`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:usages", {
    description: "Find usages of a symbol",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let symbol = argsArray.find((a) => !a.startsWith("-"));
      if (!symbol) symbol = await ctx.ui.input("Symbol name:");
      if (!symbol) return;

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Usages of ${symbol}`,
        `sampler usages "${symbol}" --project "${resolved.name}" --style bars`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:related", {
    description: "Find related symbols in the graph",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let symbol = argsArray.find((a) => !a.startsWith("-"));
      if (!symbol) symbol = await ctx.ui.input("Symbol name:");
      if (!symbol) return;

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Related to ${symbol}`,
        `sampler related "${symbol}" --project "${resolved.name}" --style bars`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:overview", {
    description: "Get structural overview of a file",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let file = argsArray.find((a) => !a.startsWith("-"));
      if (!file) file = await ctx.ui.input("File path:");
      if (!file) return;

      // side effect: ensure project for current dir is indexed so overview works better
      const resolved = await resolveProject(pi, ctx);

      await runAndReport(
        pi,
        ctx,
        `Overview of ${file}`,
        `sampler overview "${file}" --style bars`,
        resolved?.name,
      );
    },
  });

  pi.registerCommand("sampler:stale", {
    description: "Find potentially stale code (only called from tests)",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      const explicitProject = argsArray.find((a) => !a.startsWith("-"));
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Stale code in ${resolved.name}`,
        `sampler stale-code "${resolved.name}" --limit 15`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:projects", {
    description: "List all registered projects",
    handler: async (args, ctx) => {
      await runAndReport(
        pi,
        ctx,
        "Registered Projects",
        "sampler project list",
        undefined,
        "info",
      );
    },
  });

  pi.registerCommand("sampler:remove", {
    description: "Remove a registered project",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let name = argsArray[0];
      if (!name) name = await ctx.ui.input("Project name to remove:");
      if (!name) return;

      const result = await pi.exec("bash", [
        "-c",
        `sampler project remove "${name}"`,
      ]);
      if (result.code === 0) {
        ensuredProjects.delete(name);
        ctx.ui.notify(`Project '${name}' removed.`, "success");
      } else {
        ctx.ui.notify(result.stderr || result.stdout, "error");
      }
    },
  });

  // ============================================
  // 2. Register a high-level tool that the LLM
  // can call directly. Tool results are returned
  // to the agent automatically; slash-command
  // results are also injected into context via
  // injectAgentContext so the user can refer to
  // them manually.
  // ============================================

  pi.registerTool({
    name: "sampler_explore_codebase",
    label: "Explore Codebase",
    description:
      "Explore an indexed codebase using sampler: structural/semantic search, callers, usages, related symbols, file overview, and stale-code detection. " +
      "Use this instead of grep/find when asking architectural questions ('who calls X', 'what's related to Y', 'is Z used anywhere'). " +
      "Always inspect the returned 'nextSteps' hint and consider calling this tool again with a follow-up action before answering the user.",
    promptSnippet:
      "Explore indexed codebase structure: search, callers, usages, related, overview, stale, list_projects",
    promptGuidelines: [
      "Use sampler_explore_codebase before making architectural claims about the current project (callers, usages, related symbols).",
      "Use sampler_explore_codebase with action=list_projects to check which projects are already indexed before assuming none exist.",
      "Chain sampler_explore_codebase calls: after a search or callers result, call it again with action=related or action=callers on an interesting symbol instead of stopping.",
      "Manual slash commands like /sampler:search results are also visible in your context window for follow-up questions.",
    ],
    parameters: Type.Object({
      action: StringEnum(
        [
          "search",
          "callers",
          "usages",
          "related",
          "overview",
          "stale",
          "list_projects",
        ] as const,
        {
          description: "What to do",
        },
      ),
      query: Type.Optional(
        Type.String({
          description:
            "Symbol name, file path, or search query (omit for list_projects)",
        }),
      ),
      semantic: Type.Optional(
        Type.Boolean({
          description: "Use semantic search (only for action=search)",
        }),
      ),
      project: Type.Optional(
        Type.String({ description: "Optional project name override" }),
      ),
      force: Type.Optional(
        Type.Boolean({ description: "Force re-index project before querying" }),
      ),
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const {
        action,
        query,
        semantic = false,
        project: explicitProject,
        force = false,
      } = params;

      if (action === "list_projects") {
        const cmd = "sampler project list";
        const result = await pi.exec("bash", ["-c", cmd], {
          signal,
        });
        const text =
          result.stdout || result.stderr || "(no projects registered)";

        await injectAgentContext(ctx, "Registered Projects", text);
        ctx.ui.notify(
          `▶ ${cmd}\n${result.code === 0 ? "✓ Results added to context" : text}`,
          result.code === 0 ? "info" : "error",
        );
        return {
          content: [{ type: "text", text }],
          details: { action, success: result.code === 0 },
        };
      }

      if (!query && action !== "list_projects") {
        throw new Error(`action=${action} requires a 'query' parameter`);
      }

      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) {
        throw new Error("Could not resolve or index the current project");
      }

      if (force) {
        await ensureProjectReady(pi, ctx, resolved.name, resolved.path, true);
      }

      const runCmd = async (c: string) => {
        let res = await pi.exec("bash", ["-c", c], { signal });
        // Handle CLI version mismatch: some versions might not support --style yet
        if (
          res.code !== 0 &&
          (res.stderr.includes("No such option '--style'") ||
            res.stdout.includes("No such option '--style'"))
        ) {
          const fallback = c.replace(/\s+--style\s+\S+/, "");
          res = await pi.exec("bash", ["-c", fallback], { signal });
        }
        return res;
      };

      let cmd = "";
      switch (action) {
        case "search":
          cmd = semantic
            ? `sampler search "${query}" --semantic --project "${resolved.name}" --limit 12 --style bars`
            : `sampler search "${query}" --project "${resolved.name}" --limit 12 --style bars`;
          break;
        case "callers":
          cmd = `sampler callers "${query}" --project "${resolved.name}" --style bars`;
          break;
        case "usages":
          cmd = `sampler usages "${query}" --project "${resolved.name}" --style bars`;
          break;
        case "related":
          cmd = `sampler related "${query}" --project "${resolved.name}" --style bars`;
          break;
        case "overview":
          cmd = `sampler overview "${query}" --style bars`;
          break;
        case "stale":
          cmd = `sampler stale-code "${resolved.name}" --limit 15`;
          break;
      }

      let result = await runCmd(cmd);

      // Fallback for semantic search missing deps
      let note = "";
      if (action === "search" && semantic && result.code !== 0) {
        const stderr = result.stderr || result.stdout;
        if (
          stderr.includes("numpy") ||
          stderr.includes("semantic") ||
          stderr.includes("embeddings")
        ) {
          const fallbackCmd = `sampler search "${query}" --project "${resolved.name}" --limit 12`;
          result = await runCmd(fallbackCmd);
          note =
            "(Semantic search unavailable [missing deps: pip install 'sampler-cli[semantic,embeddings]'], showing keyword results instead)\n\n";
        } else if (
          stderr.includes("requires embeddings") ||
          stderr.includes("not found")
        ) {
          await pi.exec("bash", ["-c", `sampler embed "${resolved.name}"`], {
            signal,
          });
          result = await runCmd(cmd);
        }
      }

      if (result.code !== 0) {
        throw new Error(
          result.stderr || result.stdout || `sampler ${action} failed`,
        );
      }

      const nextSteps: Record<string, string> = {
        search:
          "Next: call sampler_explore_codebase again with action=callers or action=related on an interesting result to explore the call graph.",
        callers:
          "Next: call sampler_explore_codebase with action=related to see connections, or action=usages to find where it's used.",
        usages:
          "Next: call sampler_explore_codebase with action=overview on a usage site, or action=related for graph exploration.",
        related:
          "Next: call sampler_explore_codebase with action=callers or action=search to dig deeper into the graph.",
        overview:
          "Next: call sampler_explore_codebase with action=callers or action=related on a symbol from this file.",
        stale:
          "Next: call sampler_explore_codebase with action=callers on a candidate to confirm it truly has no callers.",
      };

      const title = `Sampler ${action}${query ? `: ${query}` : ""}`;
      const output = cleanSamplerOutput(
        result.stdout || result.stderr || "",
        resolved.name,
      );
      const text = note + output + "\n\n" + (nextSteps[action] ?? "");

      await injectAgentContext(ctx, title, text);
      ctx.ui.notify(
        `▶ ${cmd}\n✓ Results added to context`,
        "success",
      );

      return {
        content: [{ type: "text", text }],
        details: { action, project: resolved.name, success: true },
      };
    },
  });

  // ============================================
  // 3. Nudge the agent toward sampler before edits
  // ============================================

  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "edit" || event.toolName === "write") {
      const file = (event.input as { path?: string })?.path;
      if (file) {
        ctx.ui.notify(
          `Tip: Consider calling sampler_explore_codebase (action=callers/related) on key symbols in ${file} first.`,
          "info",
        );
      }
    }
  });

  pi.on("before_agent_start", async (event, ctx) => {
    return {
      message: {
        customType: "sampler",
        content:
          "You have access to the sampler_explore_codebase tool for codebase exploration.",
        display: true,
      },
    };
  });
}
